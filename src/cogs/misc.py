import ast
import asyncio
import datetime
import io
import itertools
import math
import operator as op
import random
import re
import traceback
import urllib
from itertools import chain
from math import factorial
from operator import attrgetter
from time import time
from typing import List

import aiohttp
import discord
from discord import Guild, Member, TextChannel, ChannelType, GroupChannel, VoiceChannel, CategoryChannel
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import (Cog, command, Command, CommandError, Context, Group, guild_only)
from discord.utils import get

from src.cogs.perms import RuleSet
from src.constants import *
from src.core import CustomBot
from src.errors import EpflError
from src.utils import mentions_to_id, myembed, section, start_time, with_max_len, french_join

# supported operators
OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.FloorDiv: op.floordiv, ast.Mod: op.mod,
    ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
    ast.USub: op.neg, "abs": abs, "π": math.pi, "τ": math.tau,
    "i": 1j, "fact": factorial,
}

for name in dir(math):
    if not name.startswith("_"):
        OPS[name] = getattr(math, name)

class MiscCog(Cog, name="Divers"):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.show_hidden = False
        self.verify_checks = True
        self.computing = False  # Fractal

    @command(
        name="choose",
        usage='choix1 choix2 "choix 3"...',
        aliases=["choice", "choix", "ch"],
    )
    async def choose(self, ctx: Context, *args):
        """
        Choisit une option parmi tous les arguments.

        Pour les options qui contiennent une espace,
        il suffit de mettre des guillemets (`"`) autour.
        """

        choice = random.choice(args)
        msg = await ctx.send(f"J'ai choisi... **{choice}**")
        await self.bot.wait_for_bin(ctx.author, msg),

    @guild_only()
    @command(name="info", aliases=["status"])
    async def info_cmd(self, ctx: Context, *, what: str=None):
        """Affiche des informations à propos du serveur ou de l'argument."""

        if what is None:
            return await self.send_server_info(ctx)

        guild: Guild = ctx.guild
        what_ = what
        what = what.strip()

        # try to convert it to an id
        what = mentions_to_id(what)
        try:
            what = int(what)
            obj = guild.get_channel(what) or guild.get_role(what) or guild.get_member(what)
        except ValueError:
            obj = guild.get_member_named(what) or get(guild.roles, name=what) or get(guild.channels, name=what)

            # Last try: casefold comp
            what = what.casefold()
            for r in chain(guild.roles, guild.channels, guild.members):
                if r.name.casefold() == what:
                    obj = r
                    break

        if isinstance(obj, GuildChannel) and not obj.permissions_for(ctx.author).read_messages:
            obj = None

        if obj is None:
            raise EpflError(f"Could not understand what {what_} is.")

        if isinstance(obj, discord.Role):
            return await self.send_role_info(ctx, obj)
        elif isinstance(obj, discord.Member):
            return await self.send_member_info(ctx, obj)
        else:
            return await self.send_channel_info(ctx, obj)

    async def send_server_info(self, ctx):
        guild: Guild = ctx.guild
        embed = discord.Embed(title="État du serveur", color=EMBED_COLOR)
        in_sections = [g for g in guild.members if section(g) is not None]
        no_year = [g for g in guild.members if get(g.roles, name="No year")]
        uptime = datetime.timedelta(seconds=round(time() - start_time()))
        text = len(guild.text_channels)
        vocal = len(guild.voice_channels)
        infos = {
            "Etudiants": len(in_sections),
            "Sans année": len(no_year),
            "Membres": len(guild.members),
            "Salons texte": text,
            "Salons vocaux": vocal,
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

        age = (datetime.datetime.now() - role.created_at)
        d = age.days

        embed = myembed(
            f"Info pour le role {role.name}",
            "",
            role.color,
            Mention=role.mention,
            ID=role.id,
            Members=len(role.members),
            # Creation=role.created_at.ctime(),
            Created=f"{d} day{'s'*(d > 1)} ago",
            Mentionable="Yes" if role.mentionable else "No",
            Position=role.position,
            Auto_condition=rule.with_mentions() if rule is not None else "",
        )

        await ctx.send(embed=embed)

    async def send_member_info(self, ctx: Context, member: Member):

        member_since = datetime.datetime.now() - member.joined_at

        embed = myembed(
            f"Info pour {member.display_name}",
            "",
            member.color,
            Mention=member.mention,
            ID=member.id,
            Top_role=member.top_role.mention,
            Member_for=f"{member_since.days} day{'s' * (member_since.days > 1)}",
            Booster_since=member.premium_since,
            _Roles=french_join(r.mention for r in reversed(member.roles[1:])),
        )

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
            Created=f"{crea.days} day{'s'*(crea.days > 1)} ago",
            Authorized=french_join((r.mention
                                  for r, ov in chan.overwrites.items()
                                  if isinstance(r, discord.Role) and ov.read_messages), "ou"),
            Auto_condition=rule.with_mentions() if rule is not None else None,
        )
        await ctx.send(embed=embed)

    @guild_only()
    @commands.has_role(Role.MODO)
    @command(name="temp-hide", aliases=["th"])
    async def temp_hide_cmd(self, ctx: Context, duration:int =60):
        """
        (modo) Hide the channel for a given time. Useful to prevent pings.

        The channel is hidden for a default of 60s and can be made visible
        again earlier by deleting the `!temp-hide` message.

        Works only on channels with less than 10 permissions.
        """

        chan: GuildChannel = ctx.channel
        if isinstance(chan, GuildChannel):
            perms = chan.overwrites

            if len(perms) > 10:
                raise EpflError("Cannot hide a channel with more than 10 permissions.")

            await chan.set_permissions(ctx.author, read_messages=True)
            await chan.set_permissions(ctx.guild.default_role, read_messages=False)
            for p in perms:
                if p not in (ctx.guild.default_role, ctx.author):
                    await chan.set_permissions(p, overwrite=None)

            await self.bot.wait_for_bin(ctx.author, ctx.message, timeout=duration)

            await chan.set_permissions(ctx.author, overwrite=None)
            for p, perm in perms.items():
                await chan.set_permissions(p, overwrite=perm)

    @command(hidden=True)
    async def fractal(self, ctx: Context):
        """Dessine une fractale aléatoire."""
        if self.computing:
            return await ctx.send("Il y a déjà une fractale en cours de calcul...")

        try:
            self.computing = True

            await ctx.message.add_reaction(Emoji.CHECK)
            msg: discord.Message = ctx.message
            seed = msg.content[len("!fractal ") :]
            seed = seed or str(random.randint(0, 1_000_000_000))
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    FRACTAL_URL.format(seed=urllib.parse.quote(seed)), timeout=120
                ) as resp:
                    if resp.status != 200:
                        print(resp)
                        return await ctx.send(
                            "Il y a un problème pour calculer/télécharger l'image..."
                        )
                    data = io.BytesIO(await resp.read())
                    await ctx.send(
                        f"Seed: {seed}", file=discord.File(data, f"{seed}.png")
                    )
        finally:
            self.computing = False

    @command(aliases=["pong"])
    async def ping(self, ctx):
        """Affiche la latence avec le bot."""

        msg: discord.Message = ctx.message
        rep = "Ping !" if "pong" in msg.content.lower() else "Pong !"

        ping = msg.created_at.timestamp()
        msg: discord.Message = await ctx.send(rep)
        pong = msg.created_at.timestamp()

        delta = pong - ping

        await msg.edit(content=rep+f" Ça a pris {int(1000 * (delta))}ms")

    # ---------------- Calc ----------------- #

    @command(name="calc", aliases=["="])
    async def calc_cmd(self, ctx, *args):
        """Effectue un calcul simple"""
        with_tb = ctx.author.id == OWNER
        embed = self._calc(ctx.message.content, with_tb)
        resp = await ctx.send(embed=embed)

        def check(before, after):
            return after.id == ctx.message.id

        while True:
            try:
                before, after = await self.bot.wait_for(
                    "message_edit", check=check, timeout=600
                )
            except asyncio.TimeoutError:
                break

            embed = self._calc(after.content, with_tb)
            await resp.edit(embed=embed)

        # Remove the "You may edit your message"
        embed.set_footer()
        try:
            await resp.edit(embed=embed)
        except discord.NotFound:
            pass

    def _calc(self, query: str, with_tb=False):

        for prefix in (PREFIX + " ", PREFIX, "calc", "="):
            if query.startswith(prefix):
                query = query[len(prefix):]
        # Replace implicit multiplication by explicit *
        query = re.sub(r"\b((\d)+(\.\d+)?)(?P<name>[a-zA-Z]+)\b", r"\1*\4", query)

        query = query.strip().strip("`")

        ex = None
        result = 42
        try:
            result = self._eval(ast.parse(query, mode='eval').body)
        except Exception as e:
            ex = e

        if isinstance(result, complex):
            if abs(result.imag) < 1e-12:
                result = result.real
            else:
                r, i = result.real, result.imag
                r = r if abs(int(r) - r) > 1e-12 else int(r)
                i = i if abs(int(i) - i) > 1e-12 else int(i)
                if not r:
                    result = f"{i if i != 1 else ''}i"
                else:
                    result = f"{r}{i if i != 1 else '':+}i"
        if isinstance(result, float):
            result = round(result, 12)

        embed = discord.Embed(title=discord.utils.escape_markdown(query), color=EMBED_COLOR)
        # embed.add_field(name="Entrée", value=f"`{query}`", inline=False)
        embed.add_field(name="Valeur", value=f"`{with_max_len(str(result), 1022)}`", inline=False)
        if ex and with_tb:
            embed.add_field(name="Erreur", value=f"{ex.__class__.__name__}: {ex}", inline=False)
            trace = io.StringIO()
            traceback.print_exception(type(ex), ex, ex.__traceback__, file=trace)
            trace.seek(0)
            embed.add_field(name="Traceback", value=f"```\n{trace.read()}```")
        embed.set_footer(text="You may edit your message")

        return embed

    def _eval(self, node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return OPS[type(node.op)](self._eval(node.left), self._eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return OPS[type(node.op)](self._eval(node.operand))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return OPS[node.func.id](*(self._eval(n) for n in node.args), **{k.arg: self._eval(k.value) for k in node.keywords})
        elif isinstance(node, ast.Name):
            return OPS[node.id]

        fields = ", ".join(
            f"{k}={getattr(node, k).__class__.__name__}" for k in node._fields
        )
        raise TypeError(f"Type de noeud non supporté: {node.__class__.__name__}({fields})")

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
        commands = itertools.groupby(sorted(self.bot.walk_commands(), key=cog_getter), cog_getter)

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
    bot.add_cog(MiscCog(bot))
