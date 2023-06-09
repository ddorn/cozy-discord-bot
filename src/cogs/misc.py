import ast
import asyncio
import io
import math
import operator as op
import random
import re
import traceback
import urllib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import partial
from math import factorial
from operator import itemgetter
from time import time
from typing import List, Set, Union

import aiohttp
import discord
import yaml
from discord import (
    AllowedMentions,
    Member,
)

from discord.ext.commands import (
    BadArgument,
    command,
    Context,
    group,
    MemberConverter,
    RoleConverter,
)
from discord.utils import get
from engine import (
    check_role,
    CogConfig,
    CozyError,
    CustomBot,
    CustomCog,
    with_max_len,
)

from src.constants import *
from src.engine import send_and_bin, utils

# supported operators
OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    "abs": abs,
    "π": math.pi,
    "τ": math.tau,
    "i": 1j,
    "fact": factorial,
}

for name in dir(math):
    if not name.startswith("_"):
        OPS[name] = getattr(math, name)


@dataclass
class Joke(yaml.YAMLObject):
    yaml_tag = "Joke"
    yaml_dumper = yaml.SafeDumper
    yaml_loader = yaml.SafeLoader
    joke: str
    joker: int
    likes: Set[int] = field(default_factory=set)
    dislikes: Set[int] = field(default_factory=set)
    file: str = None


HUG_RE = re.compile(r"^(?P<hugger>\d+) -> (?P<hugged>\d+) \| (?P<text>.*)$")


class Hug:
    def __init__(self, hugger, hugged, text):
        self.hugger = hugger
        self.hugged = hugged
        self.text = text

    @classmethod
    def from_str(cls, line: str):
        match = HUG_RE.match(line)
        if not match:
            raise ValueError(f"'{line}' is not a valid hug format.")
        hugger = int(match.group("hugger"))
        hugged = int(match.group("hugged"))
        text = match.group("text")

        return cls(hugger, hugged, text)

    def __repr__(self):
        return f"{self.hugger} -> {self.hugged} | {self.text}"


