import asyncio
import sys
from datetime import datetime
from importlib import reload
from typing import Union, Tuple, Type, Iterator, Any, Dict

import yaml
from discord import User, Message, Reaction, NotFound, Forbidden, Guild
from discord.ext.commands import Bot, Cog

__all__ = ["CustomBot"]

from discord.utils import get

from src.constants import *
from src.errors import ConfigUndefined


class Undef:
    def __repr__(self):
        return "Undefined"
Undefined = Undef()


class CogConfigMeta(type):
    def __iter__(cls):
        return iter(cls._annotations())

    def __contains__(cls, item):
        return item in cls._annotations()


class CogConfig(metaclass=CogConfigMeta):
    _cog = None  # type: CustomCog

    def __init__(self, guild):
        self._guild = guild
        self.load()

    @classmethod
    def _annotations(cls) -> Dict:
        # Empty Config does not have __annotations__
        return getattr(cls, "__annotations__", {})

    # Getter for information of settings
    @classmethod
    def descr(cls, name):
        return getattr(cls, f"__{name}__", "")

    @classmethod
    def type_of(cls, name):
        return cls._annotations()[name]

    @classmethod
    def default_of(cls, name):
        return getattr(cls, name, Undefined)

    # Context manager for auto saving
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    # Iteration (redirected from class iteration)
    def __iter__(self):
        return iter(self.__class__)

    def __contains__(self, item):
        return item in self.__class__

    def __getitem__(self, item):
        if item not in self:
            raise IndexError(f"{item} is not a valid config key")
        return getattr(self, item)

    def __setitem__(self, key, value):
        if key not in self:
            raise IndexError(f"{key} is not a valid config key")

        if value is not Undefined:
            value  = self.type_of(key)(value)

        setattr(self, key, value)

    @classmethod
    def name(cls):
        return cls._cog.name()

    @classmethod
    def slots(cls) -> Iterator[Tuple[str, Type, Any, str]]:
        """Yield all the config slots.

        They are tuples (name, type, default, description).
        """

        for name, typ in cls._annotations().items():
            if name.startswith("_"):
                continue

            descr = cls.descr(name)
            default = cls.default_of(name)
            yield name, typ, default, descr

    def items(self) -> Dict[str, Any]:
        for name in self:
            yield name, self[name]

    def _read_full_config(self):
        File.CONFIG.touch()
        return yaml.safe_load(File.CONFIG.read_text() or "{}")

    def load(self):
        conf = self._read_full_config()
        conf = conf.get(self._guild.id, {}).get(self.name(), {})

        for name, typ, default, descr in self.slots():
            value = conf.get(name, default)

            # Reconstruct the value from the type
            self[name] = value

    def save(self):
        full_config = self._read_full_config()

        # Put all attributes in a dict, with defaults when needed
        d = {}
        for name, _, default, _ in self.slots():
            val = self[name]
            if val is not Undefined:
                d[name] = val
        # and store it in full_config[guild][cog]
        full_config.setdefault(self._guild.id, {})[self.name()] = d

        # Finally, save it to aa file
        File.CONFIG.write_text(yaml.safe_dump(full_config))


class CustomCog(Cog):
    """
    A discord Cog, but with a cool config
    interface.
    """

    def __init__(self, bot: "CustomBot"):
        self.Config._cog = self
        self.bot = bot

    class Config(CogConfig):
        pass
        # event_category: int = 0
        # __event_category__ = "The category where events channels are created."

    def config(self, guild: Union[int, Guild], *require_defined) -> Config:
        """Get the config if the cog for a given guild.

        If any setting name passed in require_defined is undefined, raises
        an ConfigUndefined.
        """

        conf = self.Config(guild)

        undef = [name for name in require_defined if conf[name] is Undefined]
        if undef:
            raise ConfigUndefined(conf, undef)

        return self.Config(guild)

    @classmethod
    def name(cls):
        name = cls.__name__.lower()
        if name.endswith("cog"):
            name = name[:-3]
        return name


class CustomBot(Bot):
    """
    This is the same as a discord bot except
    for class reloading and it provides hints
    for the type checker about the modules
    that are added by extensions.
    """

    async def on_ready(self):
        print("Connected to discord !", datetime.now().ctime())

        await self.get_channel(Channels.LOG_CHANNEL).send("Here I am !")

    def __str__(self):
        return f"{self.__class__.__name__}:{hex(id(self.__class__))} obj at {hex(id(self))}"

    def reload(self):
        cls = self.__class__
        module_name = cls.__module__
        old_module = sys.modules[module_name]

        print("Trying to reload the bot.")
        try:
            # del sys.modules[module_name]
            module = reload(old_module)
            self.__class__ = getattr(module, cls.__name__, cls)
        except:
            print("Could not reload the bot :/")
            raise
        print("The bot has reloaded !")

    async def wait_for_bin(bot: Bot, user: User, *msgs: Message, timeout=300):
        """Wait for timeout seconds for `user` to delete the messages."""

        msgs = list(msgs)

        assert msgs, "No messages in wait_for_bin"

        for m in msgs:
            await m.add_reaction(Emoji.BIN)

        def check(reaction: Reaction, u):
            return (
                    user == u
                    and any(m.id == reaction.message.id for m in msgs)
                    and str(reaction.emoji) == Emoji.BIN
            )

        try:
            while msgs:
                reaction, u = await bot.wait_for(
                    "reaction_add", check=check, timeout=timeout
                )

                the_msg: Message = get(msgs, id=reaction.message.id)
                try:
                    await the_msg.delete()
                except NotFound:
                    pass  # message was deleted
                msgs.remove(the_msg)
        except asyncio.TimeoutError:
            pass

        for m in msgs:
            try:
                await m.clear_reaction(Emoji.BIN)
            except (NotFound, Forbidden):
                # Message or reaction deleted / in dm channel
                pass
