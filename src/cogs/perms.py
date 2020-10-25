import ast
import re
from collections import defaultdict
from typing import Set, Dict, Optional, Iterator, Tuple

import discord
import yaml
from discord import Member, Guild
from discord.abc import GuildChannel
from discord.ext.commands import (Cog, Context, group, has_role)

from src.constants import *
from src.core import CustomBot
from src.errors import EpflError
from src.utils import confirm, french_join, myembed


def mentions_to_id(s: str) -> str:
    return re.sub(r"<[@#][&!]?([0-9]{18,21})>", r"\1", s)


class Rule:
    def __init__(self, rule: str):
        # Normalize mentions
        self.string = mentions_to_id(rule)
        self.ast = ast.parse(self.string, mode="eval").body

    def __repr__(self):
        return self.string

    def with_mentions(self):
        return re.sub(r"([0-9]{18,21})", r"<@&\1>", self.string)

    def eval(self, member: Member):
        return self._eval({r.id for r in member.roles}, self.ast)

    def _eval(self, roles: Set[int], node):

        if isinstance(node, ast.Num):  # Role ID
            return node.n in roles
        elif isinstance(node, ast.BoolOp):  # <left> <operator> <right>
            if isinstance(node.op, ast.And):
                return self._eval(roles, node.values[0]) and self._eval(roles, node.values[1])
            elif isinstance(node.op, ast.Or):
                return self._eval(roles, node.values[0]) or self._eval(roles, node.values[1])
        elif isinstance(node, ast.Compare):
            pass
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval(roles, node.operand)

        # noinspection PyProtectedMember
        fields = ", ".join(
            f"{k}={getattr(node, k).__class__.__name__}" for k in node._fields
        )
        raise TypeError(f"Type de noeud non supporté: {node.__class__.__name__}({fields})")

    def roles_implied(self):
        """Return a set of all roles referenced in this rule."""
        return {int(r.group()) for r in re.finditer("[0-9]{18,21}", self.string)}


class RuleSet(dict):
    """
    A dictionnary of rules indexed py role/channel ids.

    It saves itself on the disk at File.RULES every time it is modified.
    There should not be multiple instances of this class.
    """

    def __delitem__(self, key):
        super().__delitem__(key)
        self.save()

    def __setitem__(self, key, value):
        assert not self.add_collisions(key, value)

        super(RuleSet, self).__setitem__(key, value)
        self.save()

    def roles(self, guild: Guild) -> Iterator[Tuple[discord.Role, Rule]]:
        """Iterate over the pairs (Role, Rule) in a given guild."""
        for item, rule in self.items():

            role = guild.get_role(item)
            if role is not None:
                yield role, rule

    @classmethod
    def load(cls):
        rules = yaml.load(File.RULES.read_text())

        return cls({item: Rule(r) for item, r in rules.items()})

    def save(self):
        dict_ = {item: str(r) for item, r in self.items()}

        File.RULES.write_text(yaml.dump(dict_))

    def add_collisions(self, item: int, rule: Rule) -> set:
        """
        Return the set conflicts that would arise if the rule were added to the Rules.
        """

        implied = rule.roles_implied()

        inputs = set(self) | {item}
        outputs = {o for r in self.values() for o in r.roles_implied()} | implied

        return inputs & outputs


