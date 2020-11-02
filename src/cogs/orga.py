from dataclasses import dataclass
from typing import Any

import discord
from discord import Guild, PermissionOverwrite, Color, TextChannel, CategoryChannel, VoiceChannel, Member
from discord.ext.commands import Cog, command, group, Context, has_role, is_owner
from discord.utils import get

from src.constants import *
from src.converters import DictOf, ListOf, to_raw
from src.core import CustomBot, CustomCog, CogConfig
from src.errors import EpflError
from src.utils import official_guild, myembed, french_join, confirm, pprint_send


@dataclass
class Event:
    creator: Member
    role: discord.Role
    voice: ListOf(VoiceChannel)
    text: ListOf(TextChannel)


class OrgaCog(CustomCog, name="Events"):
    class Config(CogConfig):
        event_category: CategoryChannel
        __event_category__ = "The category in which to put events"

        chat: TextChannel
        __chat__ = "The private channel with the organisers"

        events: DictOf(str, Event) = {}  # Stores event names to (creator, role, text chan, voice, chan)

    @group("orga", aliases=["o"], invoke_without_command=True)
    @has_role(Role.ORGA)
    async def orga(self, ctx: Context):
        """(orga) Affiche l'aide pour les organisateurs d'événements."""

        orga_chan = self.get_conf(ctx.guild, "chat")

        diego = self.bot.get_user(OWNER)
        orga = get(ctx.guild.roles, name=Role.ORGA)

        await ctx.send(embed=myembed(
            "Guide pour l'organisation d'un événement",
            f"Tout d'abord merci à toi cher {orga.mention} pour ton énergie et ton temps, "
            "de la part de tous les étudiants qui seront moins isolés "
            "grâce à toi! :smiling_face_with_3_hearts: \n"
            "Voici les outils que EPFL Community met à disposition de tous "
            "pour gérer des événements au sein du serveur. N'hésite pas à discuter "
            f"sur {orga_chan.mention} si tu as besoin d'aide ou de choses particulières, "
            "tout est possible.",
            0xffa500,
            **{
                "_Créer un event":
                    "Tu peux utiliser `!orga new <nom de l'event>` pour créer : \n"
                    " - un role @event \n"
                    " - Un salon texte #event \n"
                    " - Un salon vocal #event \n"
                    "L'idée est d'annoncer ton event sur les salons publics, comme #general "
                    "et ensuite de faire l'event lui même seulement avec les gens interessés "
                    "sur les salons privés, histoire de limiter au maximum le "
                    "nombre de messages que chacun reçoit sans que ça l'intéresse.",
                "_Annoncer l'event (WIP)":
                    "Au moment d'annoncer un event, il faut faire en sorte que les gens "
                    "puissent obtenir le role @event et donc l'accès aux salons. "
                    "Pour ça le plus simple est que "
                    "chaque personne qui réagit au message d'annonce obtient automatiquement "
                    "le role. J'ai pas trouvé de moyen de faire ça 100% automatiquement, "
                    "donc il faut que : \n"
                    " - Tu dises dans ton message *\"Réagissez à ce message pour obtenir le role\"* "
                    "ou un équivalent, histoire que les gens sachent quoi faire\n"
                    " - Tu lances `!orga annonce #salon-de-l'annonce` pour dire au bot de checker "
                    "les reactions sur le dernier message que tu as envoyé dans ce salon. ",
                "_Notes":
                    "Tout ça rend les choses un peu plus compliquées pour les organisateurs, "
                    "mais le but est que ce soit simple pour les étudiants et d'éviter que le serveur "
                    "se transforme en gros fouillis. Si tu as une idée pour rendre ça plus simple, "
                    f"contacte {diego.mention} :wink:"
            }
        ))

    @orga.command("new")
    @has_role(Role.ORGA)
    async def new_event_cmd(self, ctx: Context, *, event: str):
        """(orga) Crée un role et un salon vocal+texte pour un event."""

        guild: Guild = ctx.guild
        passe_partout = guild.get_role(PASSE_PARTOUT_ROLE)
        reason = f"{ctx.author} wants to organise an event."

        conf: OrgaCog.Config
        with self.config(guild, "event_category") as conf:
            if event in conf.events or get(guild.roles, name=event):
                raise EpflError(f"Le nom *{event}* est déjà pris.")

            event_role = await guild.create_role(
                reason=reason,
                name=event,
                color=Color(0xcc99ff),
                mentionable=True,
            )
            await ctx.author.add_roles(event_role)

            # Nothing special, we give the orga most perms
            # especially perms to manage the channel,
            # Event can interact, Passe-partout can see
            # And the rest can not.
            overwrites = {
                ctx.author: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                    manage_channels=True,
                    manage_permissions=True,
                    manage_messages=True,
                    mute_members=True,
                    deafen_members=True,
                    priority_speaker=True,
                ),
                event_role: PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    connect=True,
                ),
                passe_partout: PermissionOverwrite(
                    read_messages=True,
                ),
                guild.default_role: PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                    connect=False,
                ),
            }

            # So we create a text and voice channel in the category
            event_text = await guild.create_text_channel(
                name=event,
                overwrites=overwrites,
                category=conf.event_category,
                reason=reason,
            )
            event_voice = await guild.create_voice_channel(
                name=event,
                overwrites=overwrites,
                category=conf.event_category,
                reason=reason,
            )

            # Store the event name
            conf.events[event] = to_raw(Event(ctx.author, event_role, [event_voice], [event_text]))

            # Confirmation
            await ctx.send(f"J'ai créé {event_role.mention} et {event_text.mention} ! Amusez vous bien ! :robot:")

    @orga.command("del")
    @has_role(Role.ORGA)
    async def del_event_cmd(self, ctx: Context, *, event: str):
        """(orga) Supprime un événement."""

        with self.config(ctx.guild) as conf:
            if event not in conf.events:
                raise EpflError(f"`{event}` is not an event. "
                                f"Valid names: {french_join(conf.events, 'and')}.")

            ev = conf.events[event]

            if ctx.author != ev.creator:
                raise EpflError(f"You are not the organiser of this event. "
                                f"Contact {ctx.author.mention} to delete it.")

            if await confirm(ctx, self.bot, embed=myembed(
                    "Confirm event deletion",
                    "Those roles and channels will be deleted.",
                    Role=ev.role.mention,
                    Text=french_join([t.mention for t in ev.text], "and"),
                    Voice=french_join([t.mention for t in ev.voice], "and"),
            )):

                reason = f"{ctx.author.mention} deleted event {event}."
                await ev.role.delete(reason=reason)
                for t in ev.text:
                    await t.delete(reason=reason)
                for v in ev.voice:
                    await v.delete(reason=reason)
                del conf.events[event]

    @command(name="events")
    async def events(self, ctx: Context):
        """Liste des événements en cours."""
        events = self.get_conf(ctx.guild, "events")

        if not events:
            await ctx.send("Il n'y a pas d'événements en cours :(")
            return

        msg = f"Voici une liste de tous les événements actuels : \n - " \
              + "\n - ".join(events)

        await ctx.send(msg)


def setup(bot: CustomBot):
    bot.add_cog(OrgaCog(bot))
