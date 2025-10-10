import discord
import os
import io
import time
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageOps
from main import logger
from ext.utils import xp_to_level, level_to_xp
import aiosqlite
from ext.ui_base import Message
from views import LevelRefreshSummaryLayout, LevelBoostsLayout, LevelupLayout
from ext.colors import Color
from typing import Any
from models import Codygen
import ext.errors


async def get_boosts(cur: aiosqlite.Cursor, guild: discord.Guild, user: discord.Member):
    # fetch global boost (guild)
    global_boost_res = await cur.execute(
        "SELECT percentage, expires FROM global_boosts WHERE guild_id=?", (guild.id,)
    )
    global_boost_row = await global_boost_res.fetchone()
    if global_boost_row is None:
        global_boost = {"percentage": 0, "expires": 0}
    else:
        global_boost = {
            "percentage": global_boost_row[0],
            "expires": global_boost_row[1],
        }

    # fetch role boosts
    try:
        user_roles = [role.id for role in user.roles]
    except AttributeError:
        user_roles = []
    # fetch user boosts
    user_boost_res = await cur.execute(
        "SELECT percentage, expires FROM user_boosts WHERE guild_id=? AND user_id=?",
        (guild.id, user.id),
    )
    user_boost_rows = await user_boost_res.fetchone()

    if not user_boost_rows:
        user_boost = {"percentage": 0, "expires": 0}
    else:
        user_boost = {
            "percentage": user_boost_rows[0],
            "expires": user_boost_rows[1],
        }
    role_boosts = await get_active_role_boosts(cur, user_roles)

    multiplier = 0

    multiplier += global_boost["percentage"]
    multiplier += user_boost["percentage"]
    for boost in role_boosts.keys():
        multiplier += role_boosts[boost]["percentage"]
    return {
        "multiplier": multiplier,
        "user": user_boost,
        "global": global_boost,
        "role": role_boosts,
    }


async def get_active_role_boosts(cur, role_ids):
    if not role_ids:
        return {}

    placeholders = ",".join("?" for _ in role_ids)
    query = f"""
        SELECT role_id, percentage, expires FROM role_boosts
        WHERE role_id IN ({placeholders})
    """
    cursor = await cur.execute(query, role_ids)
    rows = await cursor.fetchall()

    now = time.time()
    active_boosts = {}
    for role_id, percentage, expires in rows:
        if expires == -1 or expires > now:
            active_boosts[role_id] = {
                "percentage": percentage,
                "expires": expires,
            }
    return active_boosts


def split_embed_description(lines, max_length=4096) -> list:
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_length:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def boost_value(value, percentage) -> int:
    return value * (1 + percentage / 100)


def timestamp(unix: int | str, type: str = "R", infinite_msg: str = "never") -> str:
    """
    Generates a Discord timestamp out of a Unix timestamp.
    -1 for infinite
    """
    if unix == -1:
        return infinite_msg
    return f"<t:{unix}" + f":{type}>" if type else ">"


async def send_levelup(
    user: discord.Member,
    guild: discord.Guild,
    xp,
    new_xp,
    highest_boost: int,
    cur: aiosqlite.Cursor,
    old_level: int,
    new_level: int,
):
    """
    Sends a levelup message to the channel configured in the guild config.
    """
    rank_res = await cur.execute(
        "SELECT COUNT(*) FROM users WHERE guild_id=? AND xp > ?",
        (guild.id, xp),
    )
    rank_row = await rank_res.fetchone()
    place_in_leaderboard = rank_row[0] if rank_row else 1
    # logger.debug(f"place in leaderboard: {place_in_leaderboard}")
    if user.bot:
        return
    cid_res = await cur.execute(
        "SELECT levelup_channel FROM guilds WHERE guild_id=?", (guild.id,)
    )
    cid_row = await cid_res.fetchone()
    if not cid_row:
        return
    channel_id = cid_row[0]
    if not channel_id:
        return
    channel_before = guild.get_channel(channel_id)
    channel: discord.TextChannel | Any = (
        channel_before if channel_before else await guild.fetch_channel(channel_id)
    )
    # logger.debug(f"levelup channel: {channel_id}")
    if not channel:
        return
    # old_level = xp_to_level(xp - int(new_xp))
    # new_level = xp_to_level(xp)
    view = LevelupLayout(
        user,
        xp,
        place_in_leaderboard,
        highest_boost,
        old_level,
        new_level,
    )
    await channel.send(view=view)