class PermsCog(Cog, name="Permissions"):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.rules = RuleSet.load()
        self.modifying = defaultdict(int)

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        """This is the main listener where roles and permissions are updated."""

        bef = set(before.roles)
        now = set(after.roles)
        diff = bef.symmetric_difference(now)

        if not diff:
            # We only care about role changes
            return

        print(after)
        print(bef)
        print(now)

        # Check what the rules are supposed to give
        role_need = {role for role, rule in self.rules.roles(after.guild) if rule.eval(after)}
        # Find what rules were giving before
        # This is better than checking which roles one has,
        # as roles manually assigned (when the rule would not)
        # are not removed
        role_have = {role for role, rule in self.rules.roles(after.guild) if rule.eval(before)}

        add = role_need - role_have
        rem = (role_have - role_need) & now  # Remove only roles it has

        if not add and not rem:
            return  # Nothing to do !

        # Logging what happens. We are in trouble, maybe if we reach this point
        # more than twice for the same member
        s = lambda x: french_join(r.mention for r in x) or "None"
        await self.bot.get_channel(DEV_BOT_CHANNEL).send(embed=myembed(
            f"Role race of level {self.modifying[after.id]}" if self.modifying[after.id] else "No race (yet)",
            after.mention,
            Before=s(bef),
            After=s(now),
            Diff=s(diff),
            Add=s(add),
            Rem=s(rem),
        ))

        self.modifying[after.id] += 1
        if self.modifying[after.id] > 1:
            # Abort if two calls try to modify roles.
            return

        # Change roles (one by one)
        if add:
            await after.add_roles(*add)
        if rem:
            await after.remove_roles(*rem)
        del self.modifying[after.id]

    def input_chan_or_role(self, val):
        """
        Convert a string that contains an int or a channel/role mention to an int.

        Raises EpflError when it cannot.
        """

        try:
            return int(mentions_to_id(val))
        except ValueError:
            raise EpflError(f"Channel or role format not understood: `{val}`")

    def get_role_or_channel(self, id_, guild: Guild):
        # This makes sure we take a role/channel from the guild and don't modify other guilds.
        return guild.get_role(id_) or guild.get_channel(id_)

    @group("perms", invoke_without_command=True, hidden=True, aliases=["p", "permissions"])
    async def perms(self, ctx: Context):
        """Affiche l'aide pour le setup des permissions."""
        await ctx.invoke(self.bot.get_command("help"), "perms")

    @has_role(Role.MODO)
    @perms.command("set")
    async def perms_set_cmd(self, ctx: Context, channel_or_role, *, rule: Rule):
        """
        (modo) Setup des roles ou permissions automatiques.

        TODO: write doc.
        """

        # Parse input
        channel_or_role = self.input_chan_or_role(channel_or_role)

        # Abort if we don't know what we are talking about
        item = self.get_role_or_channel(channel_or_role, ctx.guild)
        if not item:
            raise EpflError("Channel or role not found!")

        # Abort if conflicts with other rules
        conflicts = self.rules.add_collisions(channel_or_role, rule)
        if conflicts:
            conflicts_str = french_join(
                ctx.guild.get_role(r).mention for r in conflicts
            )
            raise EpflError(
                "The set of all rules input must be distinct from the set out all rules output."
                f" Conflicts: {conflicts_str}"
            )

        # We have different logic for roles and permissions.
        if isinstance(item, discord.Role):
            await self.change_auto_role(ctx, item, rule)
        else:  # Channel
            await self.change_auto_channel(ctx, item, rule)

        await ctx.send("Done !")

    async def change_auto_role(self, ctx: Context, role: discord.Role, rule: Optional[Rule]):
        """
        Update all members when we modify a Role rule but ask for confirmation first.

        It is supposed that rule is in self.rules.
        If rule is None, it deletes the current one.

        This method mddifies self.rules.
        """

        have_role = set(role.members)
        need_role = set() if rule is None else {m for m in role.guild.members if rule.eval(m)}

        to_remove = have_role - need_role
        to_add = need_role - have_role

        embed = myembed(
            "Automatic role confirmation",
            "Please make sure this is what you want.",
            Role=role.mention,
            Rule=rule.with_mentions() if rule is not None else "Deleting",
            Added=len(to_add),
            Removed=len(to_remove),
        )
        if not await confirm(ctx, self.bot, embed=embed):
            return

        member: Member
        for member in to_remove:
            await member.remove_roles(role)
        for member in to_add:
            await member.add_roles(role)

        if rule is None:
            del self.rules[role.id]
        else:
            self.rules[role.id] = rule

    async def change_auto_channel(self, ctx: Context, channel: GuildChannel, rule: Rule):
        await ctx.send("mdr j'ai pas implémenté ça moi :joy:")

    @has_role(Role.MODO)
    @perms.command("show")
    async def perms_show_cmd(self, ctx: Context, raw: bool = False):
        """(modo) Affiche les permissions automatiques."""

        descr = "Voici la liste des permissions que le bot synchronise sur ce serveur. \n"

        for item, rule in self.rules.items():
            obj = self.get_role_or_channel(item, ctx.guild)
            if not obj: continue

            if raw:
                descr += f"{obj.mention} ({item}): \n{rule.with_mentions()}\n {rule}\n\n"
            else:
                descr += f"{obj.mention}: {rule.with_mentions()}\n"

        embed = discord.Embed(
            colour=EMBED_COLOR,
            title="Automatic permissions",
            description=descr,
        )
        await ctx.send(embed=embed)

    @has_role(Role.MODO)
    @perms.command("del")
    async def perms_del_cmd(self, ctx: Context, channel_or_role):
        """(modo) Supprime une regle automatique."""
        item = self.input_chan_or_role(channel_or_role)
        if item not in self.rules:
            await ctx.send("Nothing to delete.")
            return

        obj = self.get_role_or_channel(item, ctx.guild)
        if isinstance(obj, discord.Role):
            await self.change_auto_role(ctx, obj, None)
        else:
            await self.change_auto_channel(ctx, obj, None)

        await ctx.send("Done !")


def setup(bot: CustomBot):
    bot.add_cog(PermsCog(bot))
