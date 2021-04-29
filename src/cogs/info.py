import datetime
import datetime
import itertools
import random
from itertools import chain
from operator import attrgetter
from time import time
from typing import List

import discord
from discord import (
    ChannelType,
    Guild,
    Member,
    TextChannel,
)
from discord.abc import GuildChannel
from discord.ext.commands import (
    command,
    Command,
    CommandError,
    Context,
    Group,
    guild_only,
)
from discord.utils import find, get
from engine import (
    CozyError,
    CustomBot,
    CustomCog,
    french_join,
    mentions_to_id,
    myembed,
    start_time,
)
from src.cogs.perms import RuleSet
from src.constants import *


class InfoCog(CustomCog, name="Infos"):
    def __init__(self, bot: CustomBot):
        super().__init__(bot)
        self.show_hidden = False
        self.verify_checks = True

    # ---------------- Info ----------------- #

    @guild_only()
    @command(name="info", aliases=["status"])
    async def info_cmd(self, ctx: Context, *, what: str = None):
        """Affiche des informations à propos du serveur ou de l'argument."""

        if what is None:
            return await self.send_server_info(ctx)

        guild: Guild = ctx.guild
        what_ = what
        what = what.strip()

        # Special cases
        if what in ("ici", "here"):
            return await self.send_channel_info(ctx, ctx.channel)
        if what in ("me", "moi"):
            return await self.send_member_info(ctx, ctx.author)

        # Emojis first
        emoji = get(ctx.guild.emojis, name=what) or find(
            lambda e: str(e) == what or e.name.casefold() == what.casefold(),
            ctx.guild.emojis,
        )
        if emoji:
            return await self.send_emoji_info(ctx, emoji)

        # try to convert it to an id
        what = mentions_to_id(what)
        try:
            what = int(what)
            obj = (
                guild.get_channel(what)
                or guild.get_role(what)
                or guild.get_member(what)
            )
        except ValueError:
            obj = (
                guild.get_member_named(what)
                or get(guild.roles, name=what)
                or get(guild.channels, name=what)
            )

            # Last try: casefold comp
            what = what.casefold()
            for r in chain(guild.roles, guild.channels, guild.members):
                if r.name.casefold() == what:
                    obj = r
                    break

        if (
            isinstance(obj, GuildChannel)
            and not obj.permissions_for(ctx.author).read_messages
        ):
            obj = None

        if obj is None:
            raise CozyError(f"Could not understand what {what_} is.")

        if isinstance(obj, discord.Role):
            return await self.send_role_info(ctx, obj)
        elif isinstance(obj, discord.Member):
            return await self.send_member_info(ctx, obj)
        else:
            return await self.send_channel_info(ctx, obj)

    async def send_server_info(self, ctx):
        guild: Guild = ctx.guild
        embed = discord.Embed(title="Server info", color=EMBED_COLOR)
        uptime = datetime.timedelta(seconds=round(time() - start_time()))
        text = len(guild.text_channels)
        vocal = len(guild.voice_channels)
        infos = {
            "Members": len(guild.members),
            "Text channels": text,
            "Voice channels": vocal,
            "Nombres de roles": len(guild.roles),
            "Bot uptime": uptime,
        }

        width = max(map(len, infos))
        txt = "\n".join(
            f"`{key.rjust(width)}`: {value}" for key, value in infos.items()
        )
        embed.add_field(name="Stats", value=txt)

        await ctx.send(embed=embed)

    async def send_role_info(self, ctx: Context, role: discord.Role):
        rule = RuleSet.load().get(role.id)

        age = datetime.datetime.now() - role.created_at
        d = age.days

        embed = myembed(
            f"Info pour le role {role.name}",
            "",
            role.color,
            Mention=role.mention,
            ID=role.id,
            Members=len(role.members),
            # Creation=role.created_at.ctime(),
            Created=f"{d} day{'s' * (d > 1)} ago",
            Mentionable="Yes" if role.mentionable else "No",
            Position=role.position,
            Auto_condition=rule.with_mentions() if rule is not None else "",
        )

        await ctx.send(embed=embed)

    async def send_member_info(self, ctx: Context, member: Member):

        member_since = datetime.datetime.now() - member.joined_at

        title = f"Info pour {member.display_name}"

        embed = myembed(
            title,
            "",
            member.color,
            Mention=member.mention,
            ID=member.id,
            Top_role=member.top_role.mention,
            Member_for=f"{member_since.days} day{'s' * (member_since.days > 1)}",
            Booster_since=member.premium_since,
            _Roles=french_join(r.mention for r in reversed(member.roles[1:])),
        )

        embed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=embed)

    async def send_channel_info(self, ctx: Context, chan: GuildChannel):

        crea = datetime.datetime.now() - chan.created_at
        rule = RuleSet.load().get(chan.id)
        type = "la catégorie" if chan.type == ChannelType.category else "le salon"
        access = [m for m in ctx.guild.members if chan.permissions_for(m).read_messages]

        embed = myembed(
            f"Info pour {type} {chan.name}",
            "",
            Link=chan.mention if isinstance(chan, TextChannel) else None,
            ID=chan.id,
            Have_access=f"{len(access)} members",
            Created=f"{crea.days} day{'s' * (crea.days > 1)} ago",
            Authorized=french_join(
                (
                    r.mention
                    for r, ov in chan.overwrites.items()
                    if isinstance(r, discord.Role) and ov.read_messages
                ),
                "ou",
            ),
            Auto_condition=rule.with_mentions() if rule is not None else None,
        )

        access.sort(key=lambda x: (-x.top_role.position, x.display_name))
        access = " ".join([m.mention for m in access if not m.bot]) + " + bots"
        if len(access) <= 1024:
            embed.add_field(name="Members", value=access)

        await ctx.send(embed=embed)

    async def send_emoji_info(self, ctx: Context, emoji: discord.Emoji):

        # Author can only be retreived this way
        emoji = await ctx.guild.fetch_emoji(emoji.id)

        created = datetime.datetime.now() - emoji.created_at

        embed = myembed(
            f"Info pour {str(emoji)}",
            "",
            Added=f"{created.days} day{'s' * (created.days > 1)} ago",
            Added_by=emoji.user.mention,
            ID=emoji.id,
            Mention=f"`{str(emoji)}`",
            Link=emoji.url,
        )

        embed.set_image(url=emoji.url)

        await ctx.send(embed=embed)

    @command(aliases=["pong"])
    async def ping(self, ctx):
        """Affiche la latence avec le bot."""

        msg: discord.Message = ctx.message
        rep = "Ping !" if "pong" in msg.content.lower() else "Pong !"

        ping = msg.created_at.timestamp()
        msg: discord.Message = await ctx.send(rep)
        pong = msg.created_at.timestamp()

        delta = pong - ping

        await msg.edit(content=rep + f" Ça a pris {int(1000 * (delta))}ms")

    # ----------------- Help ---------------- #

    @command(name="help", aliases=["h"])
    async def help_cmd(self, ctx: Context, *args):
        """Affiche des détails à propos d'une commande."""

        if not args:
            msg = await self.send_bot_help(ctx)
        else:
            msg = await self.send_command_help(ctx, args)

        await self.bot.wait_for_bin(ctx.author, msg)

    async def send_bot_help(self, ctx: Context):
        embed = discord.Embed(
            title="Aide pour EPFL-bot",
            description="Voici une liste des commandes utiles (ou pas) "
            "sur ce serveur. Pour avoir plus de détails il "
            "suffit d'écrire `!help COMMANDE` en remplacant `COMMANDE` "
            "par le nom de la commande, par exemple `!help help`.",
            color=EMBED_COLOR,
        )

        cog_getter = attrgetter("cog_name")
        commands = itertools.groupby(
            sorted(self.bot.walk_commands(), key=cog_getter), cog_getter
        )

        for cat_name, cat in commands:
            cat = {c.qualified_name: c for c in cat}
            cat = await self.filter_commands(
                ctx, list(cat.values()), sort=True, key=attrgetter("qualified_name")
            )

            if not cat:
                continue

            names = ["!" + c.qualified_name for c in cat]
            width = max(map(len, names))
            names = [name.rjust(width) for name in names]
            short_help = [c.short_doc for c in cat]

            lines = [f"`{n}` - {h}" for n, h in zip(names, short_help)]

            if cat_name is None:
                cat_name = "Autres"

            c: Command
            text = "\n".join(lines)
            embed.add_field(name=cat_name, value=text, inline=False)

        embed.set_footer(text="Suggestion ? Problème ? Envoie un message à @Diego")

        return await ctx.send(embed=embed)

    async def send_command_help(self, ctx, args):
        name = " ".join(args).strip("!")
        comm: Command = self.bot.get_command(name)
        if comm is None:
            return await ctx.send(
                f"La commande `!{name}` n'existe pas. "
                f"Utilise `!help` pour une liste des commandes."
            )
        elif isinstance(comm, Group):
            return await self.send_group_help(ctx, comm)

        embed = discord.Embed(
            title=f"Aide pour la commande `!{comm.qualified_name}`",
            description=comm.help,
            color=EMBED_COLOR,
        )

        if comm.aliases:
            aliases = ", ".join(f"`{a}`" for a in comm.aliases)
            embed.add_field(name="Alias", value=aliases, inline=True)
        if comm.signature:
            embed.add_field(
                name="Usage", value=f"`!{comm.qualified_name} {comm.signature}`"
            )
        embed.set_footer(text="Suggestion ? Problème ? Envoie un message à @Diego")

        return await ctx.send(embed=embed)

    async def send_group_help(self, ctx, group: Group):
        embed = discord.Embed(
            title=f"Aide pour le groupe de commandes `!{group.qualified_name}`",
            description=group.help,
            color=EMBED_COLOR,
        )

        comms = await self.filter_commands(ctx, group.commands, sort=True)
        if not comms:
            embed.add_field(
                name="Désolé", value="Il n'y a aucune commande pour toi ici."
            )
        else:
            names = ["!" + c.qualified_name for c in comms]
            width = max(map(len, names))
            just_names = [name.rjust(width) for name in names]
            short_help = [c.short_doc for c in comms]

            lines = [f"`{n}` - {h}" for n, h in zip(just_names, short_help)]

            c: Command
            text = "\n".join(lines)
            embed.add_field(name="Sous-commandes", value=text, inline=False)

            if group.aliases:
                aliases = ", ".join(f"`{a}`" for a in group.aliases)
                embed.add_field(name="Alias", value=aliases, inline=True)
            if group.signature:
                embed.add_field(
                    name="Usage", value=f"`!{group.qualified_name} {group.signature}`"
                )

            embed.add_field(
                name="Plus d'aide",
                value=f"Pour plus de détails sur une commande, "
                f"il faut écrire `!help COMMANDE` en remplaçant "
                f"COMMANDE par le nom de la commande qui t'intéresse.\n"
                f"Exemple: `!help {random.choice(names)[1:]}`",
            )
        embed.set_footer(text="Suggestion ? Problème ? Envoie un message à @Diego")

        return await ctx.send(embed=embed)

    def _name(self, command: Command):
        return f"`!{command.qualified_name}`"

    async def filter_commands(self, ctx, commands, *, sort=False, key=None):
        """|coro|

        Returns a filtered list of commands and optionally sorts them.

        This takes into account the :attr:`verify_checks` and :attr:`show_hidden`
        attributes.

        Parameters
        ------------
        commands: Iterable[:class:`Command`]
            An iterable of commands that are getting filtered.
        sort: :class:`bool`
            Whether to sort the result.
        key: Optional[Callable[:class:`Command`, Any]]
            An optional key function to pass to :func:`py:sorted` that
            takes a :class:`Command` as its sole parameter. If ``sort`` is
            passed as ``True`` then this will default as the command name.

        Returns
        ---------
        List[:class:`Command`]
            A list of commands that passed the filter.
        """

        if sort and key is None:
            key = lambda c: c.qualified_name

        iterator = (
            commands if self.show_hidden else filter(lambda c: not c.hidden, commands)
        )

        if not self.verify_checks:
            # if we do not need to verify the checks then we can just
            # run it straight through normally without using await.
            return sorted(iterator, key=key) if sort else list(iterator)

        # if we're here then we need to check every command if it can run
        async def predicate(cmd):
            try:
                return await cmd.can_run(ctx)
            except CommandError:
                return False

        ret = []
        for cmd in iterator:
            valid = await predicate(cmd)
            if valid:
                ret.append(cmd)

        if sort:
            ret.sort(key=key)
        return ret


def setup(bot: CustomBot):
    bot.add_cog(InfoCog(bot))
