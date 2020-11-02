import dataclasses
from dataclasses import is_dataclass
from typing import Any, Type, TYPE_CHECKING, Union, Dict, Optional

import discord
from discord import CategoryChannel, Guild, TextChannel, VoiceChannel, Member
from discord.utils import get, find

from src.utils import mentions_to_id, get_casefold

if TYPE_CHECKING:
    from src.core import CustomBot

__all__ = ["to_raw", "to_nice"]


class Converter:
    raw_type = str
    nice_type = str

    def get_guild(self, guild: int, force=True) -> Guild:
        guild: Guild = BOT.get_guild(guild)
        if not isinstance(guild, Guild) and force:
            raise ValueError(f"`{guild}` is not a valid guild.")

        return guild

    def __repr__(self):
        return f"<{self.nice_type.__name__}>"

    def to_raw(self, nice: nice_type):
        return self.raw_type(nice)

    def to_nice(self, raw: raw_type, guild: int):
        return self.nice_type(raw)

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        return isinstance(value, self.nice_type)

    def is_raw(self, value):
        return isinstance(value, self.raw_type)


class IntConverter(Converter):
    raw_type = int
    nice_type = int


class AnyConverter(Converter):
    raw_type = object
    nice_type = object

    def to_raw(self, nice: nice_type):
        return nice

    def to_nice(self, raw: raw_type, guild: int):
        return raw


class ChannelConverter(Converter):
    """Convert to a channel, bot-wide."""

    raw_type = int
    nice_type = (TextChannel, VoiceChannel)
    force_guild = False

    def to_raw(self, nice: nice_type):
        return nice.id

    def to_nice(self, raw: raw_type, guild: int) -> Union[TextChannel, VoiceChannel]:

        if self.force_guild:
            guild = self.get_guild(guild)
            iterator = lambda: guild.channels
        else:
            iterator = BOT.get_all_channels

        # Try to get a channel with the same name, and if there is none, compare casefold
        if isinstance(raw, str):
            # Exact name match
            for chan in iterator():
                if chan.name == raw:
                    return chan
            # Casefold name match
            casefold = raw.casefold()
            for chan in iterator():
                if chan.name.casefold() == casefold:
                    return chan

            # Fail => Try to convert to int
            raw = mentions_to_id(raw)

        raw = int(raw)

        chan = BOT.get_channel(raw)

        if chan:
            return chan

        raise ValueError(f"No channel with id {raw}")


class TextChannelConverter(ChannelConverter):
    """Converter for a text channel in a guild."""

    nice_type = TextChannel
    force_guild = True

    def to_nice(self, raw, guild: int):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a text channel.")

        return chan


class CategoryConverter(ChannelConverter):
    """Converter for a category channel in a guild."""

    nice_type = CategoryChannel
    force_guild = False

    def to_nice(self, raw, guild: int):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a category.")

        return chan


class VoiceChannelConverter(ChannelConverter):
    """Converter for a category channel in a guild."""

    nice_type = VoiceChannel
    force_guild = False

    def to_nice(self, raw, guild: int):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a voice channel.")

        return chan


class MemberConverter(Converter):
    raw_type = int
    nice_type = Member

    def to_raw(self, nice: nice_type):
        return nice.id

    def to_nice(self, raw: raw_type, guild: int):
        guild = self.get_guild(guild)

        if isinstance(raw, str):
            # Try exact name/nick match
            mem = guild.get_member_named(raw)

            # Then casefold name/display_name
            mem = mem or get_casefold(guild.members, name=raw) \
                  or get_casefold(guild.members, display_name=raw)

            if mem:
                return mem

            raw = mentions_to_id(raw)

        raw = int(raw)
        mem = guild.get_member(raw)

        if mem:
            return mem
        raise ValueError(f"No member with id {raw}.")


