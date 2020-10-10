import asyncio
import json
from datetime import datetime
from threading import Thread

import discord
import parsedatetime
from discord.ext.commands import Cog, group, command, Context

from src.constants import File, Emoji
from src.core import CustomBot
from src.errors import EpflError
from src.utils import send_all


class RemindCog(Cog, name="Reminders"):
    def __init__(self, bot: CustomBot):
        self.bot = bot

        self.cal = parsedatetime.Calendar()
        File.REMINDERS.touch()
        self.reminders = self.load()
        """self.reminders[date] = (channel_id, msg)"""

        self.bg_check = None
        self.bg_checking = False

    def start(self):
        self.bg_check = self.bot.loop.create_task(self.check_reminders())

    def stop(self):
        self.bg_checking = True
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
        while not self.bg_checking:
            await asyncio.sleep(1)
            now = datetime.now()

            for date, (chan, txt) in self.reminders.items():
                if date < now:
                    chan = self.bot.get_channel(chan)
                    await chan.send(txt)
                    del self.reminders[date]
                    self.save()
                    break

    @command("remind", aliases=["re"], rest_is_raw=True)
    async def remind_group(self, ctx: Context, when, *, what):
        """Remind the channel of an event at a given time."""
        now = datetime.now()
        when, ok = self.cal.parseDT(when, now)

        if not ok:
            raise  EpflError("Sorry, I could not parse the date.")

        if when < now:
            raise EpflError("The date is already passed.")

        what = discord.utils.escape_mentions(what)
        self.reminders[when] = (ctx.channel.id, what)
        self.save()

        await ctx.message.add_reaction(Emoji.CHECK)


__cog = None
def setup(bot: CustomBot):
    global __cog
    __cog = RemindCog(bot)
    __cog.start()
    bot.add_cog(__cog)

    print("Started Reminders")


def teardown(bot):
    global __cog
    __cog.stop()
    __cog = None
    print("Stopped Reminders")
