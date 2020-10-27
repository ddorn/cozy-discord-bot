import sys
import traceback
from datetime import datetime
from io import StringIO
from pprint import pprint

import discord
from discord.ext.commands import *
from discord.utils import maybe_coroutine

from src.constants import LOG_CHANNEL
from src.core import CustomBot
from src.errors import EpflError

# Global variable and function because I'm too lazy to make a metaclass
from src.utils import myembed, with_max_len, py

handlers = {}


def handles(error_type):
    """
    This registers an error handler.

    Error handlers can be coroutines or functions.
    """

    def decorator(f):
        handlers[error_type] = f
        return f

    return decorator


class ErrorsCog(Cog):
    """This cog defines all the handles for errors."""

    def __init__(self, bot: CustomBot):
        self.bot = bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        err = error if not isinstance(error, CommandInvokeError) else error.original

        now = datetime.now().ctime()
        trace = StringIO()
        traceback.print_tb(err.__traceback__, file=trace)

        print("---" * 4, file=sys.stderr)
        print(now, file=sys.stderr)
        print(repr(err), ctx.author, ctx.message.content, sep="\n", file=sys.stderr)
        traceback.print_tb(err.__traceback__, file=sys.stderr)

        if not isinstance(err, (CommandNotFound)):
            # Always send a message in the log channel
            embed = myembed(
                f"A {err.__class__.__name__} happened",
                repr(err),
                _traceback=py(with_max_len(trace)),
                time=now,
                author=ctx.author.mention,
                message_id=ctx.message.id,
                _message=with_max_len(ctx.message.content),
            )
            await self.bot.get_channel(LOG_CHANNEL).send(embed=embed)

        # We take the first superclass with an handler defined
        handler = None
        for type_ in error.__class__.__mro__:
            handler = handlers.get(type_)
            if handler:
                break

        if handler is None:
            # Default handling
            msg = repr(error)
        else:
            msg = await maybe_coroutine(handler, self, ctx, error)

        if msg:
            message = await ctx.send(msg)
            await self.bot.wait_for_bin(ctx.message.author, message)


    async def on_error(self, event, *args, **kwargs):
        type_, value, traceback_ = sys.exc_info()
        now = datetime.now()

        # stderr
        print("---" * 4, file=sys.stderr)
        print(now.ctime(), file=sys.stderr)
        print(event, args, kwargs, sep="\n", file=sys.stderr)
        traceback.print_tb(traceback_, file=sys.stderr)

        # Also send embed
        trace = StringIO()
        args_io = StringIO()
        kwargs_io = StringIO()

        traceback.print_tb(traceback_, file=trace)
        if args:  # So they don't appear if empty
            pprint(args, args_io)
        if kwargs:
            pprint(kwargs, kwargs_io)

        embed = myembed(
            f"{type_.__name__} during {event} event",
            repr(value),
            traceback=py(with_max_len(trace)),
            _args=py(with_max_len(args_io)),
            _kwargs=py(with_max_len(kwargs_io)),
            time=now.ctime(),
        )

        await self.bot.get_channel(LOG_CHANNEL).send(embed=embed)

    @handles(EpflError)
    async def on_epfl_error(self, ctx: Context, error: EpflError):
        msg = await ctx.send(error.msg)
        await self.bot.wait_for_bin(ctx.author, msg)

    @handles(CommandInvokeError)
    async def on_command_invoke_error(self, ctx, error):
        specific_handler = handlers.get(type(error.original))

        if specific_handler:
            return await specific_handler(self, ctx, error.original)

        return (
            error.original.__class__.__name__
            + ": "
            + (str(error.original) or str(error))
        )

    @handles(CommandNotFound)
    def on_command_not_found(self, ctx, error):

        # Here we just take advantage that the error is formatted this way:
        # 'Command "NAME" is not found'
        name = str(error).partition('"')[2].rpartition('"')[0]
        return f"La commande {name} n'existe pas. Pour une liste des commandes, envoie `!help`."

    @handles(MissingRole)
    def on_missing_role(self, ctx, error):
        return (
            f"Il te faut le role de {error.missing_role} pour utiliser cette commande."
        )


def setup(bot: CustomBot):
    cog = ErrorsCog(bot)
    bot.add_cog(cog)
    bot.on_error = cog.on_error
