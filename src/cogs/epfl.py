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
)
from discord.utils import get
from ptpython.repl import embed

from src.constants import *
from src.core import CustomBot
from src.errors import EpflError
from src.utils import fg, french_join


class EpflCog(Cog, name="Epfl stuff"):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    @command(name="mod3", aliases=["mod"])
    async def mod3_cmd(self, ctx: Context, sciper: int):
        """Calcule le modulo 3 d'un SCIPER..."""
        mess: Message = ctx.message

        emoji = ["0️⃣", "1️⃣", "2️⃣"][sciper % 3]
        await mess.add_reaction(emoji)


def setup(bot: CustomBot):
    bot.add_cog(EpflCog(bot))