async def reward_xp(
    member: discord.Member, guild: discord.Guild, con: aiosqlite.Connection, xp
):
    """
    if applicable grants roles for the user based on their xp
    """
    cur: aiosqlite.Cursor = await con.cursor()

    rewards_res = await cur.execute(
        "SELECT level, reward_id FROM level_rewards WHERE guild_id=?",
        (guild.id,),
    )
    rewards = await rewards_res.fetchall()
    list(rewards).sort(key=lambda x: x[0])

    user_level = xp_to_level(xp)
    roles_to_add = [
        role_id for level_required, role_id in rewards if user_level >= level_required
    ]

    current_role_ids = {role.id for role in member.roles}
    missing_roles = [
        role_id for role_id in roles_to_add if role_id not in current_role_ids
    ]

    roles_to_remove = [
        role_id
        for level_required, role_id in rewards
        if user_level < level_required and role_id in current_role_ids
    ]
    added_roles = {}
    removed_roles = {}
    if missing_roles:
        try:
            roles_to_add = [
                role
                for rid in missing_roles
                if (role := guild.get_role(rid)) is not None
            ]

            await member.add_roles(*roles_to_add, reason="Level refresh sync")
            added_roles[member.id] = missing_roles
        except Exception as e:
            logger.error(f"failed to add roles to {member}: {e}")

    if roles_to_remove:
        try:
            roles_to_remove_objs = [
                role
                for rid in roles_to_remove
                if (role := guild.get_role(rid)) is not None
            ]

            await member.remove_roles(
                *roles_to_remove_objs, reason="Level refresh sync"
            )
            removed_roles[member.id] = roles_to_remove
        except Exception as e:
            logger.error(f"failed to remove roles from {member}: {e}")


