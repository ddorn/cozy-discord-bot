#!/bin/python

from src.constants import *
from src.core import CustomBot


def start():
    # We allow "! " to catch people that put a space in their commands.
    # It must be in first otherwise "!" always match first and the space is not recognised
    bot = CustomBot((PREFIX + " ", PREFIX), case_insensitive=True, owner_id=OWNER)

    @bot.event
    async def on_ready():
        print(f"{bot.user} has connected to Discord!")

    bot.remove_command("help")
    bot.load_extension("src.cogs.dev")
    bot.load_extension("src.cogs.epfl")
    bot.load_extension("src.cogs.errors")
    bot.load_extension("src.cogs.misc")
    bot.load_extension("src.cogs.remind")
    bot.load_extension("src.utils")

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    start()
