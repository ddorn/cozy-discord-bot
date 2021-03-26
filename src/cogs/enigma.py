import dataclasses
from dataclasses import dataclass
from operator import attrgetter

import discord
from discord import CategoryChannel, Colour, Guild, Member, PermissionOverwrite, TextChannel, VoiceChannel
from discord.ext.commands import Context, group, has_role
from discord.utils import get
from discord_slash import SlashCommandOptionType, SlashContext
from discord_slash.cog_ext import cog_slash
from discord_slash.utils.manage_commands import create_option

from src.constants import EPFL_GUILD, Role
from src.converters import ListOf
from src.core import CogConfig, CustomBot, CustomCog
from src.errors import EpflError
from src.utils import check_role, french_join, myembed


@dataclass
class Team:
    name: str
    members: ListOf(Member)
    role: discord.Role
    text: TextChannel
    voice: VoiceChannel
    solved: ListOf(str)

    @property
    def points(self):
        return len(self.solved)


class EnigmaCog(CustomCog, name="Concours d'énigmes"):
    class Config(CogConfig):
        chat_category: CategoryChannel
        __chat_category__ = "Where team channels are created"
        teams: ListOf(Team) = []
        cqfd: discord.Role
        __cqfd__ = "Organiser role"
        participants: discord.Role
        __participants__ = "Role requiered to participate"

    @group(name="enigma", aliases=["en"], invoke_without_command=True, hidden=True)
    async def enigma(self, ctx: Context):

        embed = myembed(
            "Aide pour le concours d'énigmes",
            ""
        )

        # await ctx.send()

    # @enigma.command(name="team", aliases=["new"])
    # @check_role("MA - Mathématiques")
    @cog_slash(name='enigma-new', description="Create a new team for CQFD's enigma contest.",
               guild_ids=[EPFL_GUILD], options=[
            create_option('name', 'Name of the team.', SlashCommandOptionType.STRING, True),
            create_option('member_1', 'First member of the team.', SlashCommandOptionType.USER, True),
            create_option('member_2', 'Second member of the team.', SlashCommandOptionType.USER, True),
            create_option('member_3', 'Optional third member of the team.', SlashCommandOptionType.USER, False),
        ])
    async def new_team(self, ctx: SlashContext, name, member_1, member_2, member_3=None):
        """Crée une équipe."""

        await ctx.respond()

        members = [member_1, member_2]
        if member_3:
            members.append(member_3)

        if len(set(members)) < len(members):
            await ctx.send('Every member must be different.')
            return

        guild: Guild = ctx.guild
        conf: EnigmaCog.Config = self.config(guild, "cqfd", "chat_category", "participants")


        if any(team.name == name for team in conf.teams):
            await ctx.send("Ce nom est déjà pris !")
            return

        # Create the role
        role = await guild.create_role(
            name=name,
            colour=Colour(0xF62459),
        )

        # add it the the team members
        for m in members:
            await m.add_roles(role)

        # Create the channels
        perms = {
            role: PermissionOverwrite(read_messages=True, connect=True),
            ctx.guild.default_role: PermissionOverwrite(read_messages=False),
            conf.cqfd: PermissionOverwrite(read_messages=True, connect=True),
        }

        text = await conf.chat_category.create_text_channel(
            name, overwrites=perms
        )

        # So people see the there is activity
        perms[get(ctx.guild.roles, name="MA - Mathématiques")] = PermissionOverwrite(view_channel=True)
        voice = await conf.chat_category.create_voice_channel(
            name, overwrites=perms
        )

        # Let the see the category Channels
        await conf.chat_category.set_permissions(role, view_channel=True)

        # Save everything
        with self.config(ctx.guild) as conf:
            conf.teams.append(
                Team(
                    name,
                    members,
                    role,
                    text,
                    voice,
                    solved=[]
                )
            )

        await ctx.send(f"J'ai créé l'équipe {name} et le salon {text.mention} ! Amusez vous bien {french_join([m.mention for m in members])};)")

    @enigma.command(name="del")
    @check_role("■ CQFD")
    async def del_team(self, ctx: Context, name: discord.Role):
        """Supprime une équipe."""
        conf: EnigmaCog.Config
        with self.config(ctx.guild) as conf:
            team: Team = get(conf.teams, name=name.name)

            if team is None:
                await ctx.send(f"No such team: `{name}`.")
                return

            reason = f"Team deleted by {ctx.author}"
            await team.role.delete(reason=reason)
            await team.text.delete(reason=reason)
            await team.voice.delete(reason=reason)

            conf.teams.remove(team)

            await ctx.send(f"Removed team {team.name} with {team.points} points.")

    @enigma.command(name="done", aliases=["solve", "points"])
    @check_role("■ CQFD")
    async def solve(self, ctx: Context, team: discord.Role, problem: int):
        """Marque un problème comme résolu."""
        conf: EnigmaCog.Config
        with self.config(ctx.guild) as conf:
            the_team = get(conf.teams, role=team)

            if the_team is None:
                raise EpflError("Not a valid team.")

            if problem not in range(12):
                raise EpflError(f"The problem must be an integer between 0 and 12, not {problem}")

            the_team.solved.append(problem)
            await ctx.send(
                f"L'équipe {team.mention} a désormais {the_team.points} pts !"
            )

    # @enigma.command(name="leaderboard", aliases=["l"])
    @cog_slash(name='enigma-leaderboard', description='Current points of each team.', guild_ids=[EPFL_GUILD])
    async def leaderboard(self, ctx: Context):
        """Classement du concours d'énigmes."""

        with self.config(ctx.guild) as conf:
            teams = sorted(conf.teams,
                           key=attrgetter("points"),
                           reverse=True)

            medals = [
                ":first_place:",
                ":second_place:",
                ":third_place:",
                ":military_medal:",
            ]

            nb = sum(len(t.members) for t in teams)
            embed = myembed(
                "Classement du concours d'énigmes",
                f"Avec {nb} participants ",
                0x000000,
            )

            for i, t in enumerate(teams):
                medal = medals[min(i, len(medals) - 1)]
                embed.add_field(
                    name=f"{medal} Place {i+1}",
                    value=f"{t.role.mention} - **{t.points}** pts",
                    inline=(i > 0),
                )

            await ctx.send(embed=embed)



def setup(bot: CustomBot):
    bot.add_cog(EnigmaCog(bot))