class RoleConverter(Converter):
    raw_type = int
    nice_type = discord.Role

    def to_raw(self, nice: nice_type):
        return nice.id

    def to_nice(self, raw: raw_type, guild: int):
        guild = self.get_guild(guild)

        if isinstance(raw, str):
            role = get(guild.roles, name=raw) \
                   or get_casefold(guild.roles, name=raw)
            if role:
                return role

            raw = mentions_to_id(raw)
        raw = int(raw)
        role = guild.get_role(raw)

        if role:
            return role
        raise ValueError(f"No role with id {raw}")


class ListOf(Converter):
    raw_type = list
    nice_type = list

    def __init__(self, type_: Type=object):
        self.inner_type = to_converter(type_)

    def __repr__(self):
        return f"ListOf({self.inner_type})"

    def to_raw(self, nice: nice_type):
        return [self.inner_type.to_raw(n) for n in nice]

    def to_nice(self, raw: raw_type, guild: int):
        return [self.inner_type.to_nice(r, guild) for r in raw]

    def is_nice(self, value) -> bool:
        return all(self.inner_type.is_nice(v) for v in value)

    def is_raw(self, value):
        return all(self.inner_type.is_raw(v) for v in value)


class DictOf(Converter):
    raw_type = dict
    nice_type = dict

    def __init__(self, key_type=str, value_type=object):
        self.key_type = to_converter(key_type)
        self.value_type = to_converter(value_type)

    def __repr__(self):
        return f"DictOf({self.key_type} -> {self.value_type})"

    def to_raw(self, nice: nice_type):
        return {self.key_type.to_raw(key): self.value_type.to_raw(val) for key, val in nice.items()}

    def to_nice(self, raw: raw_type, guild: int):
        return {
            self.key_type.to_nice(key, guild): self.value_type.to_nice(val, guild)
            for key, val in raw.items()
        }

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        return all(self.key_type.is_nice(key) and self.value_type.is_nice(val) for key, val in value.items())

    def is_raw(self, value):
        return all(self.key_type.is_raw(key) and self.value_type.is_raw(val) for key, val in value.items())


class DataclassConverter(Converter):
    raw_type = dict
    nice_type = type("dataclass", (), {})  # Filling value, dataclasses don't have a base class.

    def __init__(self, dataclass):
        self.dataclass = dataclass
        self.converters: Dict[str, Converter] = {
            field: to_converter(typ)
            for field, typ in self.dataclass.__annotations__.items()
        }

    def __repr__(self):
        return f"<DataclassConverter({self.dataclass.__name__})>"

    def to_raw(self, nice: nice_type):
        return {
            field: conv.to_raw(getattr(nice, field))
            for field, conv in self.converters.items()
        }

    def to_nice(self, raw: raw_type, guild: int):
        return self.dataclass(**{
            field: conv.to_nice(raw[field], guild)
            for field, conv in self.converters.items()
        })

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        return is_dataclass(value)


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]).union({cls})


def to_converter(nice_type: Union[Type, Converter]) -> Converter:
    if is_dataclass(nice_type):
        return DataclassConverter(nice_type)

    if isinstance(nice_type, Converter) or nice_type.__class__.__base__.__name__ == "Converter":
        ### I HAVE NO FREAKING IDEA WHY DICTOF DOES NOT WORK HERE.....
        return nice_type

    for klass in all_subclasses(Converter):
        if klass.nice_type == nice_type:
            return klass()

    raise ValueError(f"No converter from {nice_type} found ")


def to_raw(value, nice_type: Union[Type, Converter]=None):
    if nice_type is None:
        nice_type = type(value)

    converter = to_converter(nice_type)

    if converter.is_raw(value):
        return value
    return converter.to_raw(value)


def to_nice(value, nice_type: Union[type, Converter], guild: Optional[Union[int, Guild]]):
    if isinstance(guild, Guild):
        guild = guild.id

    converter = to_converter(nice_type)

    if converter.is_nice(value):
        return value
    return converter.to_nice(value, guild)


BOT: "CustomBot" = None


def setup(bot: "CustomBot"):
    global BOT
    BOT = bot
