import dataclasses
from dataclasses import dataclass
from operator import attrgetter

import discord
from discord import CategoryChannel, Colour, Guild, Member, PermissionOverwrite, TextChannel, VoiceChannel
from discord.ext.commands import Context, group, has_role
from discord.utils import get

from src.constants import Role
from src.converters import ListOf
from src.core import CogConfig, CustomBot, CustomCog
from src.errors import EpflError
from src.utils import check_role, myembed


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
        return sum(2**int(pb[-1]) for pb in self.solved)


class EnigmaCog(CustomCog):
    class Config(CogConfig):
        chat_category: CategoryChannel
        __chat_category__ = "Where team channels are created"
        teams: ListOf(Team) = []
        cqfd: discord.Role
        __cqfd__ = "Organiser role"
        participants: discord.Role
        __participants__ = "Role requiered to participate"

    @group(name="enigma", aliases=["en"], invoke_without_command=True, hidden=True)
    @check_role("MA - Mathématiques")
    async def enigma(self, ctx: Context):

        embed = myembed(
            "Aide pour le concours d'énigmes",
            ""
        )

        # await ctx.send()

    @enigma.command(name="team", aliases=["new"])
    @check_role("■ CQFD")
    async def new_team(self, ctx: Context, name: str, *members: Member):
        """Crée une équipe."""

        guild: Guild = ctx.guild
        conf: EnigmaCog.Config = self.config(guild, "cqfd", "chat_category", "participants")


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




        await ctx.send(f"J'ai crée l'équipe {name} et le salon {text.mention} ! Amusez vous bien ;)")

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
    async def solve(self, ctx: Context, team: discord.Role, problem: str):
        """Marque un problème comme résolu."""
        conf: EnigmaCog.Config
        with self.config(ctx.guild) as conf:
            the_team = get(conf.teams, role=team)

            if the_team is None:
                raise EpflError("Not a valid team.")

            cat = problem[:2]
            nb = problem[2:]

            if nb not in "123" or cat.lower() not in ("an", "al", "lo", "ma"):
                raise EpflError("The problem must be two two letters, either AN, AL, LO or MA"
                                "followed by the digit.")

            the_team.solved.append(problem)
            await ctx.send(
                f"L'équipe {team.mention} a désormais {the_team.points} pts !"
            )

    @enigma.command(name="leaderboard", aliases=["l"])
    @check_role("MA - Mathématiques")
    async def leaderboard(self, ctx: Context):
        """Classement du concours d'énigmes."""

        with self.config(ctx.guild) as conf:
            teams = sorted(conf.teams,
                           key=attrgetter("points"),
                           reverse=True)



            msg = "\n".join(
                f"{t.role.mention}: {t.points}pts"
                for t in teams
            )

            medals = [
                ":first_place:",
                ":second_place:",
                ":third_place:",
                ":military_medal:",
            ]

            embed = myembed(
                "Classement du concours d'énigmes",
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
