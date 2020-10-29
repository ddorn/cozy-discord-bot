from discord.ext.commands import Cog, command, group, Context

from src.core import CustomBot


class OrgaCog(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    @group("orga", hidden=True)
    async def orga(self, ctx: Context):
        """Affiche l'aide pour les organisateur d'événements."""
        await ctx.invoke(self.bot.get_command("help"), "perms")


def setup(bot: CustomBot):
    bot.add_cog(OrgaCog(bot))