import aiosqlite
import functools
import os
import traceback
import sys
import discord
from discord.ext import commands, ipcx
from ext.logger import logger
from discord import Permissions
from dataclasses import dataclass
from ext.utils import parse_commands
from discord.abc import GuildChannel
from models import Codygen
from typing import cast, Any


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


@dataclass
class ModuleConfig:
    admin: bool
    applications: bool
    codygen: bool
    dashboard: bool
    fm: bool
    fun: bool
    info: bool
    level: bool
    moderation: bool
    settings: bool
    utility: bool

    @classmethod
    def from_db_row(cls, row: tuple) -> "ModuleConfig":
        return cls(
            admin=bool(row[1]),
            applications=bool(row[2]),
            codygen=bool(row[3]),
            dashboard=bool(row[4]),
            fm=bool(row[5]),
            fun=bool(row[6]),
            info=bool(row[7]),
            level=bool(row[8]),
            moderation=bool(row[9]),
            settings=bool(row[10]),
            utility=bool(row[11]),
        )

    def to_dict(self):
        return self.__dict__


@dataclass
class ConfigModel:
    prefix: str
    prefix_enabled: bool
    level_per_message: int
    levelup_channel: str | None
    config_ver: int
    modules: ModuleConfig

    @classmethod
    def from_db_rows(
        cls, guild_row: tuple | Any, module_row: tuple | Any | None
    ) -> "ConfigModel":
        if module_row is None:
            # set all modules to False by default
            module_config = ModuleConfig(
                admin=False,
                applications=False,
                codygen=False,
                dashboard=False,
                fm=False,
                fun=False,
                info=False,
                level=False,
                moderation=False,
                settings=False,
                utility=False,
            )
        else:
            module_config = ModuleConfig.from_db_row(module_row)

        return cls(
            prefix=guild_row[1],
            prefix_enabled=bool(guild_row[2]),
            level_per_message=guild_row[3],
            levelup_channel=str(guild_row[4]),
            config_ver=guild_row[5],
            modules=module_config,
        )

    def to_dict(self):
        return {
            "prefix": self.prefix,
            "prefix_enabled": self.prefix_enabled,
            "level_per_message": self.level_per_message,
            "levelup_channel": self.levelup_channel,
            "config_ver": self.config_ver,
            "modules": self.modules.to_dict(),
        }


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

                if int(guild.id) not in user_guild_ids:
                    logger.warning("User is not a member of the guild")
                    return {"error": 4004, "message": "user not a member of the guild"}

                user_guild = next(
                    (g for g in user_guilds if int(g.get("id", 0)) == guild.id), None
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
                    self, data, guild=guild, user_guild=user_guild, *args, **kwargs
                )

            except Exception as e:
                tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
                logger.error(f"Exception in permission check:\n{tb}")
                print(f"Exception in permission check:\n{tb}", file=sys.stderr)
                return {"error": 5000, "message": "internal server error"}

        return wrapper

    return decorator


FORBIDDEN_KEYS = {"config_ver", "timestamp"}


