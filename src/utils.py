import asyncio
from pprint import pprint
from functools import wraps
from io import StringIO, BytesIO
from time import time
from typing import Union, Optional

import discord
import psutil
from discord.ext.commands import Bot

from src.constants import *


def fg(text, color: int = 0xFFA500):
    r = color >> 16
    g = color >> 8 & 0xFF
    b = color & 0xFF
    return f"\033[38;2;{r};{g};{b}m{text}\033[m"


def french_join(l):
    l = list(l)
    if not l:
        return ""
    if len(l) == 1:
        return l[0]
    start = ", ".join(str(i) for i in l[:-1])
    return f"{start} et {l[-1]}"


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
        msg = await ctx.send(f"{descr}: NaN/{len(l)}")
        start = time()
        for i, x in enumerate(l):
            yield x

            if i > 0 and i % step == 0:
                now = time()
                elapsed = round(now - start, 2)
                remain = round((now - start) / i * len(l), 2)
                await msg.edit(
                    f"{descr}: {i}/{len(l)}, elapsed {elapsed}s, remaining {remain}s."
                )



def myembed(title, descr="", **fields):
    embed = discord.Embed(
        color=EMBED_COLOR,
        title=title,
        description=descr,
    )

    if fields:
        for name, value in fields.items():
            value = str(value)
            if value:
                embed.add_field(name=name, value=value)

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


def setup(bot: Bot):
    pass
