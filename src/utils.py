import re
from functools import wraps
from io import StringIO
from pprint import pprint
from time import time
from typing import Optional, Union, Type, TYPE_CHECKING

import discord
import psutil
from discord.ext import commands
from discord.ext.commands import Bot, Context, NoPrivateMessage

from src.constants import *
from src.errors import EplfOnlyError, ConfigUndefined

if TYPE_CHECKING:
    from src.core import CogConfig, Undefined


def fg(text, color: int = 0xFFA500):
    r = color >> 16
    g = color >> 8 & 0xFF
    b = color & 0xFF
    return f"\033[38;2;{r};{g};{b}m{text}\033[m"


def py(txt):
    """
    Suround a text in a python code block for discord formatting.
    If there is no text, returns the empty string.
    """
    if not txt:
        return ""
    return f"```py\n{txt}```"


def french_join(l, last_link="et", sep=', '):
    l = list(l)
    if not l:
        return ""
    if len(l) == 1:
        return l[0]
    start = sep.join(str(i) for i in l[:-1])
    return f"{start} {last_link} {l[-1]}"


def mentions_to_id(s: str) -> str:
    """
    Remove all mentions from a string and replace them with IDs.

    Does not work with plain text mentions like @everyone and @here.
    """
    return re.sub(r"<[@#][&!]?([0-9]{18,21})>", r"\1", s)


def get_casefold(seq, **attrs):
    """Return the first element of a list whose attr is casefold equal to the value.

    Example:
        >>> get_casefold(members, name="Diego")
    """

    assert len(attrs) == 1
    k, v = attrs.popitem()
    v = v.casefold()
    for x in seq:
        if getattr(x, k).casefold() == v:
            return x


def has_role(member, role: Union[str, tuple]):
    """Return whether the member has a role with this name."""

    if isinstance(role, str):
        return any(r.name == role for r in member.roles)
    else:
        return any(r.name == rol for r in member.roles for rol in role)


def send_and_bin(f):
    """
    Decorator that allows a command in a cog to just return
    the messages that needs to be sent, and allow the author that
    trigger the message de delete it.
    """

    @wraps(f)
    async def wrapped(cog, ctx, *args, **kwargs):
        msg = await f(cog, ctx, *args, **kwargs)
        if msg:
            msg = await ctx.send(msg)
            await cog.bot.wait_for_bin(ctx.author, msg)

    return wrapped


async def pprint_send(ctx, *objs, **nobjs):
    embed = discord.Embed(title="Debug")

    nobjs.update({f"Object {i}": o for i, o in enumerate(objs)})

    for name, obj in nobjs.items():
        out = StringIO()
        pprint(obj, out)
        out.seek(0)
        value = out.read()
        if len(value) > 1000:
            value = value[:500] + "\n...\n" + value[-500:]
        value = f"```py\n{value}\n```"
        embed.add_field(name=name, value=value)
    return await ctx.send(embed=embed)


async def confirm(ctx, bot, prompt="", **kwargs):
    msg: discord.Message = await ctx.send(prompt, **kwargs)
    await msg.add_reaction(Emoji.CHECK)
    await msg.add_reaction(Emoji.CROSS)

    def check(reaction: discord.Reaction, u):
        return (
                ctx.author == u
                and msg.id == reaction.message.id
                and str(reaction.emoji) in (Emoji.CHECK, Emoji.CROSS)
        )

    reaction, u = await bot.wait_for("reaction_add", check=check)

    if str(reaction) == Emoji.CHECK:
        await msg.clear_reaction(Emoji.CROSS)
        return True
    else:
        await msg.clear_reaction(Emoji.CHECK)
        return False


async def report_progress(it, ctx, descr="Progress", mini=50, step=10):
    l = list(it)
    if len(l) < mini:
        for x in l:
            yield x
    else:
        msg = await ctx.send(f"{descr}: 0/{len(l)}")
        start = time()
        for i, x in enumerate(l):
            yield x

            if i > 0 and i % step == 0:
                now = time()
                elapsed = round(now - start, 2)
                remain = round((now - start) / i * len(l) - elapsed, 2)
                await msg.edit(
                    content=f"{descr}: {i}/{len(l)}, elapsed {elapsed}s, remaining {remain}s."
                )
        await msg.edit(
            content=f"{descr}: {len(l)}/{len(l)}, total {round(time() - start)}sec."
        )


def myembed(title, descr="", color=EMBED_COLOR, **fields):
    """
    Create an embed in one function.

    If you prefix a field by an underscore, the field will not be inline.
    Underscores are replaced with spaces in fields names.
    """

    embed = discord.Embed(
        color=color,
        title=title,
        description=descr,
    )

    for name, value in fields.items():
        if value not in (None, ""):
            val = str(value)
            view_name = name.replace("_", " ")
            embed.add_field(name=view_name, value=val, inline=not name.startswith("_"))

    return embed


def send_all(f):
    """Decorator that send each text message that a command in a cog yields."""

    @wraps(f)
    async def wrapper(self, ctx, *args, **kwargs):
        async for msg in f(self, ctx, *args, **kwargs):
            await ctx.send(msg)

    return wrapper


def with_max_len(string: Union[str, StringIO], maxi=1000) -> str:
    if isinstance(string, StringIO):
        string.seek(0)
        string = string.read()

    if len(string) > maxi:
        string = string[:maxi // 2 - 3] + "\n...\n" + string[-maxi // 2 + 3:]

    return string


def section(m: discord.Member) -> Optional[str]:
    """Get the section sigle for a member."""

    for s in SECTIONS:
        for r in m.roles:
            if r.name.startswith(s):
                return s
    return None


def start_time():
    return psutil.Process().create_time()


# A collection of useful checks


def official_guild():
    """A check that passes only of the command is invoked in the EPFL Community guild."""

    def predicate(ctx: Context):
        if ctx.guild is None or ctx.guild.id != EPFL_GUILD:
            raise EplfOnlyError()
        return True

    return commands.check(predicate)


def setup(bot: Bot):
    pass
