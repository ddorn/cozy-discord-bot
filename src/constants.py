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
    "FAN_CLUBS",
    "PREFIX",
    "SECTIONS",
]

DISCORD_TOKEN = os.environ.get("EPFL_DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    print("No token for the bot were found.")
    print("You need to set the EPFL_DISCORD_TOKEN variable in your environement")
    print("Or just run:")
    print()
    print(f'    EPFL_DISCORD_TOKEN="your token here" python epfl-discord-bot.py')
    print()
    quit(1)

GUILD = "690934836696973404"
OWNER = 430566197868625920  # Diego's id

BOT = 753577454341455882
PREFIX = "!"
EMBED_COLOR = 0xFF0000
FRACTAL_URL = "https://thefractal.space/img/{seed}.png?size=1000"
FRACTAL_COOLDOWN = 42  # seconds
FAN_CLUBS = []

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
    # "MAN": "MAN",
    "CMS": "CMS",
}


class Role:
    ADMIN = "Admin"
    MODO = "Modo"
    DEV = "dev"
    MODOS = tuple(f"Modo {t}" for t in SECTIONS)
    PRETRESSE_CALINS = "Grande prêtresse des câlins"
    JURY = "Eded"
    PARTICIPANT = "EDED"


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
    RAINBOW_HEART = "<:rainbow_heart:714172834632564818>"


class File:
    TOP_LEVEL = Path(__file__).parent.parent
    DATA = TOP_LEVEL / "data"
    HUGS = TOP_LEVEL / "data" / "hugs"
    REMINDERS = DATA / "reminders"


def setup(_):
    # Just so we can reload the constants
    pass