class level(commands.Cog):
    def __init__(self, bot):
        self.bot: Codygen = bot
        self.description = "track and reward users for activity"
        self.db: aiosqlite.Connection = bot.db

    @commands.Cog.listener("on_message")
    async def level_event(self, message):
        try:
            await self.xp(message.author, message.guild, self.db)
        except AttributeError:  # no db loaded yet
            logger.warning("tried to obtain xp before fully initialized")
            pass

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    async def xp(
        self, user: discord.Member, guild: discord.Guild, con: aiosqlite.Connection
    ):
        """
        Main handler for xp gain
        This takes boosts to account, levelup message is sent seperately
        """
        cur: aiosqlite.Cursor = await con.cursor()

        # fetch xp per message
        per_message_res = await cur.execute(
            "SELECT level_per_message FROM guilds WHERE guild_id = ?", (guild.id,)
        )
        per_message_row = await per_message_res.fetchone()

        # fetch current xp of user
        xp_res = await cur.execute(
            "SELECT xp FROM users WHERE guild_id = ? AND user_id = ?",
            (guild.id, user.id),
        )
        xp_row = await xp_res.fetchone()

        base = per_message_row[0] if per_message_row else 0
        xp = xp_row[0] if xp_row else 0
        multiplier_func = await get_boosts(cur, guild, user)
        multiplier = multiplier_func["multiplier"]
        add = int(base * (1 + multiplier / 100))
        # ensure row exists
        await cur.execute(
            "INSERT OR IGNORE INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)",
            (guild.id, user.id, 0),
        )

        # then update counter
        await cur.execute(
            "UPDATE users SET xp = xp + ? WHERE guild_id = ? AND user_id = ?",
            (add, guild.id, user.id),
        )
        new_xp = xp + add
        level = xp_to_level(xp)
        new_level = xp_to_level(new_xp)
        if new_level > level:
            self.bot.dispatch("member_level_up", user, xp, new_xp, guild)
            logger.debug(
                f"{user.id} leveled up from {level} {xp} to {new_level} {new_xp}"
            )
            await reward_xp(user, guild, con, new_xp)
            await send_levelup(
                user, guild, xp, new_xp, multiplier, cur, level, new_level
            )
        await con.commit()

        # logger.debug(f"added {add}xp to {user.id}. this puts them at level {xp_to_level(new_xp)}, with {new_xp}xp.")

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.guild_only()
    @commands.hybrid_group(
        name="level", description="track and reward users for activity"
    )
    async def level(self, ctx: commands.Context):
        pass

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.guild_only()
    @level.group(name="boost", description="manage xp boosts")
    async def boost(self, ctx: commands.Context):
        pass

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @boost.command(name="global", description="set a global boost to this server")
    @app_commands.describe(
        percentage="the percentage (multiplier) of the boost. set to 0 to remove the boost",
        duration="a unix timestamp of the expiry date. leave empty for infinite",
    )
    async def boost_global(
        self, ctx: commands.Context, percentage: int, duration: int = -1
    ):
        con: aiosqlite.Connection = ctx.bot.db
        if not ctx.guild:
            return
        cur: aiosqlite.Cursor = await con.cursor()
        if percentage == 0:
            await cur.execute(
                "DELETE FROM global_boosts WHERE guild_id = ?", (ctx.guild.id,)
            )
            await con.commit()
            await ctx.reply(
                view=Message(
                    "## removed successfully\nall previous global boosts have been removed",
                    accent_color=Color.lgreen,
                )
            )
            return
        if duration < time.time() and duration != -1:
            await ctx.reply(
                view=Message(
                    "## invalid duration.\nplease make sure the expiry date is either a [valid unix timestamp](<https://www.unixtimestamp.com/>) or -1, for infinite duration",
                    accent_color=Color.negative,
                )
            )
            return

        await cur.execute(
            """
            INSERT OR REPLACE INTO global_boosts (guild_id, percentage, expires)
            VALUES (?, ?, ?)
            """,
            (ctx.guild.id, percentage, duration),
        )
        await con.commit()
        await ctx.reply(
            view=Message(
                f"## applied successfully.\na **{percentage}%** global boost has been set\nit will expire {timestamp(duration)}",
                accent_color=Color.lgreen,
            )
        )

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @boost.command(name="role", description="set a boost to a role")
    @app_commands.describe(
        percentage="the percentage (multiplier) of the boost. set to 0 to remove the boost",
        duration="a unix timestamp of the expiry date. leave empty for infinite",
    )
    async def boost_role(
        self,
        ctx: commands.Context,
        role: discord.Role,
        percentage: int,
        duration: int = -1,
    ):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if percentage == 0:
            await cur.execute("DELETE FROM role_boosts WHERE role_id = ?", (role.id,))
            await con.commit()
            await ctx.reply(
                view=Message(
                    "## removed successfully\nall previous boosts for this role have been removed",
                    accent_color=Color.lgreen,
                )
            )
            return
        if duration < time.time() and duration != -1:
            await ctx.reply(
                view=Message(
                    "## invalid duration.\nplease make sure the expiry date is either a [valid unix timestamp](<https://www.unixtimestamp.com/>) or -1, for infinite duration",
                    accent_color=Color.negative,
                )
            )
            return

        await cur.execute(
            """INSERT OR REPLACE INTO role_boosts (role_id, percentage, expires)
            VALUES (?, ?, ?)
            """,
            (role.id, percentage, duration),
        )
        await con.commit()
        await ctx.reply(
            view=Message(
                f"## applied successfully.\n{role.mention} now has a **{percentage}%** boost.\nit will expire {timestamp(duration)}",
                accent_color=Color.lgreen,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @boost.command(name="user", description="set a boost to a user in this server")
    @app_commands.describe(
        percentage="the percentage (multiplier) of the boost. set to 0 to remove the boost",
        duration="a unix timestamp of the expiry date. leave empty for infinite",
    )
    async def boost_user(
        self,
        ctx: commands.Context,
        user: discord.Member,
        percentage: int,
        duration: int = -1,
    ):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if percentage == 0:
            await cur.execute(
                "DELETE FROM user_boosts WHERE user_id = ? AND guild_id = ?",
                (user.id, user.guild.id),
            )
            await con.commit()
            await ctx.reply(
                view=Message(
                    "## removed successfully\nall previous boosts for this user have been removed",
                    accent_color=Color.lgreen,
                )
            )
            return
        if duration < time.time() and duration != -1:
            await ctx.reply(
                view=Message(
                    "## invalid duration.\nplease make sure the expiry date is either a [valid unix timestamp](<https://www.unixtimestamp.com/>) or -1, for infinite duration",
                    accent_color=Color.negative,
                )
            )
            return

        await cur.execute(
            """INSERT OR REPLACE INTO user_boosts (user_id, guild_id, percentage, expires)
            VALUES (?, ?, ?, ?)
            """,
            (user.id, user.guild.id, percentage, duration),
        )
        await con.commit()
        await ctx.reply(
            view=Message(
                f"## applied successfully.\n{user.mention} now has a **{percentage}%** boost.\nit will expire {timestamp(duration)}",
                accent_color=Color.lgreen,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @level.command(name="boosts", description="get your active boosts")
    async def boosts(self, ctx: commands.Context, user: discord.Member | None = None):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if not ctx.guild:
            return
        if not user:
            user = ctx.guild.get_member(ctx.author.id)
            if not user:
                user = await ctx.guild.fetch_member(ctx.author.id)
        boosts = await get_boosts(cur, ctx.guild, user)
        await ctx.reply(
            view=LevelBoostsLayout(boosts),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @level.command(name="get", description="check your current level")
    async def level_get(
        self, ctx: commands.Context, user: discord.Member | None = None
    ):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if not ctx.guild:
            return
        if not user:
            user = ctx.guild.get_member(ctx.author.id)
            if not user:
                user = await ctx.guild.fetch_member(ctx.author.id)
        # data collection

        xp_res = await cur.execute(
            "SELECT xp FROM users WHERE guild_id=? and user_id=?",
            (ctx.guild.id, user.id),
        )
        xp_row = await xp_res.fetchone()

        xp = xp_row[0] if xp_row else 0
        multiplier = await get_boosts(cur, ctx.guild, user)
        level = xp_to_level(xp)
        rank_res = await cur.execute(
            "SELECT COUNT(*) FROM users WHERE guild_id=? AND xp > ?",
            (ctx.guild.id, xp),
        )
        rank_row = await rank_res.fetchone()
        place_in_leaderboard = rank_row[0] if rank_row else 1

        # image
        img = Image.new("RGB", (256, 256), color=(0, 0, 0))
        d = ImageDraw.Draw(img)

        font_bold = ImageFont.truetype("assets/ClashDisplay-Bold.ttf", 96)
        font = ImageFont.truetype("assets/ClashDisplay-Regular.ttf", 24)
        font_light = ImageFont.truetype("assets/ClashDisplay-Medium.ttf", 22)

        avatar_asset = user.display_avatar.replace(size=32)
        buffer = io.BytesIO(await avatar_asset.read())
        avatar = Image.open(buffer).convert("RGBA").resize((32, 32))

        mask = Image.new("L", (32, 32), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, 32, 32), fill=255)

        avatar = ImageOps.fit(avatar, (32, 32))
        avatar.putalpha(mask)

        img.paste(avatar, (16, 16), avatar)
        d.text((56, (16 + 4)), user.name, font=font, fill=(255, 255, 255), anchor="lt")

        d.text(
            (128, 128),
            str(level),
            font=font_bold,
            fill=(255, 255, 255),
            anchor="mm",
        )
        d.text(
            (128, 210),
            f"{xp}xp • #{place_in_leaderboard}",
            font=font_light,
            fill=(255, 255, 255),
            anchor="mm",
        )
        if not os.path.exists("cache"):
            os.makedirs("cache", exist_ok=True)
        img_path = f"cache/{ctx.guild.id}_{ctx.author.id}_level.png"
        img.save(img_path)
        logger.debug(
            f"{user.name} ({user.id}) has {xp}, which puts them at level {level}"
        )
        try:
            await ctx.reply(
                content=(
                    f"-# xp boost: **{multiplier['multiplier']}%**!"
                    if multiplier["multiplier"]
                    else None
                ),
                file=discord.File(img_path),
            )
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @level.command(name="top", description="view the most active members of the server")
    async def leveltop(self, ctx: commands.Context):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if not ctx.guild:
            return
        users_res = await cur.execute(
            "SELECT user_id, xp FROM users WHERE guild_id=? ORDER BY xp DESC",
            (ctx.guild.id,),
        )
        users = await users_res.fetchall()
        img = Image.new("RGB", (1350, 1536), color=(0, 0, 0))
        d = ImageDraw.Draw(img)

        font = ImageFont.truetype("assets/ClashDisplay-Semibold.ttf", 72)
        font_light = ImageFont.truetype("assets/ClashDisplay-Regular.ttf", 66)

        valid_users = []
        count = 0
        for user_id, xp in users:
            user = ctx.guild.get_member(int(user_id))
            if user is not None and count < 10:
                valid_users.append((user_id, xp))
                count += 1

        for i, (user_id, xp) in enumerate(valid_users[:10], start=1):
            user = ctx.guild.get_member(int(user_id))
            if user is None:
                continue
            level = xp_to_level(xp)

            avatar_asset = user.display_avatar.replace(size=128)
            buffer = io.BytesIO(await avatar_asset.read())
            avatar = Image.open(buffer).convert("RGBA").resize((128, 128))
            mask = Image.new("L", (128, 128), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 128, 128), fill=255)
            avatar = ImageOps.fit(avatar, (128, 128))
            avatar.putalpha(mask)
            y_pos = 16 * 3 + (i - 1) * 48 * 3
            img.paste(avatar, (16 * 3, y_pos), avatar)
            bbox = d.textbbox((0, 0), f"{level} • {xp}xp", font=font_light)
            text_height = bbox[3] - bbox[1]
            text_y = y_pos + 128 // 2 - text_height // 2

            d.text(
                (1350 - 16 * 3, text_y),
                f"{level} • {xp}xp",
                font=font_light,
                fill=(255, 255, 255),
                anchor="rt",
            )
            bbox_name = d.textbbox((0, 0), "A", font=font)
            text_height_name = bbox_name[3] - bbox_name[1]
            text_y_name = y_pos + 128 // 2 - text_height_name // 2

            if len(user.name) < 13:
                d.text(
                    (56 * 3 + 20, text_y_name),
                    str(i) + ". " + user.name,
                    font=font,
                    fill=(255, 255, 255),
                    anchor="lt",
                )
            else:
                d.text(
                    (56 * 3 + 20, text_y_name),
                    str(i) + ". " + user.name[:12] + "...",
                    font=font,
                    fill=(255, 255, 255),
                    anchor="lt",
                )

        img_path = f"data/guilds/{ctx.guild.id}_level_top.png"
        img.save(img_path)

        try:
            await ctx.reply(file=discord.File(img_path))

        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @level.command(
        name="set",
        description="set a user's xp. requires administrator permissions. add L to use levels instead",
    )
    async def levelset(
        self, ctx: commands.Context, xp: str, user: discord.Member | None = None
    ):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        if user is None:
            user = ctx.author
        if xp.isdigit():
            xpr = int(xp)
        elif xp.lower().endswith("l"):
            xpr = level_to_xp(int(xp[:-1]))
        else:
            await ctx.reply(view=Message("## invalid level provided."))
            return
        logger.debug(f"attempting to set {user.id}'s xp to {xpr}")
        await cur.execute(
            "INSERT OR REPLACE INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)",
            (ctx.guild.id, user.id, int(xpr)),
        )
        await con.commit()
        await ctx.reply(
            view=Message(
                f"## set {user.mention}'s xp to `{xpr}` (level `{xp_to_level(xpr)}`)."
            ),
            ephemeral=True,
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @level.command(
        name="add",
        description="add xp to a user. Use L at the end to add levels instead.",
    )
    async def leveladd(
        self, ctx: commands.Context, xp: str, user: discord.Member | None = None
    ):
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        if user is None:
            user = ctx.author
        current_xp_res = await cur.execute(
            "SELECT xp FROM users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, user.id),
        )
        current_row = await current_xp_res.fetchone()
        current_xp = current_row[0] if current_row else 0
        if isinstance(xp, str) and xp.endswith("L"):
            levels_to_add = int(xp[:-1])
            xp_to_add = (
                level_to_xp(level_to_xp(current_xp) + levels_to_add) - current_xp
            )
        else:
            xp_to_add = int(xp)

        new_xp = current_xp + xp_to_add

        await cur.execute(
            "INSERT OR REPLACE INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)",
            (ctx.guild.id, user.id, new_xp),
        )
        await con.commit()

        await ctx.reply(
            view=Message(
                f"## added `{xp_to_add}` xp to {user.mention}. (level `{xp_to_level(new_xp)}`)"
            ),
            ephemeral=True,
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @level.command(
        name="refresh",
        description="synchronizes all levels and grants role rewards. admin only",
    )
    async def levelrefresh(self, ctx: commands.Context):
        if not isinstance(ctx.author, discord.Member) or not ctx.guild:
            return
        con: aiosqlite.Connection = ctx.bot.db
        cur: aiosqlite.Cursor = await con.cursor()

        rewards_res = await cur.execute(
            "SELECT level, reward_id FROM level_rewards WHERE guild_id=?",
            (ctx.guild.id,),
        )
        rewards = await rewards_res.fetchall()
        list(rewards).sort(key=lambda x: x[0])

        users_res = await cur.execute(
            "SELECT user_id, xp FROM users WHERE guild_id=?", (ctx.guild.id,)
        )
        users = await users_res.fetchall()
        user_xp_map = {int(user_id): xp for user_id, xp in users}

        added_roles = {}
        removed_roles = {}

        for member in ctx.guild.members:
            if member.bot:
                continue

            xp = user_xp_map.get(member.id, 0)
            user_level = xp_to_level(xp)

            roles_to_add = [
                role_id
                for level_required, role_id in rewards
                if user_level >= level_required
            ]

            current_role_ids = {role.id for role in member.roles}
            missing_roles = [
                role_id for role_id in roles_to_add if role_id not in current_role_ids
            ]

            roles_to_remove = [
                role_id
                for level_required, role_id in rewards
                if user_level < level_required and role_id in current_role_ids
            ]

            if missing_roles:
                try:
                    roles_to_add = [
                        role
                        for rid in missing_roles
                        if (role := ctx.guild.get_role(rid)) is not None
                    ]

                    await member.add_roles(*roles_to_add, reason="Level refresh sync")
                    added_roles[member.id] = missing_roles
                except Exception as e:
                    self.bot.log.error(f"Failed to add roles to {member}: {e}")

            if roles_to_remove:
                try:
                    roles_to_remove_objs = [
                        role
                        for rid in roles_to_remove
                        if (role := ctx.guild.get_role(rid)) is not None
                    ]

                    await member.remove_roles(
                        *roles_to_remove_objs, reason="Level refresh sync"
                    )
                    removed_roles[member.id] = roles_to_remove
                except Exception as e:
                    self.bot.log.error(f"Failed to remove roles from {member}: {e}")

        await ctx.reply(
            view=LevelRefreshSummaryLayout(added_roles, removed_roles),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @level.group(name="rewards", description="level reward settings")
    async def rewards(self, ctx: commands.Context):
        pass

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @level.command(name="setup", description="tweak leveling settings")
    async def setup(
        self,
        ctx: commands.Context,
        levelup_channel: discord.TextChannel | None = None,
        xp_per_message: int | None = None,
    ):
        if not ctx.guild:
            return
        db = self.bot.db
        if levelup_channel is None and xp_per_message is None:
            raise ext.errors.CodygenUserError(
                "levelup channel or level per message is required (hint: use the slash command)\nusage: level setup [levelup_channel] [xp_per_message]\nexample: level setup #levelup 10"
            )

        columns = []
        params = []

        if levelup_channel is not None:
            columns.append("levelup_channel=?")
            params.append(levelup_channel.id)

        if xp_per_message is not None:
            columns.append("level_per_message=?")
            params.append(xp_per_message)

        params.append(ctx.guild.id)

        query = f"UPDATE guilds SET {', '.join(columns)} WHERE guild_id=?"
        await db.execute(query, params)

        await ctx.reply(
            view=Message(
                f"## success\n{f'`channel:` {levelup_channel.mention}' if levelup_channel else ''}\n{f'`xp per message:` `{xp_per_message}`' if xp_per_message else ''}",
                accent_color=Color.positive,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @rewards.command(name="set", description="set a reward role to a level")
    async def rewards_set(self, ctx: commands.Context, level: int, role: discord.Role):
        if not ctx.guild:
            return
        db = self.bot.db
        try:
            await db.execute(
                "INSERT INTO level_rewards (guild_id, level, reward_id) VALUES (?,?,?)",
                (ctx.guild.id, level, role.id),
            )
        except Exception:
            raise ext.errors.CodygenUserError(
                "something went wrong (maybe the role reward already exists for this level?)"
            )
        await ctx.reply(
            view=Message(
                f"## success\nlevel {level} now rewards role {role.mention}",
                accent_color=Color.positive,
            ),
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot):
    await bot.add_cog(level(bot))
