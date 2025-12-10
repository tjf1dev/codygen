from typing import Any
from discord.ext import commands
from ext.logger import logger
from ext.ui_base import Message
from ext.utils import get_xp, xp_to_level
from discord import app_commands
from ext import errors
from ext.colors import Color
import aiosqlite
import discord
from models import Cog
# this cog is focused on my server rather than the public


class events(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "premade events for engagement!!"
        self.allowed_contexts = discord.app_commands.allowed_contexts(
            True, False, False
        )
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @app_commands.allowed_installs(True, False)
    @app_commands.allowed_contexts(True, False, False)
    @app_commands.guild_only
    @commands.hybrid_group(name="events", description="")
    async def events(self, ctx: commands.Context): ...

    @app_commands.allowed_contexts(True, False, False)
    @app_commands.allowed_installs(True, False)
    @events.group(name="uotm", description="user of the month event")
    async def uotm(self, ctx: commands.Context): ...

    @app_commands.allowed_contexts(True, False, False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        name="name of the event (usually the month)",
        make_active="should the event automatically become the active one",
    )
    @uotm.command(name="start", description="starts a user of the month event")
    async def uotm_start(
        self, ctx: commands.Context, name: str, make_active: bool = True
    ):
        if not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        cur = await db.cursor()
        try:
            await cur.execute(
                "INSERT INTO uotm_events (name, guild_id) VALUES (?,?)",
                (name, ctx.guild.id),
            )
            await db.commit()

        except aiosqlite.DatabaseError:
            raise errors.CodygenError("something went wrong")
        id = cur.lastrowid
        await cur.execute("UPDATE uotm_events SET active = 0")
        await cur.execute("UPDATE uotm_events SET active = 1 WHERE event_id=?", (id,))
        await db.commit()
        await ctx.reply(
            view=Message(
                f"## event created!\n> name: `{name}`\n> active: {'`yes`' if make_active else '`no`'}\n> id: {id}"
            ),
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.allowed_contexts(True, False, False)
    @app_commands.allowed_installs(True, False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        id="the event id",
    )
    @uotm.command(name="manage", description="manages a uotm event")
    async def uotm_manage(self, ctx: commands.Context, id: int):
        db: aiosqlite.Connection = self.bot.db
        candidate_count = await (
            await db.execute(
                "SELECT COUNT(*) FROM uotm_candidates WHERE event_id = ?", (id,)
            )
        ).fetchone()
        vote_count = await (
            await db.execute(
                "SELECT COUNT(*) FROM uotm_votes WHERE event_id = ?", (id,)
            )
        ).fetchone()
        event = await (
            await db.execute(
                "SELECT name, active FROM uotm_events WHERE event_id=?", (id,)
            )
        ).fetchone()
        if not event:
            raise errors.CodygenUserError("event not found")
        if not candidate_count:
            candidate_count = [0]
        if not vote_count:
            vote_count = [0]

        class DeleteButton(discord.ui.Button):
            def __init__(
                self,
                *,
                user: int,
                style: discord.ButtonStyle = discord.ButtonStyle.danger,
                label: str = "Delete",
            ):
                self.user = user
                super().__init__(style=style, label=label)

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.user:
                    await interaction.response.send_message(
                        "cannot interact with this message", ephemeral=True
                    )

                class DeleteConfirmButton(discord.ui.Button):
                    def __init__(
                        self,
                        *,
                        style: discord.ButtonStyle = discord.ButtonStyle.danger,
                        label: str = "Yes, delete",
                    ):
                        super().__init__(style=style, label=label)

                    async def callback(self, interaction: discord.Interaction) -> Any:
                        cur = await db.cursor()
                        await cur.execute(
                            "DELETE FROM uotm_events WHERE event_id=?", (id,)
                        )
                        await db.commit()
                        await interaction.response.send_message(
                            view=Message(f"## event `#{id}` deleted successfully."),
                            ephemeral=True,
                        )
                        if not interaction.message:
                            return
                        await interaction.message.edit(view=Message("<deleted event>"))

                await interaction.response.send_message(
                    view=discord.ui.LayoutView().add_item(
                        discord.ui.Container(accent_color=Color.negative).add_item(
                            discord.ui.Section(
                                accessory=DeleteConfirmButton()
                            ).add_item(
                                discord.ui.TextDisplay(
                                    "are you sure you want to delete this event?"
                                )
                            )
                        )
                    ),
                    ephemeral=True,
                )

        class MakeActiveButton(discord.ui.Button):
            def __init__(
                self,
                *,
                style: discord.ButtonStyle = discord.ButtonStyle.secondary,
                active: bool,
                user: int,
            ):
                # current state
                self.active = active
                self.user = user
                super().__init__(
                    style=discord.ButtonStyle.secondary
                    if not active
                    else discord.ButtonStyle.primary,
                    label=f"{'Start again' if not active else 'Finish'}",
                )

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.user:
                    await interaction.response.send_message(
                        "cannot interact with this message", ephemeral=True
                    )
                old_active = self.active
                active = int(not old_active)
                logger.debug(f"making event {id} from {old_active} to {int(active)}")
                cur = await db.cursor()
                await cur.execute(
                    "UPDATE uotm_events SET active=? WHERE guild_id=?",
                    (
                        0,
                        interaction.guild_id,
                    ),
                )
                await cur.execute(
                    "UPDATE uotm_events SET active=? WHERE event_id=?",
                    (
                        active,
                        id,
                    ),
                )
                logger.debug(f"event {id} is now {int(active)}")
                await db.commit()
                if not interaction.message:
                    logger.warning("interaction.message doesnt exist")
                    return
                await interaction.message.edit(
                    view=discord.ui.LayoutView().add_item(
                        discord.ui.Container()
                        .add_item(
                            discord.ui.TextDisplay(
                                f"## event `#{id}`\n> candidates: `{candidate_count[0]}`\n> votes: `{vote_count[0]}`\n> name: `{event[0]}`\n> active: {'`yes`' if active else '`no`'}"
                            )
                        )
                        .add_item(
                            discord.ui.ActionRow()
                            .add_item(
                                MakeActiveButton(active=bool(active), user=self.user)
                            )
                            .add_item(DeleteButton(user=self.user))
                        )
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                await interaction.response.send_message(
                    f"this event is now marked as {'in' if not active else ''}active!",
                    ephemeral=True,
                )

        view = discord.ui.LayoutView().add_item(
            discord.ui.Container()
            .add_item(
                discord.ui.TextDisplay(
                    f"## event `#{id}`\n> candidates: `{candidate_count[0]}`\n> votes: `{vote_count[0]}`\n> name: `{event[0]}`\n> active: {'`yes`' if event[1] else '`no`'}"
                )
            )
            .add_item(
                discord.ui.ActionRow()
                .add_item(MakeActiveButton(active=event[1], user=ctx.author.id))
                .add_item(DeleteButton(user=ctx.author.id))
            )
        )
        await ctx.reply(
            view=view,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.allowed_contexts(True, False, False)
    @uotm.command(name="apply", description="applies for the current uotm event")
    async def uotm_apply(self, ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        xp = await get_xp(ctx.author, self.bot)
        if not xp:
            level = 0
        else:
            level = xp_to_level(xp)
        if level < 10:
            await ctx.reply(
                view=Message(
                    f"to apply for UOTM, you must have at least level 10! you are level {level}",
                    accent_color=Color.negative,
                )
            )
            return
        current_event = await (
            await db.execute(
                "SELECT (guild_id, event_id, name, timestamp) FROM uotm_events WHERE guild_id=? AND active=1",
                (ctx.guild.id,),
            )
        ).fetchone()
        if not current_event:
            await ctx.reply(
                view=Message(
                    "no UOTM event running right now!", accent_color=Color.negative
                )
            )
            return
        await db.execute(
            "INSERT INTO uotm_canidates (event_id, user_id) VALUES (?,?)",
            (current_event[1], ctx.author.id),
        )
        await db.commit()
        await ctx.reply(
            view=Message(
                f"## applied successfully!\nyou are now a candidate for the **{current_event[2]}** user of the month event."
            )
        )

    @app_commands.allowed_contexts(True, False, False)
    @uotm.command(name="vote", description="vote for a uotm candidate")
    async def uotm_vote(self, ctx: commands.Context, target: discord.Member):
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        xp = await get_xp(ctx.author, self.bot)
        if not xp:
            level = 0
        else:
            level = xp_to_level(xp)
        if level < 5:
            await ctx.reply(
                view=Message(
                    f"to vote in UOTM, you must have at least level 5! you are level {level}",
                    accent_color=Color.negative,
                )
            )
            return
        current_event = await (
            await db.execute(
                "SELECT (guild_id, event_id, name, timestamp) FROM uotm_events WHERE guild_id=? AND active=1",
                (ctx.guild.id,),
            )
        ).fetchone()
        if not current_event:
            await ctx.reply(
                view=Message(
                    "no UOTM event running right now!", accent_color=Color.negative
                )
            )
            return
        candidates = await (
            await db.execute(
                "SELECT (user_id) FROM uotm_candidates WHERE event_id=?",
                (current_event[1],),
            )
        ).fetchall()
        if not candidates:
            await ctx.reply(
                view=Message(
                    "there are no candidates yet!", accent_color=Color.negative
                )
            )
            return
        is_valid = False
        for c in candidates:
            if c[1] == target.id:
                is_valid = True

        if not is_valid:
            await ctx.reply(
                view=Message(
                    "that isnt a valid candidate!", accent_color=Color.negative
                )
            )
            return
        await db.execute(
            "INSERT INTO uotm_votes (event_id, user_id, vote_id) VALUES (?,?)",
            (current_event[1], ctx.author.id, target.id),
        )
        await db.commit()
        await ctx.reply(
            view=Message(f"## voted successfully!\nvote placed for {target.mention}")
        )

    @app_commands.allowed_contexts(True, False, False)
    @uotm.command(name="summary", description="check state of the current uotm")
    async def uotm_summary(self, ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        current_event = await (
            await db.execute(
                "SELECT (guild_id, event_id, name, timestamp) FROM uotm_events WHERE guild_id=? AND active=1",
                (ctx.guild.id,),
            )
        ).fetchone()
        if not current_event:
            await ctx.reply(
                view=Message(
                    "no UOTM event running right now!", accent_color=Color.negative
                )
            )
            return
        votes = await (
            await db.execute(
                "SELECT vote_id FROM uotm_votes WHERE event_id=?", (current_event[1],)
            )
        ).fetchall()
        if not votes:
            await ctx.reply(
                view=Message("no votes placed yet!", accent_color=Color.negative)
            )
            return
        total = len(list(votes))
        counts = {}

        for (vote_id,) in votes:
            counts[vote_id] = counts.get(vote_id, 0) + 1

        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        vote_str = ""
        for idx, (cid, num) in enumerate(sorted_counts, start=1):
            pct = (num / total) * 100 if total else 0
            vote_str += f"{idx}. <@{cid}>\n-# `{num}` votes, `{pct:.1f}%`\n"

        await ctx.reply(
            view=Message(f"## user of the month {current_event[1]}\n{vote_str}")
        )


async def setup(bot):
    await bot.add_cog(events(bot))
