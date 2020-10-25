import asyncio
import json
import re
from datetime import datetime, timedelta
from threading import Thread

import discord
import parsedatetime
from discord import Member, Guild
from discord.abc import GuildChannel
from discord.ext.commands import Cog, group, command, Context
from discord.utils import escape_mentions, get

from src.constants import File, Emoji
from src.core import CustomBot
from src.errors import EpflError
from src.utils import send_all, pprint_send


class RemindCog(Cog, name="Reminders"):
    def __init__(self, bot: CustomBot):
        self.bot = bot

        self.cal = parsedatetime.Calendar()
        File.REMINDERS.touch()
        self.reminders = self.load()
        """self.reminders[date] = (channel_id, msg)"""

        self.bg_check = None
        self.bg_checking = True

    def __repr__(self):
        return f"<RemindCog at {hex(id(self))}: {len(self.reminders)} rems>"

    def start(self):
        self.bg_check = self.bot.loop.create_task(self.check_reminders())

    def stop(self):
        self.bg_checking = False
        File.REMINDERS.write_text(json.dumps(self.reminders))
        self.save()

    def load(self):
        return {
            datetime.fromtimestamp(float(t)): x
            for t, x in json.loads(File.REMINDERS.read_text() or "{}").items()
        }

    def save(self):
        j = {
            date.timestamp() : x
            for date, x in self.reminders.items()
        }
        File.REMINDERS.write_text(json.dumps(j))

    async def check_reminders(self):
        print(self, "started checking reminders")

        while self.bg_checking:
            await asyncio.sleep(1)
            now = datetime.now()

            for date, (chan, txt) in self.reminders.items():
                if date < now:
                    chan = self.bot.get_channel(chan)
                    await chan.send(txt)
                    del self.reminders[date]
                    self.save()
                    break

        print(self, "stoped checking reminders")

    @command("remind", aliases=["re"], rest_is_raw=True)
    async def remind_group(self, ctx: Context, when, *, what):
        """
        Remind the channel of an event at a given time.

        The times must be in plain english, and insides quotes
        if it consists of more than one word.

        **Examples**:
         - tomorrow
         - "in 10 minutes"
         - "next monday at 8am"
         - "tuesday noon"
        """

        now = datetime.now()
        when, ok = self.cal.parseDT(when, now)

        if not ok:
            raise  EpflError("Sorry, I could not parse the date.")

        if when < now - timedelta(seconds=1):
            raise EpflError("The date is already passed.")

        a: Member = ctx.author
        toggle = False
        if toggle ^ (not a.permissions_in(ctx.channel).mention_everyone):
            # Escape only @everyone/@here
            what = re.sub(r'@(everyone|here|[!&]?%d})' % ctx.guild.default_role.id, '@\u200b\\1', what)
            # escape roles mentions if not mentionable
            for match in re.finditer(r"<@&([0-9]{17,21})>", what):
                mention_id = int(match.group(1))
                r: discord.Role = get(ctx.guild.roles, id=mention_id)
                if not r.mentionable:
                    what = what.replace(match.group(0), "@\u200b" + r.name)

        msg = ctx.author.mention + ": " + what
        self.reminders[when] = (ctx.channel.id, msg)
        self.save()

        await ctx.message.add_reaction(Emoji.CHECK)


__cog = None
def setup(bot: CustomBot):
    global __cog
    __cog = RemindCog(bot)
    __cog.start()
    bot.add_cog(__cog)


def teardown(bot):
    global __cog
    __cog.stop()
    __cog = None
