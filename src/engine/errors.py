"""
This module defines all the custom Exceptions used in this project.
"""

__all__ = ["CozyError", "CozyOnlyError", "ConfigUndefined"]

from discord.ext.commands import CommandError


class CozyError(CommandError):
    """Base class for all exceptions raised by the bot itself.

     It contains a user-targeted message."""

    def __init__(self, msg):
        super(CozyError, self).__init__(msg)

    @property
    def message(self):
        return self.args[0]

    def __repr__(self):
        return self.message


class CozyOnlyError(CozyError):
    """Error raised when a command should be used only in Cozy's server."""

    def __init__(self):
        super().__init__("This command can only be used in the Cozy's server.")


class ConfigUndefined(CozyError):
    def __init__(self, config, names):
        self.config = config
        self.names = names

        config_name = config.name()
        qualified_names = [f"`{config_name}.{n}`" for n in names]
        super().__init__(
            f"The following settings are not defined: "
            f'{", ".join(qualified_names)}. '
            f"Run `!set <setting> <value>` to define them."
        )


def setup(bot):
    pass