class MiscCog(CustomCog, name="Divers"):
    class Config(CogConfig):
        fractals_generated: int = 0

    def __init__(self, bot: CustomBot):
        super().__init__(bot)
        self.computing = False
        self.hugs = self.get_hugs()

    # ----------------- Hugs ---------------- #

    @command(aliases=["<3", "❤️", ":heart:"])  # Emoji.RAINBOW_HEART])
    async def hug(self, ctx: Context, who="everyone"):
        """Give someone a hug. :heart:"""

        if who == "everyone":
            who = ctx.guild.default_role
        elif who == "back":
            return await self.hug_back(ctx)
        else:
            try:
                who = await RoleConverter().convert(ctx, who)
            except BadArgument:
                try:
                    who = await MemberConverter().convert(ctx, who)
                except BadArgument:
                    return await ctx.send(
                        discord.utils.escape_mentions(
                            f'There is no "{who}". :man_shrugging:'
                        )
                    )
        who: Union[discord.Role, Member]
        bot_hug = who == self.bot.user

        bonuses = [
            "It's too cuuute!",
            "It boosts morale! :D",
            ":hugging:",
            ":smiling_face_with_3_hearts:",
            "Oh wiiii",
            f"{who.mention} asks for one more!"
            if not bot_hug
            else "I want another one! :heart_eyes:",
            "The poor is all red!"
            if not bot_hug
            else "A robot cannot blush, but I believe that ... :blush:",
            "Hihi, their woolen sweater tickles! :sheep:",
        ]

        # if has_role(ctx.author, Role.PRETRESSE_CALINS):
        #     bonuses += [
        #         "C'est le plus beau calin du monde :smiling_face_with_3_hearts: :smiling_face_with_3_hearts:",
        #         f"{who.mention} est subjugué·e ! :smiling_face_with_3_hearts:",
        #     ]

        if who.id == OWNER:
            bonuses += [
                "Wait... It smells like mojito... :lemon:",
                ":green_heart: :lemon: :green_heart:",
            ]

        if who == ctx.author:
            msg = f"{who.mention} self-hug!"
            bonuses += [
                "But it's a bit ridiculous ...",
                "But his arms are too short! :cactus:",
                "It takes little to be happy :wink:",
            ]
        elif who == ctx.guild.default_role:
            msg = f"{ctx.author.mention} gives a hug to everyone!"
            bonuses += [
                "That's a lot of people for a hug!",
                "The more we are, the more hugs we are!",
                "It's not very COVID-19 all that!",
                "Everyone is happy now!",
            ]
        elif bot_hug:
            msg = f"{ctx.author.mention} gives me a biiig huuug!"
            bonuses += ["I find that really welcoming <3 !"]
        else:
            msg = f"{ctx.author.mention} gives a big hug to {who.mention} !"
            bonuses += [
                f"But {who.mention} doesn't like...",
                "And they go hunting ducks together :wink:",
                "Oh! It smells good...",
                "And when am I entitled to a hug?"
                f"{who.mention} squeezed so hard that they cut you in half: scream:",
                f"{who.mention} suggests to {ctx.author.mention} to meet again around a :pizza:!",
                "Commissioner Winston's drones are passing by and ordering you to stop.",
                "After this beautiful moment of tenderness, they decide to go and discuss by creating puzzles.",
                f"{who.mention} takes refuge in Animath's warehouse and blocks the entrance with a piece of furniture.",
            ]

        bonus = random.choice(bonuses)

        text = f"{msg} {bonus}"
        self.add_hug(ctx.author.id, who.id, text)

        await ctx.send(text)

        if bot_hug and random.random() > 0.9:
            await asyncio.sleep(3.14159265358979323)
            ctx.author = get(ctx.guild.members, id=self.bot.user.id)
            await ctx.invoke(self.hug, "back")

    async def hug_back(self, ctx: Context):
        hugger = ctx.author.id

        last_hug: Hug = get(reversed(self.hugs), hugged=hugger)
        if not last_hug:
            return await ctx.send(
                f"No one has ever hugged {ctx.author.mention}, we have to fix it!"
            )

        if "cut you in half" in last_hug.text:
            return await ctx.send(
                "You're not going to hug someone after " "that you just cut in half!"
            )

        await ctx.invoke(self.hug, str(last_hug.hugger))

    @command(name="hug-stats", aliases=["hs"])
    # @commands.has_role(Role.PRETRESSE_CALINS)
    @check_role(Role.MODO)
    async def hugs_stats_cmd(self, ctx: Context, who: Member = None):
        """(priestess of hugs) posts who is the most warm"""

        if who is None:
            await self.send_all_hug_stats(ctx)
        else:
            await self.send_hugs_stats_for(ctx, who)

    async def send_all_hug_stats(self, ctx):
        medals = [
            ":first_place:",
            ":second_place:",
            ":third_place:",
            ":medal:",
            ":military_medal:",
        ]
        ranks = ["Big Teddy Bear", "Little Panda", "Teddy Bear"]

        embed = discord.Embed(
            title="More hugged prize",
            color=discord.Colour.magenta(),
            description=f"Total number of hugs {len(self.hugs)} {Emoji.HEART}",
        )

        everyone = ctx.guild.default_role.id
        everyone_hugs = 0
        everyone_diff = set()
        stats = Counter()
        diffs = defaultdict(set)
        for h in self.hugs:
            if h.hugged == everyone:
                everyone_hugs += 1
                everyone_diff.add(h.hugger)
            else:
                if h.hugged != h.hugger:
                    stats[h.hugged] += 1
                    diffs[h.hugged].add(h.hugger)

                role: discord.Role = get(ctx.guild.roles, id=h.hugged)
                if role is not None:
                    for m in role.members:
                        if m.id != h.hugger:
                            stats[m.id] += 1
                            diffs[m.id].add(h.hugger)

        for m, d in diffs.items():
            stats[m] += len(everyone_diff.union(d)) * 42 + everyone_hugs

        top = sorted(list(stats.items()), key=itemgetter(1), reverse=True)

        for i in range(min(3, len(top))):
            m = medals[i]
            r = ranks[i]
            id, qte = top[i]
            who = self.name_for(ctx, id)

            embed.add_field(name=f"{m} - {r}", value=f"{who} : {qte}  :heart:")

        top4to7 = "\n ".join(
            f"{medals[3]} {self.name_for(ctx, id)} : {qte}  :orange_heart:"
            for id, qte in top[3 : min(8, len(top))]
        )
        if top4to7:
            embed.add_field(name="Teddy apprentice", value=top4to7)

        top8to13 = "\n".join(
            f"{medals[4]} {self.name_for(ctx, id)} : {qte}  :yellow_heart:"
            for id, qte in top[8 : min(13, len(top))]
        )
        if top8to13:
            embed.add_field(name="Ball of duck wool", value=top8to13)

        await ctx.send(embed=embed)

    async def send_hugs_stats_for(self, ctx: Context, who: discord.Member):

        given = self.hugs_given(ctx, who.id)
        received = self.hugs_received(ctx, who.id)
        auto = self.auto_hugs(ctx, who.id)
        cut = [h for h in given if "cut in half" in h.text]
        infos = {
            "Given hugs": (len(given), 1),
            "Received hugs": (len(received), 1),
            "Hugged people": (len(set(h.hugged for h in given)), 20),
            "Hugges by": (len(set(h.hugger for h in received)), 30),
            "Self hugs": ((len(auto)), 3),
            "Parts": (len(cut), 30),
        }

        most_given = Counter(h.hugged for h in given).most_common(1)
        most_received = Counter(h.hugger for h in received).most_common(1)
        most_given = most_given[0] if most_given else (0, 0)
        most_received = most_received[0] if most_received else (0, 0)

        embed = discord.Embed(
            title=f"Câlins de {who.display_name}",
            color=discord.Colour.magenta(),
            description=(
                f"We can say that {who.mention} is very cuddly, with a score of "
                f"{self.score_for (ctx, who.id)}. He cuddled a lot "
                f"{self.name_for (ctx, most_given [0])}"
                f"*({most_given [1]} :heart:)* and "
                f"got hugged a lot by {self.name_for (ctx, most_received [0])} "
                f"*({most_received [1]} :heart:)*!"
            ),
        )
        user: discord.User = self.bot.get_user(who.id)
        embed.set_thumbnail(url=user.avatar_url)

        for f, (v, h_factor) in infos.items():
            heart = self.heart_for_stat(v * h_factor)
            if f == "Parts":
                v = 2 ** v
            embed.add_field(name=f, value=f"{v} {heart}")

        await ctx.send(embed=embed)

    def ris(self, ctx: Context, id, role_or_member_id):
        """Whether the id is the same member or a member that has the given role."""
        if id == role_or_member_id:
            return True

        member: Member = get(ctx.guild.members, id=id)

        if member is None:
            return False

        role = get(member.roles, id=role_or_member_id)

        return role is not None

    @staticmethod
    def heart_for_stat(v):
        hearts = [
            ":broken_heart:",
            ":green_heart:",
            ":yellow_heart:",
            ":orange_heart:",
            ":heart:",
            ":sparkling_heart:",
            Emoji.RAINBOW_HEART,
        ]

        if v <= 0:
            return hearts[0]
        elif v >= 5000:
            return hearts[-1]
        elif v >= 2000:
            return hearts[-2]
        else:
            return hearts[len(str(v))]

    def name_for(self, ctx, member_or_role_id):
        memb = ctx.guild.get_member(member_or_role_id)
        if memb is not None:
            name = memb.mention
        else:
            role = ctx.guild.get_role(member_or_role_id)
            if role is None:
                name = getattr(
                    self.bot.get_user(member_or_role_id), "mention", "Personne"
                )
            else:
                name = role.name

        return name

    def score_for(self, ctx, member_id):
        received = self.hugs_received(ctx, member_id)
        diffs = set(h.hugger for h in received)
        return 42 * len(diffs) + len(received)

    def hugs_given(self, ctx, who_id):
        eq = partial(self.ris, ctx, who_id)
        return [h for h in self.hugs if eq(h.hugger) and not eq(h.hugged)]

    def hugs_received(self, ctx, who_id):
        eq = partial(self.ris, ctx, who_id)
        return [h for h in self.hugs if eq(h.hugged) and not eq(h.hugger)]

    def auto_hugs(self, ctx, who_id):
        eq = partial(self.ris, ctx, who_id)
        return [h for h in self.hugs if eq(h.hugged) and eq(h.hugger)]

    @staticmethod
    def get_hugs():
        File.HUGS.touch()
        lines = File.HUGS.read_text().strip().splitlines()
        return [Hug.from_str(l) for l in lines]

    def add_hug(self, hugger: int, hugged: int, text):
        File.HUGS.touch()
        with open(File.HUGS, "a") as f:
            f.write(f"{hugger} -> {hugged} | {text}\n")
        self.hugs.append(Hug(hugger, hugged, text))

    # ---------------- Jokes ---------------- #

    @staticmethod
    def load_jokes() -> List[Joke]:
        # Ensure it exists
        File.JOKES_V2.touch()
        with open(File.JOKES_V2) as f:
            jokes = list(yaml.safe_load_all(f))

        return jokes

    @staticmethod
    def save_jokes(jokes):
        File.JOKES_V2.touch()
        with open(File.JOKES_V2, "w") as f:
            yaml.safe_dump_all(jokes, f)

    # ---------------- Joke ----------------- #

    @group(name="joke", invoke_without_command=True, case_insensitive=True)
    async def joke(self, ctx: Context, id=None):
        """Quietly makes a random joke."""

        m: discord.Message = ctx.message
        await m.delete()

        jokes = self.load_jokes()
        if id is not None:
            id = int(id)
            joke_id = id
            jokes = sorted(
                jokes, key=lambda j: len(j.likes) - len(j.dislikes), reverse=True
            )
        else:
            joke_id = random.randrange(len(jokes))

        try:
            joke = jokes[joke_id]
        except IndexError:
            raise CozyError("There are no jokes with this ID.")

        if joke.file:
            file = discord.File(File.MEMES / joke.file)
        else:
            file = None

        message: discord.Message = await ctx.send(joke.joke, file=file)

        await message.add_reaction(Emoji.PLUS_1)
        await message.add_reaction(Emoji.MINUS_1)
        await self.wait_for_joke_reactions(joke_id, message)

    @joke.command(name="new")
    @send_and_bin
    async def new_joke(self, ctx: Context):
        """Add a joke for the joke contest."""
        jokes = self.load_jokes()
        joke_id = len(jokes)

        author: discord.Member = ctx.author
        message: discord.Message = ctx.message

        msg = message.content[len("!joke new ") :]

        joke = Joke(msg, ctx.author.id, set())

        if message.attachments:
            file: discord.Attachment = message.attachments[0]
            joke.file = str(f"{joke_id}-{file.filename}")
            await file.save(File.MEMES / joke.file)
        elif not msg.strip():
            return "You can't add an empty joke..."

        jokes.append(joke)
        self.save_jokes(jokes)
        await message.add_reaction(Emoji.PLUS_1)
        await message.add_reaction(Emoji.MINUS_1)

        await self.wait_for_joke_reactions(joke_id, message)

    async def wait_for_joke_reactions(self, joke_id, message):
        # D: is the `u` parameter used
        def check(reaction: discord.Reaction, u):
            return (message.id == reaction.message.id) and str(reaction.emoji) in (
                Emoji.PLUS_1,
                Emoji.MINUS_1,
            )

        start = time()
        end = start + 24 * 60 * 60 * 5  # 5 days
        while time() < end:

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", check=check, timeout=end - time()
                )
            except asyncio.TimeoutError:
                return

            if user.id == BOT:
                continue

            jokes = self.load_jokes()
            if str(reaction.emoji) == Emoji.PLUS_1:
                jokes[joke_id].likes.add(user.id)
            else:
                jokes[joke_id].dislikes.add(user.id)

            self.save_jokes(jokes)

    @joke.command(name="top")
    @check_role(Role.MODO)
    async def best_jokes(self, ctx: Context):
        """Displays the list of jokes ."""

        jokes = self.load_jokes()

        s = sorted(jokes, key=lambda j: len(j.likes) - len(j.dislikes), reverse=True)

        embed = discord.Embed(title="Best jokes.")
        for i, joke in enumerate(s[:10]):
            who = get(ctx.guild.members, id=joke.joker)

            text = joke.joke
            if joke.file:
                text += " - no image included - "

            name = who.display_name if who else "Unknown"
            embed.add_field(
                name=f"{i} - {name} - {len(joke.likes)} :heart: {len(joke.dislikes)} :broken_heart:",
                value=text,
                inline=False,
            )

        await ctx.send(embed=embed)

    # @joke.command(name="del")
    # @check_role(Role.MODO)
    # async def delete_joke(self, ctx: Context, identifier):
    #     """Deletes a joke by ID"""
    #     try:
    #         identifier = int(identifier)
    #     except ValueError:
    #         raise ValueError('You should give an integer as argument')
    #     jokes = self.load_jokes()
    #     if identifier >= len(jokes):
    #         raise IndexError('You gave a role identifier out of range')
    #     else:
    #         del jokes[identifier]
    #         self.save_jokes(jokes)

    # ---------------- Choose ----------------- #

    @command(
        name="choose",
        usage='choice1 choice2 "choice 3"...',
        aliases=["choice", "choix", "ch", "elige"],
    )
    async def choose(self, ctx: Context, *args):
        """
        Choose an option from all the arguments.

        For options that contain a space,
        just put quotes (`"`) around.
        """

        if not args:
            msg = await ctx.send("You didn't give me any option !")
        else:
            choice = random.choice(args)
            msg = await ctx.send(f"J'ai choisi... **{choice}**")
        await self.bot.wait_for_bin(ctx.author, msg),

    # @cog_slash(
    #     name='fractal',
    #     description='Genère une fractale aléatoire',
    #     options=[
    #         create_option(
    #             'seed', 'La graine pour générer la fractale',
    #             SlashCommandOptionType.STRING, False,
    #         )
    #     ],
    # )
    @command(rest_is_raw=True)
    async def fractal(self, ctx: Context, *, seed=None):
        """Draw a random fractal."""

        if self.computing:
            return await ctx.send("There is a fractal being calculated already")

        with ctx.channel.typing():
            try:
                self.computing = True

                # await ctx.respond()
                # msg: discord.Message = ctx.message
                # seed = msg.content[len("!fractal "):]
                seed = seed or str(random.randint(0, 1_000_000_000))
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        FRACTAL_URL.format(seed=urllib.parse.quote(seed)), timeout=120
                    ) as resp:
                        if resp.status != 200:
                            print(resp)
                            return await ctx.send(
                                "There was a problem calculating or downloading the image..."  # D: maybe send?
                            )
                        data = io.BytesIO(await resp.read())

                        # seed_escaped = remove_mentions_as(ctx.author, ctx.channel, seed)
                        await ctx.send(
                            f"Seed: {seed}",
                            file=discord.File(data, "fractal.png"),
                            allowed_mentions=AllowedMentions.none(),
                        )

                        if ctx.guild:
                            conf: MiscCog.Config
                            with self.config(ctx.guild) as conf:
                                conf.fractals_generated += 1
            finally:
                self.computing = False

    # ---------------- Calc ----------------- #

    @command(name="calc", aliases=["="])
    async def calc_cmd(self, ctx, *args):
        """Make a simple calculus"""
        with_tb = ctx.author.id == OWNER
        embed = self._calc(ctx.message.content, with_tb)
        resp = await ctx.send(embed=embed)

        def check(before, after):
            return after.id == ctx.message.id

        while True:
            try:
                before, after = await self.bot.wait_for(
                    "message_edit", check=check, timeout=600
                )
            except asyncio.TimeoutError:
                break

            embed = self._calc(after.content, with_tb)
            await resp.edit(embed=embed)

        # Remove the "You may edit your message"
        embed.set_footer()
        try:
            await resp.edit(embed=embed)
        except discord.NotFound:
            pass

    def _calc(self, query: str, with_tb=False):

        for prefix in (PREFIX + " ", PREFIX, "calc", "="):
            if query.startswith(prefix):
                query = query[len(prefix) :]
        # Replace implicit multiplication by explicit *
        query = re.sub(r"\b((\d)+(\.\d+)?)(?P<name>[a-zA-Z]+)\b", r"\1*\4", query)

        query = query.strip().strip("`")

        ex = None
        result = 42
        try:
            result = self._eval(ast.parse(query, mode="eval").body)
        except Exception as e:
            ex = e

        if isinstance(result, complex):
            if abs(result.imag) < 1e-12:
                result = result.real
            else:
                r, i = result.real, result.imag
                r = r if abs(int(r) - r) > 1e-12 else int(r)
                i = i if abs(int(i) - i) > 1e-12 else int(i)
                if not r:
                    result = f"{i if i != 1 else ''}i"
                else:
                    result = f"{r}{i if i != 1 else '':+}i"
        if isinstance(result, float):
            result = round(result, 12)

        embed = discord.Embed(
            title=discord.utils.escape_markdown(query), color=EMBED_COLOR
        )
        # embed.add_field(name="Entrée", value=f"`{query}`", inline=False)
        embed.add_field(
            name="Valeur", value=f"`{with_max_len(str(result), 1022)}`", inline=False
        )
        if ex and with_tb:
            embed.add_field(
                name="Erreur", value=f"{ex.__class__.__name__}: {ex}", inline=False
            )
            trace = io.StringIO()
            traceback.print_exception(type(ex), ex, ex.__traceback__, file=trace)
            trace.seek(0)
            embed.add_field(name="Traceback", value=f"```\n{trace.read()}```")
        embed.set_footer(text="You may edit your message")

        return embed

    def _eval(self, node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return OPS[type(node.op)](self._eval(node.left), self._eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return OPS[type(node.op)](self._eval(node.operand))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return OPS[node.func.id](
                    *(self._eval(n) for n in node.args),
                    **{k.arg: self._eval(k.value) for k in node.keywords},
                )
        elif isinstance(node, ast.Name):
            return OPS[node.id]

        fields = ", ".join(
            f"{k}={getattr(node, k).__class__.__name__}" for k in node._fields
        )
        raise TypeError(f"Node type not supported: {node.__class__.__name__}({fields})")

    @command(name="Diego", aliases=[OWNER_NAME], hidden=True)
    async def diego_cmd(self, ctx):
        msg = "He is my daddy! :smiling_face_with_3_hearts:"

        if random.random() < 0.05:
            msg += f"  (and he is single {Emoji.PANDANGEL})"

        await ctx.send(msg)

    # ---------------- Stream ----------------- #
    
    @staticmethod
    def load_pings():
        return [user for user in File.PING.read_text().split("\n") if user]
    
    @staticmethod
    def save_pings(ping):
        File.PING.write_text("\n".join(ping))

    @group(name="stream", invoke_without_command=True, case_insensitive=True)
    async def stream(self, ctx):
        """Have a look at the users in the memento ping list."""
        ping = self.load_pings()
        embed = discord.Embed(
            title="Memento ping list",
            description="\n".join((f"<@{user}>" for user in ping)),
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)

    @stream.command(name="ping")
    async def stream_ping(self, ctx: Context):
        """Ping all users in the memento ping list to announce your stream."""
        ping = self.load_pings()
        msg = "Hey " + ", ".join((f"<@{user}>" for user in ping)) + f"!\n<@{ctx.message.author.id}> is gonna stream!"
        await ctx.send(msg)

    @stream.command(name="addme")
    async def stream_addme(self, ctx: Context):
        """Add yourself to the memento ping list"""
        user_id = str(ctx.message.author.id)
        ping = self.load_pings()
        if user_id in ping:
            await ctx.send("You are already in the ping list!")
        else:
            ping.append(user_id)
            self.save_pings(ping)
        embed = discord.Embed(
            title="Memento ping list",
            description="\n".join(("<@" + user.replace("\n", "") + ">" for user in ping)),
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)

    @check_role(Role.ADMIN)
    @stream.command(name="add")
    async def stream_add(self, ctx, who: Member = None):
        """Adds a user to the stream-ping-list"""
        if who:
            user_id = str(who.id)
            ping = self.load_pings()
            if user_id in ping:
                await ctx.send("User already in the ping list!")
            else:
                ping.append(user_id)
                self.save_pings(ping)

            embed = discord.Embed(
                title="Memento ping list",
                description="\n".join(("<@" + user.replace("\n", "") + ">" for user in ping)),
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("You must give a user to add to the list")

    @stream.command(name="delme")
    async def stream_delme(self, ctx: Context):
        """Remove yourself from the memento ping list."""
        user_id = str(ctx.message.author.id)
        ping = self.load_pings()
        if user_id not in ping:
            await ctx.send("You are not in the ping list!")
        else:
            ping.remove(user_id)
            self.save_pings(ping)
        embed = discord.Embed(
            title="Memento ping list",
            description="\n".join(("<@" + user.replace("\n", "") + ">" for user in ping)),
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)

    @check_role(Role.ADMIN)
    @stream.command(name="del")
    async def stream_del(self, ctx, who: Member = None):
        """Removes a user from the stream-ping-list"""

        if who:
            user_id = str(who.id)
            ping = self.load_pings()
            if user_id not in ping:
                await ctx.send("Unable to delete user. It is not in the ping list")
            else:
                ping.remove(user_id)
                self.save_pings(ping)
            embed = discord.Embed(
                title="Memento ping list",
                description="\n".join((f"<@{user}>" for user in ping)),
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("You must give a user to add to the list")


def setup(bot: CustomBot):
    bot.add_cog(MiscCog(bot))
