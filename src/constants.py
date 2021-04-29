import os
from pathlib import Path

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
    "File",
    "Emoji",
    "PREFIX",
]

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    print("No token for the bot were found.")
    print("You need to set the DISCORD_TOKEN variable in your environment")
    print("Or just run:")
    print()
    print('    DISCORD_TOKEN="your token here" python .')
    print()
    quit(1)

OWNER = 430566197868625920  # Diego's id
BOT = 837400346808549417
MAIN_GUILD = 822820580889853952
DIEGO_MENTION = f"<@{OWNER}>"

PREFIX = "!"
EMBED_COLOR = 0xFF0000
FRACTAL_URL = "https://thefractal.space/img/{seed}.png?size=640"
FRACTAL_COOLDOWN = 42  # seconds


class Role:
    ADMIN = "Admin"
    MODO = "Modo"
    ORGA = "Orga"


class Channels:
    LOG_CHANNEL = 837402825784033300


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
    RAINBOW_HEART = "<:rainbowheart:837416173603520522>"


class File:
    TOP_LEVEL = Path(__file__).parent.parent
    COGS = TOP_LEVEL / "src" / "cogs"
    DATA = TOP_LEVEL / "data"
    HUGS = TOP_LEVEL / "data" / "hugs"
    REMINDERS = DATA / "reminders"
    RULES = DATA / "rules.yaml"
    CONFIG = DATA / "config.yaml"
    MEMES = DATA / "memes"
    JOKES_V2 = DATA / "jokes.yaml"


def setup(_):
    # Just so we can reload the constants
    pass
