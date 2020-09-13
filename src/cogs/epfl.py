import asyncio
from datetime import date
from typing import Union

import discord
from discord import TextChannel, PermissionOverwrite, Message, ChannelType
from discord.ext.commands import (
    command,
    has_role,
    Cog,
    Context,
    is_owner,
)
from discord.utils import get

from src.constants import *
from src.core import CustomBot
from src.errors import EpflError
from src.utils import fg, french_join, send_all, pprint_send


class EpflCog(Cog, name="Epfl stuff"):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    @command(name="mod3", aliases=["mod"])
    async def mod3_cmd(self, ctx: Context, sciper: int):
        """Calcule le modulo 3 d'un SCIPER..."""
        mess: Message = ctx.message

        emoji = ["0️⃣", "1️⃣", "2️⃣"][sciper % 3]
        await mess.add_reaction(emoji)

    @command(name="campus-day", aliases=["cd"])
    @send_all
    async def campus_day_cmd(self, ctx: Context, day: int=None, month: int=None):
        """Quel groupe est en présentiel ?"""
        first_day = date(2020, 9, 14)
        goal = date.today()

        if month:
            goal = goal.replace(month=month)
        if day:
            goal = goal.replace(day=day)
        if goal.month < 9:
            goal = goal.replace(year=2021)

        elapsed = (goal - first_day).days
        weeks, weekday = divmod(elapsed, 7)

        d = (weekday - weeks) % 3

        if day or month:
            if weekday >= 5:
                jour = "samedi" if weekday == 5 else "dimanche"
                yield f"Le {goal.day}/{goal.month}/{goal.year} est un {jour}... Le lundi ce sera le groupe { (d - (weekday==6)) % 3 }."
            else:
                yield f"Le {goal.day}/{goal.month}/{goal.year} ce sera le groupe {(d - (weekday == 6)) % 3} sur le campus."
        else:
            if weekday >= 5:  # weekend
                yield f"Lundi c'est le modulo { (d - (weekday==6)) % 3 } sur le campus."
            else:
                yield f"C'est le modulo {d} sur le campus aujourd'hui !"


def setup(bot: CustomBot):
    bot.add_cog(EpflCog(bot))
