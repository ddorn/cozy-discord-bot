#!/bin/python
from itertools import chain

from discord import Intents, MemberCacheFlags
from discord_slash import SlashCommand

from src.constants import *
from .engine import CustomBot


def start():
    # We allow "! " to catch people that put a space in their commands.
    # It must be in first otherwise "!" always match first and the space is not recognised
    bot = CustomBot(
        (PREFIX + " ", PREFIX),
        case_insensitive=True,
        owner_id=OWNER,
        intents=Intents.all(),
    )
    slash = SlashCommand(
        bot, sync_commands=True, sync_on_cog_reload=True
    )  # Declares slash commands through the client.

    # We have our own help command, so remove the existing one before loading it
    bot.remove_command("help")

    # Load all cogs in File.COGS and engine/
    for cog in chain(File.COGS.glob("*.py"), File.ENGINE.glob("*.py")):
        if not cog.name.startswith("_"):
            bot.load_extension(
                cog.relative_to(File.TOP_LEVEL).as_posix().replace("/", ".")[:-3]
            )

    # Let's goooo
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    start()
