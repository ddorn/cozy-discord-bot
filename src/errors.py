"""
This module defines all the custom Exceptions used in this project.
"""

__all__ = ["EpflError", "EplfOnlyError", "ConfigUndefined"]

from discord.ext.commands import CommandError


class EpflError(CommandError):
    """Base class for all exceptions raised by the bot itself.

     It contains a user-targeted message."""

    def __init__(self, msg):
        super(EpflError, self).__init__(msg)

    @property
    def message(self):
        return self.args[0]

    def __repr__(self):
        return self.message


class EplfOnlyError(EpflError):
    """Error raised when a command should be used only in the EPFL Community guild."""

    def __init__(self):
        super().__init__("This command can only be used in the official EPFL Community server.")


class ConfigUndefined(EpflError):
    def __init__(self, config, names):
        self.config = config
        self.names = names

        config_name = config.name()
        qualified_names = [f"`{config_name}.{n}`" for n in names]
        super().__init__(f'The following settings are not defined: '
                         f'{", ".join(qualified_names)}. '
                         f'Run `!set <setting> <value>` to define them.')


def setup(bot):
    pass