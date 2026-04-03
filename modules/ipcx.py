import aiosqlite
import functools
import traceback
import sys
import json
import discord
from discord.ext import ipcx  # type: ignore
from ext.cache import TTLCache
import logger
from discord import Permissions
from ext.commands import parse_commands
from discord.abc import GuildChannel
from models import Codygen
from typing import cast
from models import Module

# sometimes i hate looking at my own code
# but i also love it knowing i improved so much


class ChannelSerializer:
    @staticmethod
    def serialize(channel: GuildChannel) -> dict:
        """Serializes a single Discord channel to a dictionary."""
        return {
            "id": str(channel.id),
            "name": channel.name,
            "type": str(channel.type),
            "position": getattr(channel, "position", None),
            "category_id": (
                str(channel.category_id)
                if getattr(channel, "category_id", None)
                else None
            ),
            "parent_id": (str(channel.category.id) if channel.category else None),
            "nsfw": getattr(channel, "nsfw", False),
            "permissions_synced": getattr(channel, "permissions_synced", None),
        }

    @staticmethod
    def serialize_many(channels: list[GuildChannel]) -> list[dict]:
        """Serializes a list of Discord channels."""
        return [ChannelSerializer.serialize(ch) for ch in channels]


def has_permissions_ipc(*, permissions: Permissions):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, data, *args, **kwargs):
            if data is None:
                logger.error("IPC data is None")
                return {"error": 4000, "message": "invalid data"}

            try:
                guild = self.bot.get_guild(data.guild_id)
                if guild is None:
                    logger.warning("Guild not found in cache, fetching...")
                    try:
                        guild = await self.bot.fetch_guild(data.guild_id)
                    except Exception as e:
                        logger.warning(f"Failed fetching guild: {e}")
                        return {"error": 4001, "message": "guild not found"}
                user_guilds = getattr(data, "user_guilds", None)
                if not user_guilds:
                    logger.warning("No user_guilds present on data")
                    return {"error": 4002, "message": "missing user guilds"}

                if not isinstance(user_guilds, (list, tuple)):
                    logger.warning("user_guilds is not a list/tuple")
                    return {"error": 4003, "message": "invalid user guilds format"}

                user_guild_ids = set()
                for g in user_guilds:
                    if not isinstance(g, dict):
                        logger.warning(f"user_guild entry is not a dict: {g}")
                        continue
                    try:
                        user_guild_ids.add(g.get("id"))
                    except Exception:
                        logger.warning(f"Invalid guild id in user_guild: {g}")
                        continue
                if str(guild.id) not in user_guild_ids:
                    logger.warning("User is not a member of the guild")
                    return {
                        "error": 4004,
                        "message": "user not a member of the guild",
                    }

                user_guild = next(
                    (g for g in user_guilds if int(g.get("id", 0)) == guild.id),
                    None,
                )
                if user_guild is None:
                    logger.warning("User guild info not found")
                    return {"error": 4005, "message": "user guild info missing"}

                user_perms_int_str = user_guild.get("permissions")
                if user_perms_int_str is None:
                    logger.warning("Permissions missing from user guild info")
                    return {"error": 4006, "message": "permissions missing"}

                try:
                    user_perms_int = int(user_perms_int_str)
                except Exception:
                    logger.warning(f"Invalid permissions format: {user_perms_int_str}")
                    return {"error": 4007, "message": "invalid permissions format"}

                user_perms = Permissions(user_perms_int)
                if not user_perms >= permissions:
                    logger.warning(
                        f"User lacks permissions: needed {permissions}, got {user_perms}"
                    )
                    return {
                        "error": 4008,
                        "message": f"missing permissions: user={user_perms}, required={permissions}",
                    }

                return await func(
                    self,
                    data,
                    guild=guild,
                    guild_id=guild.id,
                    user_guild=user_guild,
                    *args,
                    **kwargs,
                )

            except Exception as e:
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                logger.error(f"Exception in permission check:\n{tb}")
                print(f"Exception in permission check:\n{tb}", file=sys.stderr)
                return {"error": 5000, "message": "internal server error"}

        return wrapper

    return decorator


FORBIDDEN_KEYS = {"config_ver", "timestamp"}

guild_cache = TTLCache(ttl_seconds=300)
state_cache = TTLCache(ttl_seconds=300)


def prepare_guild(data: dict) -> dict:
    try:
        config = data.get("config", {})

        try:
            config["module_settings"] = json.loads(config.get("module_settings", "{}"))
        except (TypeError, json.JSONDecodeError):
            config["module_settings"] = {}

        try:
            config["logging_settings"] = json.loads(
                config.get("logging_settings", "{}")
            )
        except (TypeError, json.JSONDecodeError):
            config["logging_settings"] = {}

        config["prefix_enabled"] = bool(config.get("prefix_enabled"))

        data["config"] = config
        return data

    except Exception:
        data.setdefault("config", {})
        config = data["config"]
        config.setdefault("module_settings", {})
        config.setdefault("logging_settings", {})
        config.setdefault("prefix_enabled", False)
        return data


