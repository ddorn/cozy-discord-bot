import os
from pathlib import Path
from time import time

__all__ = [
    "DISCORD_TOKEN",
    "Role",
    "OWNER",
    "BOT",
    "EMBED_COLOR",
    "FRACTAL_URL",
    "FRACTAL_COOLDOWN",
    "File",
    "Emoji",
    "PREFIX",
    "SECTIONS",
    "YEARS",
    "DEV_BOT_CHANNEL"
]

DISCORD_TOKEN = os.environ.get("EPFL_DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    print("No token for the bot were found.")
    print("You need to set the EPFL_DISCORD_TOKEN variable in your environement")
    print("Or just run:")
    print()
    print(f'    EPFL_DISCORD_TOKEN="your token here" python bot.py')
    print()
    quit(1)

OWNER = 430566197868625920  # Diego's id
BOT = 753577454341455882

EPFL_GUILD = 721376511734710383  # Official EPFL guild id
DEV_BOT_CHANNEL = 753584773661982770
LOG_CHANNEL = 770004202406674433

PREFIX = "!"
EMBED_COLOR = 0xFF0000
FRACTAL_URL = "https://thefractal.space/img/{seed}.png?size=640"
FRACTAL_COOLDOWN = 42  # seconds

SECTIONS = {
    "CGC": "Chemistry and chemical engineering",
    "MA": "Mathematics",
    "SV": "Life sciences engineering",
    "IN/SC": "Computer science&Communication systems//Info et systcom",
    "GM": "Mechanical engineering",
    "ELEC": "Electrical and electronic engineering",
    "PH": "Physics",
    "MX": "Materials science and engineering//Science et génie des matériaux",
    "SIE": "Environmental sciences and engineering",
    "ARCHI": "Architecture",
    "GC": "Civil engineering",
    "MT": "Microengineering",
    "CMS": "CMS",
}

# IDs of year roles
YEARS = [
    721444748484673727,
    753679540064223293,
    753679541108736190,
    753679541821505656,
    753679542442524834,
    753679543088185526,
    770007403730960395,
    770007068585230336,
]


class Role:
    ADMIN = "Admin"
    MODO = "Modo"


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


class File:
    TOP_LEVEL = Path(__file__).parent.parent
    DATA = TOP_LEVEL / "data"
    HUGS = TOP_LEVEL / "data" / "hugs"
    REMINDERS = DATA / "reminders"
    RULES = DATA / "rules.yaml"


def setup(_):
    # Just so we can reload the constants
    pass
