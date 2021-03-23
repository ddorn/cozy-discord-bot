import asyncio
import sys
from datetime import datetime
from importlib import reload
from typing import Union, Tuple, Type, Iterator, Any, Dict

import yaml
from discord import User, Message, Reaction, NotFound, Forbidden, Guild, TextChannel
from discord.ext.commands import Bot, Cog

__all__ = ["CustomBot"]

from discord.utils import get

from src.constants import *
from src.converters import to_nice, to_raw
from src.errors import ConfigUndefined
from src.utils import myembed


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
    """Base class for cog Configuration.

    To use it, define a class Config(CogConfig) in
    your cog class definition. The fields and their
    types are defined with annotations on class variables.
    Defaults are taken from the class attributes' values.
    A description for the field can be set on __field__,
    if there is no description, it can't be set in SettingsCog,
    making it like a permanent storage for the cog.

    Example:
     >>> class MyCog(CustomCog):
     >>>    class Config:
     >>>        a: int
     >>>        __a__ = "Description for a, which has no default value."
     >>>
     >>>        nickname: str = "Billy"
     >>>        __nickname__ = "Nickname defaults to Billy."
     >>>
     >>>        storage: int  # No description prevent user from changing them in SettingsCog

     Defaults should be nice values or convert to nice values
    """

    _cog: "CustomCog" = None
    """Cog in which the config is defined. This class attribute is set only on cog instantiation."""

    @classmethod
    def _annotations(cls) -> Dict:
        """Return a dict of all config fields and associated types."""

        # I don't understand why it doesn't work to put this in the metaclass...

        # Empty Config does not have __annotations__
        try:
            ann = cls.__annotations__
        except AttributeError:
            ann = {}

        # Filter out private attributes
        return {key: value for (key, value) in ann.items() if not key.startswith("_")}

    def __init__(self, guild):
        assert guild
        self._guild: Guild = guild
        self.load()

    # Getter for information of settings
    @classmethod
    def descr(cls, field):
        """Return the description for a field."""
        return getattr(cls, f"__{field}__", "")

    @classmethod
    def type_of(cls, field):
        """Return the type of a field."""
        return cls._annotations()[field]

    @classmethod
    def default_of(cls, field):
        """Return the default for a field.

        The default is always a nice value.
        If not is set, return Undefined."""

        try:
            val = getattr(cls, field)
        except AttributeError:
            return Undefined

        return to_nice(val, cls.type_of(field), None)

    # Context manager for auto saving
    def __enter__(self):
        """Context manager that auto-save the configuration upon exit."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    # Iteration (redirected from class iteration)
    def __iter__(self):
        """Iterate over the config fields' names."""
        return iter(self.__class__)

    def __contains__(self, field):
        """Whether a field is a valid config field."""
        return field in self.__class__

    # Indexing, redirecting to attributes
    def __getitem__(self, field):
        """Return the value of the field.

        Raises KeyError if the field is not valid."""

        if field not in self:
            raise KeyError(f"{field} is not a valid config key")

        return getattr(self, field)

    def __setitem__(self, key, value):
        """Set the value for the field.

        Convert the value to the correct type in the process.
        Raises KeyError if the field is not valid."""

        if key not in self:
            raise KeyError(f"{key} is not a valid config key")

        setattr(self, key, value)

    @classmethod
    def name(cls):
        return cls._cog.name()

    def items(self) -> Dict[str, Any]:
        for name in self:
            yield name, self[name]

    @staticmethod
    def _read_full_config():
        File.CONFIG.touch()
        return yaml.safe_load(File.CONFIG.read_text() or "{}")

    def load(self):
        """Get a dict of all field and their value from the file."""

        conf = self._read_full_config()
        conf = conf.get(self._guild.id, {}).get(self.name(), {})

        for name in self:

            try:
                val = to_nice(conf[name], self.type_of(name), self._guild)
            except KeyError:
                val = self.default_of(name)

            setattr(self, name, val)

    def save(self):
        """Save this config in File.CONFIG."""

        full_config = self._read_full_config()

        # we only need to remove undefined from self._raw_dict
        d = {
            k: to_raw(v, self.type_of(k))
            for k, v in self.items()
            if v is not Undefined
        }

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

    @classmethod
    def config(cls, guild: Union[int, Guild], *require_defined) -> Config:
        """Get the config if the cog for a given guild.

        If any setting name passed in require_defined is undefined, raises
        an ConfigUndefined.
        """

        conf = cls.Config(guild)

        undef = [name for name in require_defined if conf[name] is Undefined]
        if undef:
            raise ConfigUndefined(conf, undef)

        return conf

    @classmethod
    def get_conf(cls, guild: Union[int, Guild], field: str, raise_undefined=True):
        """Return the value of {field} defined in the guild config.

        If raise_undefined is true, raises a ConfigUndefined
        when the field is not defined."""

        require = (field,) if raise_undefined else ()
        return cls.config(guild, *require)[field]

    @classmethod
    def name(cls):
        """Return the normalised name for the cog.

        The normalised name is lowercase with the last 'cog' removed."""
        name = cls.__name__.lower()
        if name.endswith("cog"):
            return name[:-3]
        return name


class CustomBot(Bot):
    """
    This is the same as a discord bot except
    for class reloading and it provides hints
    for the type checker about the modules
    that are added by extensions.
    """

    def __init__(self, *args, **kwargs):
        super(CustomBot, self).__init__(*args, **kwargs)

        # I don't know the difference...
        self.last_disconnect = None

    async def on_ready(self):
        print("Connected to discord !", datetime.now().ctime())

        await self.send_connection_info()

    async def send_connection_info(self):
        chan = self.get_channel(Channels.LOG_CHANNEL)
        if self.last_disconnect is None:
            await chan.send("Here I am !")
        else:
            disconnected_for = (datetime.now() - self.last_disconnect)
            s = int(round(disconnected_for.total_seconds()))
            await chan.send(f"Hello there! \n"
                            f"<@{self.owner_id}>: Last disconect {self.last_disconnect.ctime()} for "
                            f"{s//3600 :02}h{s//60%60 :02}m{s%60 :02}.")
        self.last_disconnect = None

    async def on_disconnect(self):
        now = datetime.now()
        print("DISCONNECTED:", now.ctime())
        if self.last_disconnect is None:
            self.last_disconnect = now

    async def on_resume(self):
        print("RESUMED:", datetime.now().ctime())
        await self.send_connection_info()

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
                    user == u or user == OWNER
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

    async def log(self, level=10, *args, **kwargs, ):
        """Send something to the log channel.

        args and kwargs are forwarded to myembed()
        :level: is between 0 and 50, 10 beeing debug and 40 being error
        """

        if level <= 10:
            color = '00ff00'
        elif level <= 20:
            color = "ffff00"
        elif level <= 30:
            color = 'ffa500'
        elif level <= 40:
            color = 'ff0000'
        else:
            color = 'ff00a0'

        kwargs.setdefault('color', int(color, 16))

        msg = DIEGO_MENTION if level >= 30 else ''

        chan: TextChannel = self.get_channel(Channels.LOG_CHANNEL)
        await chan.send(msg, embed=myembed(*args, **kwargs))

    async def debug(self, *args, **kwargs):
        await self.log(10, *args, **kwargs)
    async def info(self, *args, **kwargs):
        await self.log(20, *args, **kwargs)
    async def warn(self, *args, **kwargs):
        await self.log(30, *args, **kwargs)
    async def error(self, *args, **kwargs):
        await self.log(40, *args, **kwargs)
    async def critical(self, *args, **kwargs):
        await self.log(50, *args, **kwargs)
