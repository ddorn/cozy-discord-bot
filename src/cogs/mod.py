import discord
from discord import Message, PermissionOverwrite, TextChannel
from discord.abc import GuildChannel
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.ext.commands import command, Context, guild_only, has_role, is_owner
from engine import check_role, CustomBot, CustomCog, CozyError, myembed
from src.constants import *


class ModCog(CustomCog, name="Moderation"):
    @check_role(Role.MODO)
    @command(name="temp-hide", aliases=["th"])
    async def temp_hide_cmd(self, ctx: Context, duration: int = 60):
        """
        (modo) Hide the channel for a given time. Useful to prevent pings.

        The channel is hidden for a default of 60s and can be made visible
        again earlier by deleting the `!temp-hide` message.

        Works only on channels with less than 10 permissions.
        """

        chan: GuildChannel = ctx.channel
        if isinstance(chan, GuildChannel):
            perms = chan.overwrites

            if len(perms) > 10:
                raise CozyError("Cannot hide a channel with more than 10 permissions.")

            await chan.set_permissions(ctx.author, read_messages=True)
            await chan.set_permissions(ctx.guild.default_role, read_messages=False)
            for p in perms:
                if p not in (ctx.guild.default_role, ctx.author):
                    await chan.set_permissions(p, overwrite=None)

            await self.bot.wait_for_bin(ctx.author, ctx.message, timeout=duration)

            await chan.set_permissions(ctx.author, overwrite=None)
            for p, perm in perms.items():
                await chan.set_permissions(p, overwrite=perm)

    @check_role(Role.MODO)
    @command(name="freeze")
    async def freeze_cmd(self, ctx: Context, duration: int = 60):
        """
        (modo) Prevent anyone to write in the channel for a given time.

        The channel is hidden for a default of 60s and can be made visible
        again earlier by deleting the `!temp-hide` message.

        Works only on channels with less than 10 permissions.
        """

        chan: GuildChannel = ctx.channel
        perms = chan.overwrites

        if len(perms) > 10:
            raise CozyError("Cannot hide a channel with more than 10 permissions.")

        await ctx.message.delete()
        msg = await ctx.channel.send(
            embed=myembed(f"This channel has been frozen for {duration} seconds.")
        )
        await self.bot.info(
            "Channel frozen",
            f"Channel {ctx.channel.mention} has been frozen by {ctx.author.mention} for {duration} seconds.",
        )

        try:
            for who, perm in perms.items():
                new = PermissionOverwrite(**dict(iter(perm)))
                new.send_messages = False
                await chan.set_permissions(who, overwrite=new)

            # on public channels, we still need to prevent everyone from sending
            if ctx.guild.default_role not in perms:
                await chan.set_permissions(ctx.guild.default_role, send_messages=False)

            await self.bot.wait_for_bin(ctx.author, msg, timeout=duration)
        finally:
            for who, perm in perms.items():
                await chan.set_permissions(who, overwrite=perm)

            # on public channels, we also need to revert
            if ctx.guild.default_role not in perms:
                await chan.set_permissions(ctx.guild.default_role, overwrite=None)

    # ------------- Send / Del -------------- #

    @command(name="send")
    @is_owner()
    async def send_cmd(self, ctx, *msg):
        """(dev) Envoie un message."""
        await ctx.message.delete()
        await ctx.send(" ".join(msg))

    @command(name="embed")
    @is_owner()
    async def send_embed(self, ctx: Context):
        """
        Send an embed.

        The format of the ember must be the following
        ```
        #hexcolor    <-- optional
        ~url         <-- optional
        $thumbnail   <-- optional
        !image url   <-- optional
        Title
        Description
        ---
        Inline Field title 1
        Field one text
        can be multiple lines
        with some [links](thefractal.space)
        ---
        !Fields starting with a ! are not inline
        but if you add a space before the !, it wil still be
        ...

        ===          <-- optional
        Footer text
        ```
        """

        command_length = len(ctx.prefix) + len(ctx.invoked_with) + 1
        text: str = ctx.message.content[command_length:]

        def get_opt(key, default=EmptyEmbed):
            nonlocal text
            if text.startswith(key):
                value, _, text = text.partition("\n")
                return value[len(key) :].strip()
            return default

        color = EMBED_COLOR
        thumbnail = url = image_url = EmptyEmbed
        show_author = False
        delete = True
        while text[0] in "#~!$@x":
            t = text[0]
            if t == "#":
                color = int(get_opt("#"), 16)
            elif t == "~":
                url = get_opt("~")
            elif t == "!":
                image_url = get_opt("!")
            elif t == "$":
                thumbnail = get_opt("$")
            elif t == "@":
                show_author = get_opt("@")
            elif t == "x":
                delete = not get_opt("x")
            else:
                raise NotImplementedError(f"Not known pattern: {t}")

        if delete:
            await ctx.message.delete()

        title, _, text = text.partition("\n")
        text, _, footer = text.partition("===\n")

        parts = text.split("---\n")
        description = parts[0] if parts else None

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            url=url,
        )

        embed.set_footer(text=footer)
        embed.set_image(url=image_url)
        embed.set_thumbnail(url=thumbnail)
        if show_author:
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.avatar_url
            )

        for field in parts[1:]:
            name, _, value = field.partition("\n")
            if name.startswith("!"):
                name = name[1:]
                inline = False
            else:
                inline = True
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=embed)

    @command(name="reply")
    @is_owner()
    async def reply(self, ctx, channel: TextChannel, *msg):
        """(dev) Send a message to any channel.

        Does not delete the original post."""

        await channel.send(" ".join(msg))

    @command(name="send-to")
    @is_owner()
    async def send_to_cmd(self, ctx, who: discord.User, *msg):
        """(dev) Send a private message to any user.

        Does not delete the original post."""

        await who.send(" ".join(msg))

    @command(name="del")
    @is_owner()
    async def del_range_cmd(self, ctx: Context, id1: Message, id2: Message):
        """
        (modo) Suppress the messages between the two IDs in argument.

        To opt for the IDs of the messages you must activate the developer mode
        then right click> copy ID.

        `id1` is the most recent message to delete.
        `id2` is the oldest message.

        You cannot delete more than 100 messages at once.
        """

        channel: TextChannel = id1.channel
        to_delete = [
            message async for message in channel.history(before=id1, after=id2)
        ] + [id1, id2]
        await channel.delete_messages(to_delete)
        await ctx.message.delete()


def setup(bot: CustomBot):
    bot.add_cog(ModCog(bot))