class dashboard(commands.Cog):
    def __init__(self, bot: Codygen):
        self.bot = bot
        self.db: aiosqlite.Connection = bot.db
        self.allowed_contexts = discord.app_commands.allowed_contexts(
            True, False, False
        )

    @ipcx.route()
    async def add_bot(self, data):
        return f"https://discord.com/oauth2/authorize?client_id={cast(discord.User, self.bot.user).id}"

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @ipcx.route()
    @has_permissions_ipc(permissions=Permissions(administrator=True))
    async def get_guild(self, data, guild=None, user_guild=None):
        cur: aiosqlite.Cursor = await self.db.cursor()
        guild = self.bot.get_guild(data.guild_id)
        if not guild:
            guild = await self.bot.fetch_guild(data.guild_id)
        res = await cur.execute(
            "SELECT * FROM guilds WHERE guild_id=?", (data.guild_id,)
        )
        row = await res.fetchone()
        module_row = await (
            await cur.execute(
                "SELECT * FROM modules WHERE guild_id=?", (data.guild_id,)
            )
        ).fetchone()
        if row is None:
            logger.warning(f"No row in db for {data.guild_id}")
            return None
        config = ConfigModel.from_db_rows(row, module_row)
        return {
            "name": guild.name,
            "id": str(guild.id),
            "member_count": guild.member_count,
            "icon_url": guild.icon.url if guild.icon else None,
            "config": config.to_dict(),
        }

    # @ipcx.route()
    # @has_permissions_ipc(permissions=Permissions())
    # async def get_channel(self, data, guild=None, user_guild=None):
    #     channel_id = data.channel

    #     return {
    #         "name": guild.name,
    #         "id": guild.id,
    #         "member_count": guild.member_count,
    #         "icon_url": guild.icon.url if guild.icon else None,
    #         "config": config.to_dict(),
    #     }

    @ipcx.route()
    @has_permissions_ipc(permissions=Permissions())
    async def get_channels(self, data, guild=None, user_guild=None):
        guild = self.bot.get_guild(data.guild_id)
        if not data.guild_id:
            return {"error": 1000, "message": "no guild"}
        if not guild:
            return []
        channels = ChannelSerializer.serialize_many(list(guild.channels))
        channels.sort(key=lambda ch: ch["position"] or 0)
        return channels

    @ipcx.route()
    @has_permissions_ipc(permissions=Permissions(administrator=True))
    async def put_guild(self, data, guild=None, user_guild=None):
        guild_id = data.guild_id
        updates = data.data

        if not guild_id:
            return {"error": 1000, "message": "no guild"}
        MODULES_COLUMNS = [
            fname[:-3]
            for fname in os.listdir("modules")
            if fname.endswith(".py") and not fname.startswith("__")
        ]
        MODULES_COLUMNS.append("modules")
        # Separate updates for each table
        guilds_updates = {
            k: v
            for k, v in updates.items()
            if k not in FORBIDDEN_KEYS and k not in MODULES_COLUMNS
        }
        modules_updates = updates.get("modules", {})

        con = self.db
        cur = await con.cursor()

        # Update guilds table
        if guilds_updates:
            columns = list(guilds_updates.keys())
            values = list(guilds_updates.values())
            set_clause = ", ".join(f"{col}=?" for col in columns)
            query = f"UPDATE guilds SET {set_clause} WHERE guild_id=?"
            params = values + [guild_id]
            await cur.execute(query, params)

        # Update modules table
        if modules_updates:
            mod_cols = [k for k in modules_updates.keys() if k in MODULES_COLUMNS]
            if mod_cols:
                mod_values = [modules_updates[k] for k in mod_cols]
                mod_set_clause = ", ".join(f"{col}=?" for col in mod_cols)
                mod_query = f"UPDATE modules SET {mod_set_clause} WHERE guild_id=?"
                mod_params = mod_values + [guild_id]
                await cur.execute(mod_query, mod_params)

        await con.commit()

        # Fetch updated rows
        row = await (
            await con.execute("SELECT * FROM guilds WHERE guild_id=?", (guild_id,))
        ).fetchone()
        module_row = await (
            await con.execute("SELECT * FROM modules WHERE guild_id=?", (guild_id,))
        ).fetchone()

        if row is None:
            return None

        config = ConfigModel.from_db_rows(row, module_row)
        return config.to_dict()

    @ipcx.route()
    async def shared_guilds(self, data):
        try:
            user_guild_ids = set(data.user)
            shared = [
                {
                    "name": g.name,
                    "id": str(g.id),
                    "icon": g.icon.url if g.icon else None,
                    "created_at": round(g.created_at.timestamp()),
                }
                for g in self.bot.guilds
                if g.id in user_guild_ids
            ]
            return shared
        except Exception as e:
            logger.error(f"{type(e).__name__}: {e}")

    @ipcx.route()
    async def stats(self, data):
        return {
            "users": len(self.bot.users),
            "guilds": len(self.bot.guilds),
            "commands": len(parse_commands(self.bot.full_commands)),
        }

    @ipcx.route()
    async def commands(self, data):
        return parse_commands(self.bot.full_commands, self.bot)


async def setup(bot: Codygen):
    await bot.add_cog(dashboard(bot))
