import asyncio
import re
import traceback
from contextlib import redirect_stdout
from io import StringIO
from pprint import pprint
from textwrap import indent
from typing import Union

import discord
from discord import TextChannel, PermissionOverwrite, Message, ChannelType
from discord.ext.commands import (
    command,
    has_role,
    Cog,
    ExtensionNotLoaded,
    Context,
    is_owner,
    ExtensionFailed)
from discord.utils import get
from ptpython.repl import embed

from src.constants import *
from src.core import CustomBot
from src.errors import EpflError
from src.utils import fg, french_join, send_all, with_max_len, pprint_send, py

COGS_SHORTCUTS = {
    "c": "src.constants",
    "d": "dev",
    "e": "epfl",
    "en": "enigma",
    "m": "misc",
    "o": "orga",
    "p": "perms",
    "r": "errors",
    "re": "remind",
    "ro": "rooms",
    "s": "settings",
    "u": "src.utils",
    "v": "dev",
}

RE_QUERY = re.compile(
    r"^" + PREFIX + " ?e(val)?[ \n]+(`{1,3}(py(thon)?\n)?)?(?P<query>.*?)\n?(`{1,3})?\n?$", re.DOTALL
)


class DevCog(Cog, name="Dev tools"):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.eval_locals = {}
        self.power_warn_on = False

    @command(name="interrupt")
    @is_owner()
    async def interrupt_cmd(self, ctx):
        """
        (dev) Ouvre une console là où un @dev m'a lancé. :warning:

        A utiliser en dernier recours:
         - le bot sera inactif pendant ce temps.
         - toutes les commandes seront executées à sa reprise.
        """

        await ctx.send(
            "J'ai été arrêté et une console interactive a été ouverte là où je tourne. "
            "Toutes les commandes rateront tant que cette console est ouverte.\n"
            "Soyez rapides, je déteste les opérations à coeur ouvert... :confounded:"
        )

        # Utility functions

        def send(msg, channel=None):
            if isinstance(channel, int):
                channel = self.bot.get_channel(channel)

            channel = channel or ctx.channel
            asyncio.create_task(channel.send(msg))

        try:
            await embed(
                globals(), locals(), vi_mode=True, return_asyncio_coroutine=True
            )
        except EOFError:
            pass

        await ctx.send("Tout va mieux !")

    def full_cog_name(self, name):
        name = COGS_SHORTCUTS.get(name, name)
        if not "." in name:
            name = f"src.cogs.{name}"

        return name

    @command(
        name="reload", aliases=["r"], usage=f"[{'|'.join(COGS_SHORTCUTS.values())}]"
    )
    @is_owner()
    async def reload_cmd(self, ctx, *names):
        """
        (dev) Recharge une ou plusieurs extensions.

        Ne pas passer d'argument recharge le bot lui même
        mais sans toucher aux extensions (magie noire).

        A utiliser quand le code change. Arguments
        possibles: noms des modules python ou juste
        le nom des cogs. Certaines abbréviations existent.
        """

        if not names:
            self.bot.reload()
            working = 0
            failed = []
            last_ex = None
            for ex in list(self.bot.extensions):
                try:
                    self.bot.reload_extension(ex)
                except ExtensionFailed as e:
                    failed.append(f"`{ex}`")
                    last_ex = e
                else:
                    working += 1
            msg = f":tada: The bot was reloaded ! With {working} extensions."
            if failed:
                msg += " But " + french_join(failed, "and") + " failed."
            await ctx.send(msg)
            if last_ex:
                raise last_ex
            return

        for name in names:
            name = self.full_cog_name(name)

            if name == "src.cogs.dev":
                self.power_warn_on = False  # Shut it down

            try:
                self.bot.reload_extension(name)
            except ExtensionNotLoaded:
                await ctx.invoke(self.load_cmd, name)
                return
            except:
                await ctx.message.add_reaction(Emoji.CROSS)
                raise
        else:
            await ctx.message.add_reaction(Emoji.CHECK)

    @command(name="load", aliases=["l"])
    @is_owner()
    async def load_cmd(self, ctx, name):
        """
        (dev) Ajoute une catégorie de commandes.

        Permet d'ajouter dynamiquement un cog sans redémarrer le bot.
        """
        name = self.full_cog_name(name)

        try:
            self.bot.load_extension(name)
        except:
            await ctx.message.add_reaction(Emoji.CROSS)
            raise
        else:
            await ctx.message.add_reaction(Emoji.CHECK)

    @command(name="send")
    @is_owner()
    async def send_cmd(self, ctx, *msg):
        """(dev) Envoie un message."""
        await ctx.message.delete()
        await ctx.send(" ".join(msg))

    @command(name="del")
    @has_role(Role.MODO)
    async def del_range_cmd(self, ctx: Context, id1: Message, id2: Message):
        """
        (modo) Supprime les messages entre les deux IDs en argument.

        Pour optenir les IDs des messages il faut activer le mode developpeur
        puis clic droit > copier l'ID.

        `id1` est le message le plus récent à supprimer.
        `id2` est le message le plus ancien.

        Il est impossible de supprimer plus de 100 messages d'un coup.
        """

        channel: TextChannel = id1.channel
        to_delete = [
                        message async for message in channel.history(before=id1, after=id2)
                    ] + [id1, id2]
        await channel.delete_messages(to_delete)
        await ctx.message.delete()

    async def eval(self, msg: Message) -> discord.Embed:
        # Variables for ease of access in eval
        guild: discord.Guild = msg.guild
        channel: TextChannel = msg.channel
        if guild:
            roles = guild.roles
            members = guild.members
            categories = guild.categories
        send = lambda text: asyncio.create_task(channel.send(text))

        query = re.match(RE_QUERY, msg.content).group("query")

        if not query:
            raise EpflError("No query found.")

        if any(word in query for word in ("=", "return", "await", ":", "\n")):
            lines = query.splitlines()
            if (
                    "return" not in lines[-1]
                    and "=" not in lines[-1]
                    and not lines[-1].startswith(" ")
            ):
                lines[-1] = f"return {lines[-1]}"
                query = "\n".join(lines)
            full_query = f"""async def query():
    try:
{indent(query, " " * 8)}
    finally:
        self.eval_locals.update(locals())
"""
        else:
            full_query = query

        globs = {**globals(), **locals(), **self.eval_locals}
        stdout = StringIO()

        try:
            with redirect_stdout(stdout):
                if "\n" in full_query:
                    locs = {}
                    exec(full_query, globs, locs)
                    resp = await locs["query"]()
                else:
                    resp = eval(query, globs)
        except Exception as e:
            tb = StringIO()
            traceback.print_tb(e.__traceback__, file=tb)

            embed = discord.Embed(title=str(e), color=discord.Colour.red())
            embed.add_field(
                name="Query", value=py(with_max_len(full_query)), inline=False
            )
            embed.add_field(
                name="Traceback", value=py(with_max_len(tb)), inline=False
            )
        else:
            out = StringIO()
            pprint(resp, out)

            embed = discord.Embed(title="Result", color=discord.Colour.green())
            embed.add_field(name="Query", value=py(with_max_len(query)), inline=False)

            value = with_max_len(out)
            if resp is not None and value:
                embed.add_field(name="Value", value=py(value), inline=False)

        stdout = with_max_len(stdout)
        if stdout:
            embed.add_field(name="Standard output", value=py(stdout), inline=False)

        embed.set_footer(text="You may edit your message.")
        return embed

    @command(name="eval", aliases=["e"])
    @is_owner()
    async def eval_cmd(self, ctx: Context):
        """(dev) Evalue l'entrée."""

        self.eval_locals["ctx"] = ctx

        embed = await self.eval(ctx.message)
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

            embed = await self.eval(after)
            await resp.edit(embed=embed)

        # Remove the "You may edit your message"
        embed.set_footer()
        try:
            await resp.edit(embed=embed)
        except discord.NotFound:
            pass

    @Cog.listener()
    async def on_message(self, msg: Message):
        ch: TextChannel = msg.channel
        if ch.type == ChannelType.private:
            m = f"""{fg(msg.author.name)}: {msg.content}
MSG_ID: {fg(msg.id, 0x03A678)}
CHA_ID: {fg(msg.channel.id, 0x03A678)}"""
            print(m)

    @command(name="warn-power", aliases=["wp"])
    @is_owner()
    @send_all
    async def warn_power_cmd(self, ctx: Context):
        """(owner) Warn the owner when the server is unplugged."""

        self.power_warn_on = not self.power_warn_on

        await ctx.message.add_reaction(Emoji.CHECK)

        if not self.power_warn_on:
            # To prevent double message on deactivation
            return

        online = "1"
        while self.power_warn_on:
            await asyncio.sleep(20)
            with open("/sys/class/power_supply/AC/online") as f:
                now = f.read().strip()

            if online != now:
                online = now
                if online == "1":
                    yield "Le serveur est à nouveau branché sur le secteur !"
                else:
                    yield f":warning: {ctx.author.mention} Le serveur est sur batterie ! :warning:"

        yield "I stopped checking the power supply."


def setup(bot: CustomBot):
    bot.add_cog(DevCog(bot))
