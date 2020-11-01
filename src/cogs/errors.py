import sys
import traceback
from datetime import datetime
from io import StringIO
from pprint import pprint, pformat

import discord
from discord.ext.commands import *
from discord.utils import maybe_coroutine

from src.constants import Channels
from src.core import CustomBot
from src.errors import EpflError

# Global variable and function because I'm too lazy to make a metaclass
from src.utils import myembed, with_max_len, py, french_join, fg

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


def eprint(*args, **kwargs):
    """Alias to print that defaults to stderr"""
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


class ErrorsCog(Cog):
    """This cog defines all the handles for errors."""

    DONT_LOG = CommandNotFound,
    """Tuple of Exception classes to not log to discord"""

    def __init__(self, bot: CustomBot):
        self.bot = bot

    def get_tb(self, exc):
        trace = StringIO()
        traceback.print_tb(exc.__traceback__, file=trace)
        trace.seek(0)
        return trace.read()

    def get_handler(self, exc):
        # We take the first superclass with an handler defined
        for type_ in exc.__class__.__mro__:
            handler = handlers.get(type_)
            if handler:
                return handler

        raise RuntimeError(f"No handler for exception {exc}. Bases: {exc.__class__.__mro__}")

    def error_print(self, exc, *args):
        if isinstance(exc, CommandInvokeError):
            exc = exc.original

        eprint("-" * 12)
        eprint(datetime.now().ctime())
        eprint(repr(exc))
        eprint(*args, sep="\n")
        eprint()
        while exc:
            traceback.print_tb(exc.__traceback__, file=sys.stderr)
            exc = exc.__cause__
            if exc:
                eprint()
                eprint("Caused by:")
        eprint("-" * 12)

    def error_embed(self, exc: Exception, event='', **fields):
        if isinstance(exc, CommandInvokeError):
            exc = exc.original

        errors = []
        e = exc
        while e:
            errors.append(e)
            e = e.__cause__
        # errors = reversed(errors)

        embed = myembed(
            f"A {exc.__class__.__name__} happened" + f' during {event} event' * bool(event),
            py("\n from: ".join(repr(e) for e in errors)),
            time=datetime.now().ctime(),
            **fields
        )

        for i, exc in enumerate(errors):
            embed.add_field(
                name=f'Traceback of {exc.__class__.__name__}',
                value=py(with_max_len(self.get_tb(exc))),
                inline=False,
            )

        return embed

    @Cog.listener()
    async def on_command_error(self, ctx: Context, exc: CommandError):
        # Everything on stderr
        self.error_print(exc, ctx.author, ctx.message.content)

        # Less spam on discord
        if not isinstance(exc, self.DONT_LOG):
            embed = self.error_embed(
                exc,
                author=ctx.author.mention,
                message_id=ctx.message.id,
                _message=with_max_len(ctx.message.content),
            )
            await self.bot.get_channel(Channels.LOG_CHANNEL).send(embed=embed)

        # Handling error for Users
        handler = self.get_handler(exc)
        msg = await maybe_coroutine(handler, self, ctx, exc)

        if msg:
            message = await ctx.send(msg)
            await self.bot.wait_for_bin(ctx.message.author, message)

    async def on_error(self, event, *args, **kwargs):
        type_, exc, traceback_ = sys.exc_info()

        # stderr
        self.error_print(exc, f"Event: {event}", args, kwargs)

        # Discord log
        if isinstance(exc, self.DONT_LOG):
            return

        embed = self.error_embed(
            exc,
            event,
            args=pformat(args),
            kwargs=pformat(kwargs)
        )
        await self.bot.get_channel(Channels.LOG_CHANNEL).send(embed=embed)

    @handles(Exception)
    def on_exception(self, ctx, exc):
        return str(exc)

    @handles(EpflError)
    def on_epfl_error(self, ctx: Context, error: EpflError):
        return error.message

    @handles(CommandInvokeError)
    async def on_command_invoke_error(self, ctx, error):
        specific_handler = self.get_handler(error.original)

        if specific_handler:
            return await maybe_coroutine(specific_handler, self, ctx, error.original)

        eprint(fg(f"No specific handler for {error.original.__class__.__name__}."))

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

    @handles(BadArgument)
    def on_bad_argument(self, ctx: Context, error: BadArgument):
        self.bot.loop.create_task(ctx.invoke(self.bot.get_command("help"), ctx.command.qualified_name))

        return str(error)


def setup(bot: CustomBot):
    cog = ErrorsCog(bot)
    bot.add_cog(cog)
    bot.on_error = cog.on_error
