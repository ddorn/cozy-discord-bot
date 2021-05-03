import asyncio
import re
import traceback
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pprint import pprint
from textwrap import indent
from typing import Tuple

import discord
from discord import Reaction, TextChannel, Message, ChannelType
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
from engine import (
    CustomBot,
    CozyError,
    fg,
    french_join,
    myembed,
    with_max_len,
    py,
)

from engine.utils import paginate

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


@dataclass
class EvalResult:
    query: str
    stdout: StringIO
    locals: dict
    result: object = None
    error: Exception = None

    page: int = 0
    show_locals: bool = False

    TRACKED_EMOJI = (
        Emoji.PREVIOUS,
        Emoji.NEXT,
        Emoji.ABACUS,  # Toggle showing the locals
    )

    def get_embed(self):
        if self.show_locals:
            embed, pages = self.embed_for_locals(self.page)
        elif self.error is not None:
            embed, pages = self.embed_for_error(self.page)
        else:
            embed, pages = self.embed_for_result(self.page)

        # Clamp
        self.page = max(0, min(pages - 1, self.page))

        return embed, pages

    def embed_for_locals(self, page):
        txt, pages = paginate(" - " + "\n - ".join(self.locals), page=page)
        embed = myembed(
            "Evaluation locals",
            f"There are {len(self.locals)} variables in the interpreter",
            discord.Colour.dark_gold(),
            _Variables=py(txt),
        )
        return embed, pages

    def embed_for_error(self, page=0):
        tb = StringIO()
        traceback.print_tb(self.error.__traceback__, file=tb)

        embed = discord.Embed(title=str(self.error), color=discord.Colour.red())
        embed.add_field(name="Query", value=py(with_max_len(self.query)), inline=False)
        embed.add_field(name="Traceback", value=py(with_max_len(tb)), inline=False)

        stdout = with_max_len(self.stdout)
        if stdout:
            embed.add_field(name="Standard output", value=py(stdout), inline=False)

        return embed, 1  # TODO: support pagination here too

    def embed_for_result(self, page=0):
        out = StringIO()
        pprint(self.result, out)

        embed = discord.Embed(title="Result", color=discord.Colour.green())
        embed.add_field(name="Query", value=py(with_max_len(self.query)), inline=False)

        value, pages1 = paginate(out, page=page)
        if self.result is not None and value:
            embed.add_field(name="Value", value=py(value), inline=False)

        stdout, pages2 = paginate(self.stdout, page=page)
        if stdout:
            embed.add_field(name="Standard output", value=py(stdout), inline=False)

        return embed, max(pages1, pages2)

    async def add_reactions(self, msg: Message, clear=False):
        for rea in self.TRACKED_EMOJI:
            if clear:
                await msg.clear_reaction(rea)
            else:
                await msg.add_reaction(rea)

    async def handle_reaction(self, ctx, bot_msg, reaction: Reaction):
        e = reaction.emoji
        if e not in self.TRACKED_EMOJI:
            return
        elif e == Emoji.NEXT:
            self.page += 1
        elif e == Emoji.PREVIOUS:
            self.page -= 1
        elif e == Emoji.ABACUS:
            self.show_locals = not self.show_locals
            self.page = 0
        else:
            raise ValueError("Match doesn't cover all cases.")

        await reaction.remove(ctx.author)

        await self.send_embed(ctx, edit=bot_msg)

    async def send_embed(self, ctx, edit=None, footer=True):
        embed, pages = self.get_embed()

        f = ""
        if footer:
            f = "You may edit your message. "
        if pages > 1:
            f += f"Page {self.page + 1}/{pages}"
        if f:
            embed.set_footer(text=f)

        if edit is None:
            bot_msg = await ctx.send(embed=embed)
        else:
            bot_msg = edit
            await edit.edit(embed=embed)

        await self.add_reactions(bot_msg)

        return bot_msg


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

    async def _format_msg_for_eval(self, msg: Message) -> Tuple[str, str]:
        content: str = msg.content
        for p in await self.bot.get_prefix(msg):
            if content.startswith(p):
                content = content[len(p) :]
                break

        match = re.match(RE_QUERY, content)
        if not match:
            raise CozyError("Your query was not understood.")

        query = match.group("query")
        if not query:
            raise CozyError("Your query was not understood.")

        if any(word in query for word in ("=", "return", "await", ":", "\n", "import")):
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

        return full_query, query

    def _get_globals_for_exec(self, msg):
        # Variables for ease of access in eval
        guild: discord.Guild = msg.guild
        channel: TextChannel = msg.channel
        if guild:
            roles = guild.roles
            members = guild.members
            categories = guild.categories
        send = lambda text: asyncio.create_task(channel.send(text))
        globs = {**globals(), **locals(), **self.eval_locals}

        return globs

    async def eval(self, msg) -> EvalResult:
        try:
            full_query, pretty_query = await self._format_msg_for_eval(msg)
        except CozyError as e:
            return myembed(e.message)

        globs = self._get_globals_for_exec(msg)

        stdout = StringIO()

        try:
            with redirect_stdout(stdout):
                if "\n" in full_query:
                    locs = {}
                    exec(full_query, globs, locs)
                    resp = await locs["query"]()
                else:
                    resp = eval(full_query, globs)
        except Exception as e:
            return EvalResult(full_query, stdout, self.eval_locals, error=e)
        else:
            return EvalResult(pretty_query, stdout, self.eval_locals, result=resp)

    @command(name="eval", aliases=["e"])
    @is_owner()
    async def eval_cmd(self, ctx: Context):
        """(dev) Evaluate the entry."""

        self.eval_locals["ctx"] = ctx

        result = await self.eval(ctx.message)
        bot_msg = await result.send_embed(ctx)

        def check(before, after):
            return after.id == ctx.message.id

        def check_rea(reaction: Reaction, user):
            return user == ctx.author and reaction.message.id == bot_msg.id

        while True:
            try:
                done, pending = await asyncio.wait(
                    [
                        self.bot.wait_for("message_edit", check=check, timeout=600),
                        self.bot.wait_for("reaction_add", check=check_rea, timeout=600),
                    ],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                done = list(done)[0].result()
                if isinstance(done[0], Reaction):
                    reaction, user = done
                    await result.handle_reaction(ctx, bot_msg, reaction)
                else:
                    before, after = done
                    result = await self.eval(after)
                    bot_msg = await result.send_embed(ctx, edit=bot_msg)

            except asyncio.TimeoutError:
                break

        try:
            # Remove the "You may edit your message"
            await result.send_embed(ctx, edit=bot_msg, footer=False)
            await result.add_reactions(bot_msg, clear=True)
        except discord.NotFound:
            pass

    @command(name="eval-details", aliases=["ed"])
    @is_owner()
    async def eval_details_cmd(self, ctx: Context, name):
        """Show attributes of an object in the interpreter."""

        g = self._get_globals_for_exec(ctx.message)
        if name not in g:
            embed = myembed(
                "Variable not found.",
                "Here is a list of all the variables",
                _Variables=py(" ".join(g)),
            )
        else:
            obj = g[name]

            attrs = getattr(obj, "__dict__", getattr(obj, "__slots__", []))
            attrs = [a for a in attrs if not a.startswith("_")]
            types = {k: type(getattr(obj, k)).__name__ for k in attrs}
            values = [py(getattr(obj, attr)) for attr in attrs]
            data = sorted(zip(attrs, values), key=lambda x: len(x[1]))

            embed = myembed(
                f"Variable {name}",
                _repr=py(repr(obj)),
                type=py(type(obj)),
                **{"_" * (len(v) > 30) + f"`{k}` (`{types[k]}`)": v for k, v in data},
            )

        await ctx.send(embed=embed)

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