class ipcx_api(Module):
    def __init__(self, bot, **kwargs):
        super().__init__(hidden=True, default=True, **kwargs)
        self.bot = cast(Codygen, bot)
        self.description = "internal api for dashboard and web server"
        self.db: aiosqlite.Connection = bot.db
        self.allowed_contexts = discord.app_commands.allowed_contexts(
            True, False, False
        )

    def get_module_names(self):
        return [
            name
            for name, cog in self.bot.cogs.items()
            if getattr(cog, "hidden") is False
        ]

    @ipcx.route()
    async def add_bot(self, data):
        return f"https://discord.com/oauth2/authorize?client_id={cast(discord.User, self.bot.user).id}"

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @ipcx.route()
    async def modules(self, data):
        try:
            cached = state_cache.get("modules")
            if cached:
                return cached

            resp = self.get_module_names()

            state_cache.set("modules", resp)
            return resp

        except Exception as e:
            logger.error(e, exc_info=True)
            return {"error": "something went wrong", "code": ""}

    @ipcx.route()
    @has_permissions_ipc(permissions=Permissions(administrator=True))
    async def get_guild(
        self, data, guild_id: int, guild: discord.Guild | None = None, user_guild=None
    ):
        try:
            cached = guild_cache.get(data.guild_id)
            if cached:
                return cached
            if not guild:
                guild = self.bot.get_guild(data.guild_id) or await self.bot.fetch_guild(
                    data.guild_id
                )
            if guild is None:
                return {"error": "guild not found", "code": "GUILD_NOT_FOUND"}

            cur: aiosqlite.Cursor = await self.db.cursor()
            row = await (
                await cur.execute(
                    "SELECT prefix, prefix_enabled, level_per_message, levelup_channel, config_ver, timestamp FROM guilds WHERE guild_id=?",
                    (data.guild_id,),
                )
            ).fetchone()
            module_row = await (
                await cur.execute(
                    "SELECT * FROM modules WHERE guild_id=?", (data.guild_id,)
                )
            ).fetchone()
            bot_modules = self.get_module_names()

            if row is None or module_row is None:
                return {"error": "guild not initialized", "code": "GUILD_UNINITIALIZED"}
            module_row = dict(module_row)

            result = {
                "name": guild.name,
                "id": str(guild.id),
                "member_count": guild.member_count,
                "icon_url": guild.icon.url if guild.icon else None,
                "config": dict(row),
                "modules": {m: module_row.get(m, True) for m in bot_modules},
            }

            guild_cache.set(data.guild_id, result)
            return result

        except Exception as e:
            logger.error(f"{type(e).__name__}: {e} in get_guild")
            return {"error": "internal server error"}

    @ipcx.route()
    @has_permissions_ipc(permissions=Permissions(administrator=True))
    async def put_guild(
        self, data, guild_id: int, guild: discord.Guild | None = None, user_guild=None
    ):
        guild_id = data.guild_id
        updates = data.data

        if not guild_id:
            return {"error": 1000, "message": "no guild"}

        UPDATE_BLACKLIST = {
            "guild_id",
            "config_ver",
            "timestamp",
            "logging_settings",
            "module_settings",
        }

        if any(key in UPDATE_BLACKLIST for key in updates):
            return {
                "error": "can't modify those keys",
                "code": "CHANGED_UNMODIFIABLE_KEY",
            }

        allowed_updates = {
            k: v for k, v in updates.items() if k not in UPDATE_BLACKLIST
        }
        if not allowed_updates:
            return {"error": "no valid columns to update"}

        columns = list(allowed_updates.keys())
        values = list(allowed_updates.values())
        set_clause = ", ".join(f"{col}=?" for col in columns)
        query = f"UPDATE guilds SET {set_clause} WHERE guild_id=?"
        params = values + [guild_id]

        try:
            cur: aiosqlite.Cursor = await self.db.cursor()
            await cur.execute(query, params)
            await self.db.commit()

            self.db.row_factory = aiosqlite.Row
            row = await (
                await cur.execute("SELECT * FROM guilds WHERE guild_id=?", (guild_id,))
            ).fetchone()
            if not row:
                return {"error": "guild not found after update"}

            return prepare_guild(dict(row))

        except Exception as e:
            logger.error(f"put_guild failed: {type(e).__name__}: {e}")
            return {"error": "internal server error"}

    @ipcx.route()
    async def list_guilds(self, data):
        cached = state_cache.get("guilds")
        if cached:
            return cached
        guilds = self.bot.guilds
        if not guilds:
            logger.debug("fetching guilds")
            guilds = [guild async for guild in self.bot.fetch_guilds()]
        data = [
            {
                "id": g.id,
                "name": g.name,
                "approximate_member_count": g.approximate_member_count,
                "icon": g.icon.url if g.icon else None,
                "owner_id": g.owner_id,
            }
            for g in guilds
        ]
        state_cache.set("guilds", data)
        return data

    @ipcx.route()
    async def stats(self, data):
        return {
            "users": len(self.bot.users),
            "guilds": len(self.bot.guilds),
            "commands": len(parse_commands(self.bot.full_commands)),
        }

    @ipcx.route()
    async def commands(self, data):
        cached = state_cache.get("commands")
        if cached:
            return cached
        data = parse_commands(self.bot.full_commands, self.bot)
        state_cache.set("commands", data)
        return data


async def setup(bot: Codygen):
    await bot.add_cog(ipcx_api(bot))
