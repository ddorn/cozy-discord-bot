import asyncio
import re
import traceback
from contextlib import redirect_stdout
from io import StringIO
from pprint import pprint
from textwrap import indent

import discord
from discord import TextChannel, Message, ChannelType
from discord.ext.commands import (
    command,
    Cog,
    ExtensionNotLoaded,
    Context,
    is_owner,
    ExtensionFailed,
)
from ptpython.repl import embed

from src.constants import *
from engine import CustomBot, CozyError, fg, french_join, with_max_len, py

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
    r"^e(val)?[ \n]+(`{1,3}(py(thon)?\n)?)?(?P<query>.*?)\n?(`{1,3})?\n?$", re.DOTALL,
)


class DevCog(Cog, name="Dev tools"):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.eval_locals = {}

    @command(name="interrupt")
    @is_owner()
    async def interrupt_cmd(self, ctx):
        """
        (dev) Open a console where a @dev has called it :warning:

        Use as last resource:
         - the bot will be inctive during that time
         - all commands will be executed when they are picked up
        """

        await ctx.send(
            "I was shut down and an interactive console was opened where I am running."
            "All commands will fail while this console is open.\n"
            "Be quick, I hate open heart surgery ... :confounded:"
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

        await ctx.send("Everything is going better!")

    @command()
    @is_owner()
    async def byebye(self, ctx):
        """Exit the bot."""
        raise SystemExit()

    # ------------- Extensions -------------- #

    @staticmethod
    def full_cog_name(name):
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
        (dev) Reloads one or more extensions.

        Without an argument, reloads the bot itself
        but without touching the extensions (black magic).

        To be used when the code changes. Arguments
        possible: names of the python modules or just
        the name of the cogs. Some abbreviations exist.
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
        (dev) Add a category of commands.

        Allows you to dynamically add a cog without restarting the bot.
        """
        name = self.full_cog_name(name)

        try:
            self.bot.load_extension(name)
        except:
            await ctx.message.add_reaction(Emoji.CROSS)
            raise
        else:
            await ctx.message.add_reaction(Emoji.CHECK)

    # ---------------- Eval ----------------- #

    async def eval(self, msg: Message) -> discord.Embed:
        # Variables for ease of access in eval
        guild: discord.Guild = msg.guild
        channel: TextChannel = msg.channel
        if guild:
            roles = guild.roles
            members = guild.members
            categories = guild.categories
        send = lambda text: asyncio.create_task(channel.send(text))

        content: str = msg.content
        for p in await self.bot.get_prefix(msg):
            if content.startswith(p):
                content = content[len(p) :]
                break

        query = re.match(RE_QUERY, content).group("query")

        if not query:
            raise CozyError("No query found.")

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
            embed.add_field(name="Traceback", value=py(with_max_len(tb)), inline=False)
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
        """(dev) Evaluate the entry."""

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

    # -------------- Listeners --------------- #

    @Cog.listener()
    async def on_message(self, msg: Message):
        ch: TextChannel = msg.channel
        if ch.type == ChannelType.private:
            m = f"""{fg(msg.author.name)}: {msg.content}
MSG_ID: {fg(msg.id, 0x03A678)}
CHA_ID: {fg(msg.channel.id, 0x03A678)}"""
            print(m)

            # Log recieved messages
            if msg.author.id != self.bot.user.id:
                await self.bot.info(
                    "Private Message",
                    msg.content,
                    From=msg.author.mention,
                    Message_ID=msg.id,
                    Channel_ID=msg.channel.id,
                )

    @Cog.listener()
    async def on_message_delete(self, msg: Message):
        if msg.role_mentions or msg.mentions:
            # log all deleted message with mentions,
            # to avoid ghost pings
            await self.bot.info(
                "Deleted message with mention",
                msg.content,
                Sent_by=msg.author.mention,
                At=msg.created_at.ctime(),
                In=msg.channel.mention,
            )


def setup(bot: CustomBot):
    bot.add_cog(DevCog(bot))
