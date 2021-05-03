import os
import sys
from pathlib import Path
import argparse

__all__ = [
    "DISCORD_TOKEN",
    "Role",
    "Channels",
    "OWNER",
    "DIEGO_MENTION",
    "BOT",
    "EMBED_COLOR",
    "FRACTAL_URL",
    "FRACTAL_COOLDOWN",
    "OWNER_NAME",
    "BOT_NAME",
    "File",
    "Emoji",
    "PREFIX",
]


parser = argparse.ArgumentParser()
parser.add_argument("token", help="Discord secret token.", metavar="DISCORD_TOKEN")
parser.add_argument("--test", "-t", action="store_true")
args = parser.parse_args()

DISCORD_TOKEN = args.token
IS_TEST_BOT = args.test

if DISCORD_TOKEN is None:
    print("No token for the bot were found.")
    print("You need to set the DISCORD_TOKEN variable in your environment")
    print("Or just run:")
    print()
    print('    python . "your token here"')
    print()
    quit(1)

OWNER = 430566197868625920  # Diego's id
BOT = 837400346808549417 if not IS_TEST_BOT else 838683880604958741
MAIN_GUILD = 822820580889853952
DIEGO_MENTION = f"<@{OWNER}>"

PREFIX = "!" if not IS_TEST_BOT else "?"
EMBED_COLOR = 0xFF0000
FRACTAL_URL = "https://thefractal.space/img/{seed}.png?size=640"
FRACTAL_COOLDOWN = 42  # seconds
OWNER_NAME = "CozyFractal"
BOT_NAME = "Botzy" if not IS_TEST_BOT else "Botzy Dev"


class Role:
    ADMIN = "Admin"
    MODO = "Modo"
    ORGA = "Orga"


class Channels:
    LOG_CHANNEL = 837402825784033300 if not IS_TEST_BOT else 838717801954541599


class Emoji:
    HEART = "❤️"
    JOY = "😂"
    SOB = "😭"
    BIN = "🗑️"
    DICE = "🎲"
    CHECK = "✅"
    CROSS = "❌"
    PLUS_1 = "👍"
    MINUS_1 = "👎"
    RAINBOW_HEART = "<:rainbowheart:837416127725961246>"
    PANDANGEL = "<:pandangel:834527570715607117>"
    PREVIOUS = "◀"
    NEXT = "▶"


class File:
    TOP_LEVEL = Path(__file__).parent.parent
    ENGINE = TOP_LEVEL / "src" / "engine"
    COGS = TOP_LEVEL / "src" / "cogs"
    DATA = TOP_LEVEL / "data"
    HUGS = TOP_LEVEL / "data" / "hugs"
    REMINDERS = DATA / "reminders"
    RULES = DATA / "rules.yaml"
    CONFIG = DATA / "config.yaml"
    MEMES = DATA / "memes"
    JOKES_V2 = DATA / "jokes.yaml"


if not File.DATA.exists():
    File.DATA.mkdir()


def setup(_):
    # Just so we can reload the constants
    pass
