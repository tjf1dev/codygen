import discord
from discord.ext import commands
from ext.colors import Color
from typing import cast, Any
import datetime
from ext.utils import timestamp, describe_message
from ext.logger import logger
import time
from ext.ui_base import Message
from models import Codygen
import aiohttp
from typing import Dict
from discord import app_commands
from views import LoggingSetupLayout
from views.logging_setup import LoggingSetupStart
from models import Event
import json

_event_registry: Dict[str, Event] = {}
_event_category_map = {1: "Message", 2: "Channel", 3: "Server"}


def log_event(name: str, category: int):
    """
    decorator to mark a function as a loggable event.
    """

    def decorator(func):
        global _event_registry
        if category not in _event_category_map.keys():
            raise ValueError(f"Invalid category: '{category}'")
        _event_registry[func.__name__] = Event(
            name, category, func.__name__, _event_category_map[category]
        )
        return func

    return decorator


# TODO add codygen's custom logs (levelup, ticket create, command triggered, prefix change, etc)
class logging(commands.Cog):
    def __init__(self, bot):
        self.bot = cast(Codygen, bot)
        self.session = aiohttp.ClientSession()
        self.cid = 1416136572977549502

    def list_events(self) -> Dict[str, Event]:
        """
        return all registered events
        """
        return dict(_event_registry)

    @property
    def event_registry(self):
        return _event_registry

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__qualname__}")

    async def create_webhook(self, channel: discord.TextChannel):
        """creates a webhook from a channel id and adds it to the database"""
        user = cast(discord.ClientUser, self.bot.user)
        channel_id = channel.id
        db = self.bot.db
        channel = cast(discord.TextChannel, self.bot.get_channel(channel_id))
        if not channel:
            logger.warning("failed; couldn't fetch channel")
            return
        avatar_bytes = None
        if user.display_avatar:
            async with self.session.get(user.display_avatar.url) as resp:
                avatar_bytes = await resp.read()
        webhook = await channel.create_webhook(
            name="codygen logging", avatar=avatar_bytes
        )
        webhook_row = (webhook.id, webhook.token)
        await db.execute(
            "INSERT INTO webhooks (channel_id, guild_id, webhook_id, webhook_token) VALUES (?,?,?,?)",
            (channel_id, channel.guild.id, webhook.id, webhook.token),
        )
        await db.commit()
        logger.debug(f"created webhook in {channel_id}")
        return webhook_row

    async def delete_webhook(self, webhook_id: int):
        """deletes a webhook. warning; this only removes the webhook entry in the database, used for deleting non-existent ones"""
        await self.bot.db.execute(
            """DELETE FROM webhooks WHERE webhook_id=?""", (webhook_id,)
        )
        await self.bot.db.commit()
        logger.debug(f"deleted webhook {webhook_id}")

    def get_changes(self, before, after) -> dict[str, str]:
        """
        compare two objects and return a dict of changed attributes.
        formatted as `old_value -> new_value`.
        use as kwargs for update events
        """
        changes = {}

        def normalize(val):
            if val is None or val == "":
                return None
            return val

        for attr in dir(before):
            if attr.startswith("_"):
                continue
            if callable(getattr(before, attr)):
                continue

            before_val = getattr(before, attr, None)
            after_val = getattr(after, attr, None)

            if normalize(before_val) != normalize(after_val):
                # use .name for objects like category or guild
                if attr == "Colour":
                    continue  # Color has already been passed
                if hasattr(before_val, "name") and hasattr(after_val, "name"):
                    changes[attr.capitalize().replace("_", " ")] = (
                        f"{getattr(before_val, 'name', before_val)} -> {getattr(after_val, 'name', after_val)}"
                    )
                else:
                    changes[attr.capitalize().replace("_", " ")] = (
                        f"`{before_val}` -> `{after_val}`"
                    )

        return changes

    def event_from_title(self, name: str):
        found = next(
            (event for event in _event_registry.values() if event.name == name),
            None,
        )
        return found

    async def get_log_channel(self, guild: discord.Guild, title: str) -> int:
        db = self.bot.db
        event = self.event_from_title(title)
        if not event:
            raise ValueError(f"Couldn't find event from title {title!r}")
        eid = event.id
        gid = guild.id
        logging_settings = await (
            await db.execute(
                "SELECT logging_settings FROM guilds WHERE guild_id=?", (gid,)
            )
        ).fetchone()
        if not logging_settings:
            return 0
        logging_settings = json.loads(logging_settings[0])
        return logging_settings.get(eid, {}).get("channel", None)

    async def send_log(
        self,
        title: str,
        description: str,
        guild: discord.Guild,
        type: tuple[int, Any] = (0, None),
        color=None,
        **kwargs,
    ):
        """central method to send an embed to the logging channel"""

        # this is a lot of database queries!!!
        # i can count like 3 per every event
        # i am not gonna do anything about this
        def get_category_name(name):
            found = next(
                (
                    event.category_name
                    for event in _event_registry.values()
                    if event.name == name
                ),
                None,
            )
            return found

        log_channel = await self.get_log_channel(guild, title)
        if not log_channel:
            return  # logging is not enabled in this server
        logger.debug(f"log channel: {log_channel}")
        log_channel_obj = cast(
            discord.TextChannel,
            self.bot.get_channel(log_channel)
            or await self.bot.fetch_channel(log_channel),
        )
        kwargs = {k.replace("_", " ").capitalize(): v for k, v in kwargs.items()}
        logger.debug(f"{title} in {guild.name} ({guild.id})")
        db = self.bot.db
        webhook_row = await (
            await db.execute(
                "SELECT webhook_id, webhook_token FROM webhooks WHERE channel_id=?",
                (log_channel,),
            )
        ).fetchone()
        user = cast(discord.ClientUser, self.bot.user)
        if not webhook_row:
            logger.warning(f"no webhook found: {webhook_row}, creating one...")
            webhook_row = await self.create_webhook(log_channel_obj)

        msg_title = discord.ui.TextDisplay(f"## {title}")
        msg_sep = discord.ui.Separator()
        if type[0] == 1:
            member: discord.Member = type[1]
            if not isinstance(type[1], discord.Member):
                raise TypeError("type 1 special log is not a member")
            msg_desc = discord.ui.Section(
                accessory=discord.ui.Thumbnail(await member.display_avatar.to_file())
            ).add_item(discord.ui.TextDisplay(f"{description}"))
        msg_desc = discord.ui.TextDisplay(f"{description}")
        msg_con = (
            discord.ui.Container(accent_color=color or Color.info)
            .add_item(msg_title)
            .add_item(msg_sep)
            .add_item(msg_desc)
        )
        fields = ""
        for key, val in kwargs.items():
            fields += f"### {key}\n{val}\n"
        if fields:
            msg_sep_2 = discord.ui.Separator()
            msg_fields = discord.ui.TextDisplay(fields)
            msg_con.add_item(msg_sep_2)
            msg_con.add_item(msg_fields)
        msg_sep_3 = discord.ui.Separator()
        msg_timestamp = discord.ui.TextDisplay(
            f"-# {timestamp(time.time())} | {get_category_name(title)}"
        )
        msg_con.add_item(msg_sep_3)
        msg_con.add_item(msg_timestamp)
        msg = discord.ui.LayoutView().add_item(msg_con)
        assert webhook_row is not None
        webhook = discord.Webhook.from_url(
            f"https://discord.com/api/webhooks/{webhook_row[0]}/{webhook_row[1]}",
            session=self.session,
        )
        try:
            await webhook.send(
                view=msg,
                allowed_mentions=discord.AllowedMentions.none(),
                username=user.display_name or user.name,
                avatar_url=user.display_avatar.url,
            )
        except discord.errors.NotFound:
            logger.warning(
                f"tried to send to a non-existent webhook in {log_channel}! attemping to create new webhook..."
            )
            await self.delete_webhook(webhook.id)
            webhook_row = await self.create_webhook(log_channel_obj)
            assert webhook_row is not None
            webhook = discord.Webhook.from_url(
                f"https://discord.com/api/webhooks/{webhook_row[0]}/{webhook_row[1]}",
                session=self.session,
            )
            await webhook.send(
                view=msg,
                allowed_mentions=discord.AllowedMentions.none(),
                username=user.display_name or user.name,
                avatar_url=user.display_avatar.url,
            )

    @commands.hybrid_group(name="logging", description="log useful information")
    async def logging(self, ctx: commands.Context):
        return

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @logging.command(
        name="setup", description="help setup a log channel and default setings"
    )
    async def logging_setup(self, ctx: commands.Context):
        if not ctx.interaction:
            await ctx.reply(
                view=LoggingSetupStart(self.bot, cast(discord.User, ctx.author))
            )
            return
        await ctx.reply(view=LoggingSetupLayout(self.bot))

    @app_commands.default_permissions(discord.Permissions(administrator=True))
    @logging.command(
        name="disable_logs", description="disabled logging in this server."
    )
    async def logging_disable(self, ctx: commands.Context):
        if not ctx.guild:
            return
        db = self.bot.db
        await db.execute(
            "UPDATE guilds SET logging_settings=? WHERE guild_id=?",
            ("{}", ctx.guild.id),
        )
        await db.commit()
        await ctx.reply(
            view=Message("## logging has been disabled.", accent_color=Color.negative)
        )

    async def event_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        events = self.list_events()
        parts = current.split()
        prefix = " ".join(parts[:-1])
        latest = parts[-1] if parts else ""

        choices = []
        for event in events.values():
            if (
                event.id.lower().startswith(latest.lower())
                and event.id.lower() not in parts
            ):
                if prefix:
                    value = f"{prefix} {event.id}"
                else:
                    value = event.id
                choices.append(app_commands.Choice(name=value, value=value))

        return choices

    @app_commands.default_permissions(discord.Permissions(administrator=True))
    @logging.command(
        name="unset_channel", description="unset a channel for specific events."
    )
    @app_commands.describe(
        events="event ids. e.g 'on_message_edit on_message_delete' (use * for all)"
    )
    @app_commands.autocomplete(events=event_autocomplete)
    async def logging_unset_channel(self, ctx: commands.Context, *, events):
        if not ctx.guild:
            return
        all_events = self.list_events()
        if events == "*":
            events = list(all_events.keys())
        else:
            events = events.split()
        for event in events:
            if event not in all_events.keys():
                await ctx.reply(
                    view=Message(
                        f"{event}: not an event. try running /logging check to see available events (e.g. `on_message_edit`)",
                        accent_color=Color.negative,
                    )
                )
                return
        logging_settings_row = await (
            await self.bot.db.execute(
                "SELECT logging_settings FROM guilds WHERE guild_id=?",
                (ctx.guild.id,),
            )
        ).fetchone()
        if not logging_settings_row or not logging_settings_row[0]:
            await ctx.reply(
                view=Message(
                    "## logging is not enabled in this server.\ntry running /logging setup",
                    accent_color=Color.negative,
                )
            )
            return
        logging_settings: dict = json.loads(logging_settings_row[0])
        for event in events:
            logging_settings[event]["channel"] = 0
        logging_settings_out = json.dumps(logging_settings)
        await self.bot.db.execute(
            "UPDATE guilds SET logging_settings=? WHERE guild_id=?",
            (logging_settings_out, ctx.guild.id),
        )
        await self.bot.db.commit()
        await ctx.reply(
            view=Message(
                f"## updated successfully\n{'\n'.join([f'> - - `{e}`>' for e in events])}",
                accent_color=Color.positive,
            )
        )

    @app_commands.default_permissions(discord.Permissions(administrator=True))
    @logging.command(name="check", description="checks if logging set up correctly")
    async def logging_check(self, ctx: commands.Context):
        db = self.bot.db
        if not ctx.guild:
            return

        events = await (
            await db.execute(
                "SELECT logging_settings FROM guilds WHERE guild_id=?", (ctx.guild.id,)
            )
        ).fetchone()
        fail = False
        if not events or events[0] == "{}":
            fail = True
            events = ("{}",)
        events = json.loads(events[0])
        # logger.debug(events)
        webhooks = list(
            await (
                await db.execute(
                    "SELECT webhook_id, webhook_token FROM webhooks WHERE guild_id=?",
                    (ctx.guild.id,),
                )
            ).fetchall()
        )
        webhook_fail = False

        if not webhooks:
            webhook_fail = True
        else:
            webhook = discord.Webhook.from_url(
                f"https://discord.com/api/webhooks/{webhooks[0][0]}/{webhooks[0][1]}",
                session=self.session,
            )
            try:
                webhook = await webhook.fetch()
            except discord.errors.NotFound:
                webhook_fail = True
            if webhook_fail:
                webhooks = []
                webhook.name = "failed to fetch!"
        events_text = ""
        for event in events.values():
            events_text += f"- {event['meta']['name']} (`{event['meta']['category']}`, `{event['meta']['id']}`) - <#{event['channel']}>\n"
        if fail:
            view = Message(
                f"## logging for {cast(discord.Guild, ctx.guild).name}"
                f"{f'\n> webhooks: {len(webhooks)}' if webhooks else ''}"
                f"\n> logging is not set up. try running /logging setup."
            )
        else:
            view = Message(
                f"## logging for {cast(discord.Guild, ctx.guild).name}\n"
                f"{f'\n> webhooks: {len(webhooks)}' if webhooks else ''}"
                f"{'\n-# :warning: seems like there are no webhooks yet. this will be fixed once the first log is sent.' if not list(webhooks) else '\n-# :white_check_mark: logging working correctly!'}\n"
                f"{len(events)} events registered\n{events_text}"
            )
        await ctx.reply(view=view)

    @app_commands.default_permissions(discord.Permissions(administrator=True))
    @logging.command(
        name="set_channel", description="set a channel for specific events."
    )
    @app_commands.describe(
        events="event ids. e.g 'on_message_edit on_message_delete' (use * for all)"
    )
    @app_commands.autocomplete(events=event_autocomplete)
    async def logging_set_channel(
        self, ctx: commands.Context, channel: discord.TextChannel, *, events
    ):
        if not ctx.guild:
            return
        all_events = self.list_events()
        if events == "*":
            events = list(all_events.keys())
        else:
            events = events.split()
        for event in events:
            if event not in all_events.keys():
                await ctx.reply(
                    view=Message(
                        f"{event}: not an event. try running /logging check to see available events (e.g. `on_message_edit`)",
                        accent_color=Color.negative,
                    )
                )
                return
        logging_settings_row = await (
            await self.bot.db.execute(
                "SELECT logging_settings FROM guilds WHERE guild_id=?",
                (ctx.guild.id,),
            )
        ).fetchone()
        if not logging_settings_row or not logging_settings_row[0]:
            await ctx.reply(
                view=Message(
                    "## logging is not enabled in this server.\ntry running /logging setup",
                    accent_color=Color.negative,
                )
            )
            return
        logging_settings = json.loads(logging_settings_row[0])
        for event in events:
            logging_settings[event]["channel"] = channel.id
        logging_settings_out = json.dumps(logging_settings)
        await self.bot.db.execute(
            "UPDATE guilds SET logging_settings=? WHERE guild_id=?",
            (logging_settings_out, ctx.guild.id),
        )
        await self.bot.db.commit()
        await ctx.reply(
            view=Message(
                f"## updated successfully\n{'\n'.join([f'> - `{e}` - <#{channel.id}>' for e in events])}",
                accent_color=Color.positive,
            )
        )

    # * CATEGORY 1: MESSAGES AND POLLS
    @log_event("Message edit", 1)
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.send_log(
            title="Message edit",
            description=f"> ID: `{after.id}`\n"
            f"> Channel: {cast(discord.TextChannel, before.channel).mention} ([`{before.channel.id}`]({before.channel.jump_url}))\n"
            f"> Author: {after.author.mention} (`{after.author.name}` • `{after.author.id}`)\n"
            f"> Created: {timestamp(before.created_at.timestamp())}\n",
            Before=f"{describe_message(before)}",
            After=f"{describe_message(after)}",
            color=Color.warn,
            guild=cast(discord.Guild, before.guild),
        )

    @log_event("Message delete", 1)
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await self.send_log(
            title="Message delete",
            description=f"> ID: `{message.id}`\n"
            f"> Channel: {cast(discord.TextChannel, message.channel).mention} ([`{message.channel.id}`]({message.channel.jump_url}))\n"
            f"> Author: {message.author.mention} (`{message.author.name}` • `{message.author.id}`)\n"
            f"> Created: {timestamp(message.created_at.timestamp())}\n",
            Content=f"{describe_message(message)}",
            color=Color.negative,
            guild=cast(discord.Guild, message.guild),
        )

    @log_event("Message purge", 1)
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        data = "".join(
            [
                f"[{m.created_at.strftime('%Y/%m/%d %H:%M:%S')}] {m.author.name} ({m.author.id}): {m.content}\n"
                for m in messages
            ]
        )
        message = messages[0]
        await self.send_log(
            title="Message purge",
            description=f"> Channel: {cast(discord.TextChannel, message.channel).mention} ([`{message.channel.id}`]({message.channel.jump_url}))\n"
            f"> Count: {len(messages)}\n",
            color=Color.negative,
            Data=f"```{data if len(data) < 4000 else '[too long to display]'}```",
            guild=cast(discord.Guild, message.guild),
        )

    @log_event("Poll vote added", 1)
    @commands.Cog.listener()
    async def on_poll_vote_add(
        self, user: discord.User | discord.Member, answer: discord.PollAnswer
    ):
        message = cast(discord.Poll, answer.poll).message
        channel = cast(discord.TextChannel, cast(discord.Message, message).channel)

        await self.send_log(
            title="Poll vote added",
            description=f"> Channel: {channel.mention} ([`{channel.id}`]({channel.jump_url}))\n> Ends: {timestamp(answer.poll.expires_at.timestamp()) if answer.poll.expires_at else '[unknown]'}",
            Vote=f"{user.mention} + `{answer.text}`",
            guild=channel.guild,
        )

    @log_event("Poll vote removed", 1)
    @commands.Cog.listener()
    async def on_poll_vote_remove(
        self, user: discord.User | discord.Member, answer: discord.PollAnswer
    ):
        message = cast(discord.Poll, answer.poll).message
        channel = cast(discord.TextChannel, cast(discord.Message, message).channel)

        await self.send_log(
            title="Poll vote removed",
            description=f"> Channel: {channel.mention} ([`{channel.id}`]({channel.jump_url}))\n> Ends: {timestamp(answer.poll.expires_at.timestamp()) if answer.poll.expires_at else '[unknown]'}",
            Vote=f"{user.mention} - `{answer.text}`",
            guild=channel.guild,
        )

    # * CATEGORY 2: GUILD AND CHANNEL UPDATES
    @log_event("Channel create", 2)
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        await self.send_log(
            title="Channel create",
            description=f"> ID: {channel.id}\n"
            f"> Channel: {channel.mention} ([`{channel.id}`]({channel.jump_url}))\n"
            f"> Category: {channel.category.name if channel.category else '[none]'} (position {channel.position})",
            guild=channel.guild,
            color=Color.info,
        )

    @log_event("Channel delete", 2)
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self.send_log(
            title="Channel delete",
            description=f"> ID: {channel.id}\n"
            f"> Channel: {channel.mention} ([`{channel.id}`]({channel.jump_url}))\n"
            f"> Created: {timestamp(channel.created_at.timestamp())}\n"
            f"> Category: {channel.category.name if channel.category else '[none]'} (position {channel.position})",
            guild=channel.guild,
            color=Color.info,
        )

    @log_event("Channel update", 2)
    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        changes = self.get_changes(before, after)
        await self.send_log(
            title="Channel update",
            description=f"> ID: {after.id}\n"
            f"> Channel: {after.mention} ([`{after.id}`]({after.jump_url}))\n"
            f"> Created: {timestamp(after.created_at.timestamp())}\n",
            guild=after.guild,
            color=Color.info,
            type=(0, None),
            **changes,
        )

    @log_event("Server update", 3)
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        # changes = self.get_changes(before, after)
        await self.send_log(
            title="Server update",
            description=f"> ID: {after.id}\n"
            f"> Created: {timestamp(after.created_at.timestamp())}\n",
            guild=after,
            color=Color.info,
            # **changes
        )

    @log_event("Invite create", 3)
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        guild = invite.guild
        if not isinstance(guild, discord.Guild):
            guild = await self.bot.fetch_guild(
                cast(discord.PartialInviteGuild, invite.guild).id
            )
        await self.send_log(
            title="Invite create",
            description=f"> Server: {guild.name} (`{guild.id}`)\n"
            f"> Expires: {timestamp(cast(datetime.datetime, invite.expires_at).timestamp())}\n",
            guild=guild,
            color=Color.info,
            # **changes
        )

    @log_event("Invite delete", 3)
    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        guild = invite.guild
        if not isinstance(guild, discord.Guild):
            guild = await self.bot.fetch_guild(
                cast(discord.PartialInviteGuild, invite.guild).id
            )
        await self.send_log(
            title="Invite delete",
            description=f"> Server: {guild.name} (`{guild.id}`)\n"
            f"> Expires: {timestamp(cast(datetime.datetime, invite.expires_at).timestamp())}\n",
            guild=guild,
            color=Color.negative,
            # **changes
        )

    @log_event("Member join", 3)
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        await self.send_log(
            title="Member join",
            description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n"
            f"> Account created: {timestamp(member.created_at.timestamp())}\n",
            guild=guild,
            color=Color.positive,
            type=(1, member),
            # **changes
        )

    @log_event("Member left", 3)
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        await self.send_log(
            title="Member left",
            description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n"
            f"> Account created: {timestamp(member.created_at.timestamp())}\n",
            guild=guild,
            color=Color.negative,
            type=(1, member),
            # **changes
        )

    @log_event("Member roles updated", 3)
    async def on_member_role_update(
        self, before: discord.Member, after: discord.Member
    ):
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added = after_roles - before_roles
        removed = before_roles - after_roles
        member = after
        if not removed and added:
            await self.on_member_role_add(before, after)
        if not added and removed:
            await self.on_member_role_remove(before, after)
        else:
            await self.send_log(
                title="Member roles updated",
                description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n",
                guild=after.guild,
                Roles_added=f"{'\n'.join([f'> `+` {r.mention} (`{r.id}`)' for r in added])}",
                Roles_removed=f"{'\n'.join([f'> `-` {r.mention} (`{r.id}`)' for r in removed])}",
            )
            return

    @log_event("Member roles added", 3)
    async def on_member_role_add(self, before: discord.Member, after: discord.Member):
        member = after
        before_roles = set(before.roles)
        after_roles = set(after.roles)

        added = after_roles - before_roles
        await self.send_log(
            title="Member roles added",
            description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n",
            guild=after.guild,
            Roles_added=f"{'\n'.join([f'> `+` {r.mention} ({r.id})' for r in added])}",
        )

    @log_event("Member roles removed", 3)
    async def on_member_role_remove(
        self, before: discord.Member, after: discord.Member
    ):
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        member = after
        removed = before_roles - after_roles
        await self.send_log(
            title="Member roles removed",
            description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n",
            guild=after.guild,
            Roles_removed=f"{'\n'.join([f'> `-` {r.mention} ({r.id})' for r in removed])}",
        )

    @log_event("Member nickname update", 3)
    async def on_member_nickname_update(
        self, before: discord.Member, after: discord.Member
    ):
        member = after
        await self.send_log(
            title="Member nickname update",
            description=f"> Member: {member.mention} (`{member.name}` `{member.id}`)\n",
            guild=after.guild,
            Old_nickname=f"`{before.nick or before.display_name or before.name}`",
            New_nickname=f"`{member.nick or member.display_name or member.name}`",
        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # here we don't log an event, just dispatch one of the sub-events
        # there arent much events supported though
        if before.roles != after.roles:
            await self.on_member_role_update(before, after)
        if before.nick != after.nick:
            await self.on_member_nickname_update(before, after)


async def setup(bot):
    await bot.add_cog(logging(bot))
