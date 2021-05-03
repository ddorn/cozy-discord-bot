from dataclasses import is_dataclass
from typing import Type, TYPE_CHECKING, Union, Dict, Optional

import discord
from discord import CategoryChannel, Guild, TextChannel, VoiceChannel, Member
from discord.utils import get

from src.engine.utils import mentions_to_id, get_casefold

if TYPE_CHECKING:
    from src.engine import CustomBot

__all__ = ["to_raw", "to_nice"]


class Converter:
    """Base class for all converters.

    Converters convert values between raw and nice types. The
    raw type is the type meant to be serialised in yaml, while
    the nice type is meant to be used in the program.

    To implement a converter for a type, {nice_type} and {raw_type}
    should be set and {to_raw} and {to_nice} must be implemented.

    Subclasses of Converter are automatically registered according
    to their nice_type.

    Refer to the documentation of each function for more.
    """

    raw_type: Type = str
    """Type stored in yaml."""
    nice_type: Type = str
    """Typed used in the program/config."""

    def __repr__(self):
        return f"Conv({self.nice_type.__name__})"

    def to_raw(self, nice: nice_type):
        """Convert a nice value to a raw value.

        It can be assumed that {nice} will always be a nice value,
        according to {is_nice()}.

        Raises ValueError when the conversion is not possible."""

        return self.raw_type(nice)

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        """Convert any value to a nice value.

        to_nice should be more powerful than to_raw and handle the values
        that aren't nice, like string representations.

        It can be assumed that that raw will never be a nice value.

        Raises ValueError when the conversion is not possible."""

        return self.nice_type(raw)

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        """Whether a value is in the nice form."""
        return isinstance(value, self.nice_type)

    def is_raw(self, value):
        """Whether a value is in the raw form."""
        return isinstance(value, self.raw_type)

    def assert_guild(self, guild: Optional[Guild]):
        """Raise a value error if the guild is none."""
        if guild is None:
            raise ValueError(
                f"`{guild}` is not a valid guild but {self} requires a guild."
            )


class IntConverter(Converter):
    raw_type = int
    nice_type = int


class AnyConverter(Converter):
    """Do nothing converter. Leaves objects unchanged."""

    raw_type = object
    nice_type = object

    def to_raw(self, nice: nice_type):
        return nice

    def to_nice(self, raw: raw_type, guild: int):
        return raw


class BoolConverter(Converter):
    raw_type = bool
    nice_type = bool

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        if isinstance(raw, str):
            if raw.lower() in "yes oui y ok o 0 true".split():
                return True
            elif raw.lower() in "no non n nope 1 false".split():
                return False
        elif isinstance(raw, int):
            return bool(raw)

        raise ValueError(f"Boolean not recognised: `{raw}`")


class ChannelConverter(Converter):
    """Convert to a channel, bot-wide."""

    raw_type = int
    nice_type = (TextChannel, VoiceChannel)
    force_guild = False

    def to_raw(self, nice: nice_type):
        return nice.id

    def to_nice(
        self, raw: raw_type, guild: Optional[Guild]
    ) -> Union[TextChannel, VoiceChannel]:
        if self.force_guild:
            self.assert_guild(guild)
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

    def to_nice(self, raw, guild: Optional[Guild]):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a text channel.")

        return chan


class CategoryConverter(ChannelConverter):
    """Converter for a category channel in a guild."""

    nice_type = CategoryChannel
    force_guild = False

    def to_nice(self, raw, guild: Optional[Guild]):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a category.")

        return chan


class VoiceChannelConverter(ChannelConverter):
    """Converter for a category channel in a guild."""

    nice_type = VoiceChannel
    force_guild = False

    def to_nice(self, raw, guild: Optional[Guild]):
        chan = super().to_nice(raw, guild)

        if not isinstance(chan, self.nice_type):
            raise ValueError(f"{chan.mention} is not a voice channel.")

        return chan


class MemberConverter(Converter):
    raw_type = int
    nice_type = Member

    def to_raw(self, nice: nice_type):
        return nice.id

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        self.assert_guild(guild)

        if isinstance(raw, str):
            # Try exact name/nick match
            mem = guild.get_member_named(raw)

            # Then casefold name/display_name
            mem = (
                mem
                or get_casefold(guild.members, name=raw)
                or get_casefold(guild.members, display_name=raw)
            )

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

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        self.assert_guild(guild)

        if isinstance(raw, str):
            role = get(guild.roles, name=raw) or get_casefold(guild.roles, name=raw)
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

    def __init__(self, type_: Type = object):
        self.inner_type = to_converter(type_)

    def __repr__(self):
        return f"ListOf({self.inner_type})"

    def to_raw(self, nice: nice_type):
        return [self.inner_type.to_raw(n) for n in nice]

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
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
        return {
            self.key_type.to_raw(key): self.value_type.to_raw(val)
            for key, val in nice.items()
        }

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        return {
            self.key_type.to_nice(key, guild): self.value_type.to_nice(val, guild)
            for key, val in raw.items()
        }

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        return all(
            self.key_type.is_nice(key) and self.value_type.is_nice(val)
            for key, val in value.items()
        )

    def is_raw(self, value):
        return all(
            self.key_type.is_raw(key) and self.value_type.is_raw(val)
            for key, val in value.items()
        )


class DataclassConverter(Converter):
    raw_type = dict
    nice_type = type(
        "dataclass", (), {}
    )  # Filling value, dataclasses don't have a base class.

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

    def to_nice(self, raw: raw_type, guild: Optional[Guild]):
        return self.dataclass(
            **{
                field: conv.to_nice(raw[field], guild)
                for field, conv in self.converters.items()
            }
        )

    def is_nice(self, value: Union[raw_type, nice_type]) -> bool:
        return is_dataclass(value)


def all_subclasses(cls):
    return (
        set(cls.__subclasses__())
        .union([s for c in cls.__subclasses__() for s in all_subclasses(c)])
        .union({cls})
    )


def to_converter(nice_type: Union[Type, Converter]) -> Converter:
    if is_dataclass(nice_type):
        return DataclassConverter(nice_type)

    if (
        isinstance(nice_type, Converter)
        or nice_type.__class__.__base__.__name__ == "Converter"
    ):
        ### I HAVE NO FREAKING IDEA WHY DICTOF DOES NOT WORK HERE.....
        return nice_type

    for klass in all_subclasses(Converter):
        if klass.nice_type == nice_type:
            return klass()

    raise ValueError(f"No converter from {nice_type} found ")


def to_raw(value, nice_type: Union[Type, Converter] = None):
    if nice_type is None:
        nice_type = type(value)

    converter = to_converter(nice_type)

    if converter.is_raw(value):
        return value
    return converter.to_raw(value)


def to_nice(value, nice_type: Union[type, Converter], guild: Optional[Guild]):
    converter = to_converter(nice_type)

    if converter.is_nice(value):
        return value
    return converter.to_nice(value, guild)


BOT: "CustomBot" = None


def setup(bot: "CustomBot"):
    global BOT
    BOT = bot
