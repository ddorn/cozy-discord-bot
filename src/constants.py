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
    "SECTIONS",
    "YEARS",
    "PASSE_PARTOUT_ROLE",
    "EPFL_GUILD",
]

DISCORD_TOKEN = os.environ.get("EPFL_DISCORD_TOKEN")

if DISCORD_TOKEN is None:
    print("No token for the bot were found.")
    print("You need to set the EPFL_DISCORD_TOKEN variable in your environment")
    print("Or just run:")
    print()
    print('    EPFL_DISCORD_TOKEN="your token here" python bot.py')
    print()
    quit(1)

OWNER = 430566197868625920  # Diego's id
BOT = 753577454341455882
DIEGO_MENTION = f"<@{OWNER}>"

EPFL_GUILD = 721376511734710383  # Official EPFL guild id
PASSE_PARTOUT_ROLE = 769480338594332702

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
    ORGA = "Orga"


class Channels:
    CHAT_ORGA = 771143198487085077
    DEV_BOT_CHANNEL = 753584773661982770
    LOG_CHANNEL = 770004202406674433


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
    COGS = TOP_LEVEL / "src" / "cogs"
    DATA = TOP_LEVEL / "data"
    HUGS = TOP_LEVEL / "data" / "hugs"
    REMINDERS = DATA / "reminders"
    RULES = DATA / "rules.yaml"
    CONFIG = DATA / "config.yaml"


def setup(_):
    # Just so we can reload the constants
    pass
