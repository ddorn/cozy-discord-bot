from discord import CategoryChannel, Member, PermissionOverwrite
from discord.ext.commands import BadArgument, Context, group, TextChannelConverter, VoiceChannelConverter, \
    ChannelNotFound

from src.constants import DIEGO_MENTION
from src.engine import CogConfig, CustomCog
from engine.errors import EpflError
from engine.utils import myembed


class RoomsCog(CustomCog, name="Private Channels"):

    class Config(CogConfig):
        category: CategoryChannel
        __category__ = "Where new private channels are created."

    @group(name="private", aliases=["priv", "pv"], invoke_without_command=True)
    async def private(self, ctx: Context):
        """Aide pour la création de salons privés."""

        embed = myembed(
            "Guide pour les salons privés",
            "Il est possible de créer des salons privés pour soi et ses "
            "ami·e·s. Voici tous les détails techniques ! \n"
            "Tu auras tous les droits sur le salon que tu crée, d'ajouter "
            "des personnes, modifier le nom, ou le supprimer. Un fois le salon "
            "créé, tu pourras donc faire tout ça via l'interface de discord. "
            "N'hésite pas à demander si tu as besoin d'aide :wink:.",

            **{
                "_Créer un salon texte privé":
                    "Pour creer un salon texte privé, il faut utiliser "
                    "`!private text [Nom-du-salon]` où le nom du "
                    "salon ne comporte pas d'espace. Tu peux directement "
                    "ajouter tes ami·e·s en ajoutant leur noms après le nom "
                    "du salon, en séparant chaque nom par des espaces.\n"
                    "Exemple: `!private text coin-tranquile @Diego @Link-D`",
                "_Créer un salon vocal privé":
                    "Pour créer un salon vocal, la commande `!private vocal` "
                    "fonctionne de la même façon que `!private text`, mais "
                    "les noms de salon peuvent avoir des espaces. Pour avoir "
                    "un nom avec des espaces, il faut l'entourer de guillemets"
                    " `\"`. \n "
                    "Exemple: `!private vocal \"Petit salon\" @Diego @Link-D`",
                "_Comment ajouter des personnes dans un salon ?":
                    "Tu peux le faire avec un clic droit sur le salon puis sur permissions, "
                    "et ensuite ajouter les personnes que tu veux et leur donner "
                    "la permission *lire les messages*.",
                "_Est-ce que les salons sont vraiment privés ?":
                    "Oui, autant qu'un salon discord peut l'être. "
                    "Les bots et les admins ont toujours accès à tous les salons "
                    "mais nous (les admin) ne viendrons pas regarder (on a des séries de "
                    "retard à faire avant ! :sweat_smile:",
                "_Comment supprimer un salon ?":
                    "Celui qui l'a créé peut le supprimer dans les parametres du salons, "
                    "merci de les supprimer si vous ne les utilisez plus, comme ça on n'aura "
                    "pas trop de salons non utilisés ;) (Discord impose une limite de 500 salons).",
            }
        )

        await ctx.send(embed=embed)

    @private.command(name="vocal", aliases=["voice", "v"])
    async def priv_vocal_cmd(self, ctx: Context, name: str, *friends: Member):
        """Create a private voice channel."""
        await self._create_channel(ctx, name, friends, False)

    @private.command(name="text", aliases=["texte", "t"])
    async def priv_text_cmd(self, ctx: Context, name: str, *friends: Member):
        """Create a private text channel."""
        await self._create_channel(ctx, name, friends, True)

    async def _create_channel(self, ctx: Context, name, friends, text=True):
        cat: CategoryChannel = self.get_conf(ctx.guild, "category")

        nb_in_cat = len(cat.channels)
        if nb_in_cat == 50:
            raise EpflError("Le nombre maximum de salons privés est atteint, "
                            "il faut demander à un modo de créer une nouvelle catégorie "
                            f"et la définir dans les réglages. (ping {DIEGO_MENTION})")
        elif nb_in_cat > 47:
            await self.bot.warn("Salons privés", f"Il y a {nb_in_cat} salons dans {cat}. "
                               f"Il faut changer de catégorie bientôt.", ping=True)

        overwrites = {
            ctx.author: PermissionOverwrite(
                manage_roles=True,
                manage_channels=True,
                view_channel=True,
            ),
            ctx.guild.default_role: PermissionOverwrite(
                view_channel=False,
            ),
        }

        for f in friends:
            if f != ctx.author:
                overwrites[f] = PermissionOverwrite(view_channel=True)

        if text:
            create = cat.create_text_channel
        else:
            create = cat.create_voice_channel

        chan = await create(name, overwrites=overwrites,
                     reason=f"{ctx.author.mention} wants a private channel.")

        await ctx.send(f"J'ai créé {chan.mention} !")

    @private.command(name="add")
    async def priv_add_cmd(self, ctx: Context, channel, *friends: Member):
        """Ajoute tes potes sur un salon."""

        try:
            chan = await TextChannelConverter().convert(ctx, channel)
        except BadArgument:
            chan = await VoiceChannelConverter().convert(ctx, channel)


        author: Member = ctx.author
        if not author.permissions_in(chan).view_channel:
            # Pretend it does not exists
            raise ChannelNotFound(channel)

        if author.permissions_in(chan).manage_permissions:
            for friend in friends:
                await chan.set_permissions(
                    friend,
                    read_messages=True,
                )

            l = len(friends)
            await ctx.send(f"J'ai ajouté {l} ami·e{'·s' * (l > 1)} sur {chan.mention}")
        else:
            await ctx.send("Impossible de modifier le salon, tu n'as pas les droits dessus.")

def setup(bot):
    bot.add_cog(RoomsCog(bot))
