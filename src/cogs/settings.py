from discord.ext.commands import Context, command, has_role

from src.core import CustomCog, CustomBot
from src.constants import *
from src.errors import EpflError
from src.utils import myembed


class SettingsCog(CustomCog, name="Settings"):

    @command(name="settings", aliases=["list-settings", "ls"])
    async def settings_list_cmd(self, ctx: Context):
        """List all settings with their values."""
        embed = myembed("All settings")
        for cog_name, cog in self.bot.cogs.items():
            if isinstance(cog, CustomCog):

                sets = []
                for name, value in cog.config(ctx.guild).items():
                    descr = cog.Config.descr(name)
                    if not descr:
                        continue

                    if hasattr(value, "mention"):
                        value = value.mention
                    else:
                        value = f"`{value}`"
                    t = f"`{cog.name()}.{name}`: {value}\n  ⇒ {descr}"
                    sets.append(t)

                if sets:
                    embed.add_field(name=cog_name, value="\n".join(sets), inline=False)

        await ctx.send(embed=embed)

    @command(
        name="set",
        usage="!set group.setting VALUE",
    )
    @has_role(Role.MODO)
    async def set_cmd(self, ctx: Context, name: str, *, value: str):
        """Set a setting for this guild."""

        cog_name, _, setting = name.partition(".")

        for cog in self.bot.cogs.values():
            if not isinstance(cog, CustomCog):
                continue

            if cog.name() == cog_name:
                break
        else:
            raise EpflError(f"Il n'y a pas de groupe de commandes qui s'appelle `{cog_name}`. "
                            "`!settings` done une liste des réglages possibles.")

        with cog.config(ctx.guild) as conf:
            # Not description => not settable
            if setting not in conf or not conf.descr(setting):
                raise EpflError(f"{cog_name} n'a pas de réglage {setting}. "
                                f"`!settings` done une liste des possibilités.")

            conf[setting] = value

        await ctx.message.add_reaction(Emoji.CHECK)


def setup(bot: CustomBot):
    bot.add_cog(SettingsCog(bot))
