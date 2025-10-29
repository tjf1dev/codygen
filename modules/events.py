from typing import Any
from discord.ext import commands
from ext.logger import logger
from ext.ui_base import Message
from discord import app_commands
from ext import errors
from ext.colors import Color
import aiosqlite
import discord
# this cog is focused on my server rather than the public


class events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = ""
        self.allowed_contexts = discord.app_commands.allowed_contexts(
            True, False, False
        )

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


async def setup(bot):
    await bot.add_cog(events(bot))
