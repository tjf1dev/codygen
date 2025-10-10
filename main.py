#!/usr/bin/env python3

# codygen - a bot that tries to do everything
#
# tjf1: https://github.com/tjf1dev
#
# feel free to read this terrible code
import discord
import os
import aiofiles
import dotenv
import json
import time
import asyncio
import base64
import aiohttp
import logging
import shutil
import ext.errors
import datetime
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, Any
from colorama import Fore
from ext.colors import Color
from ext.logger import logger
from db import connect, create_table
from ext.utils import get_command, parse_flags, get_required_env, ensure_env
from discord.ext import ipcx
from ext.ui_base import Message
from models import Codygen
from typing import cast
from ext.errors import CodygenError
from traceback import format_exception
from extensions.cache_commands import cache_commands
# from ext.web import app

DEFAULT_GLOBAL_CONFIG = open("config.json.template").read()


def get_global_config() -> dict:
    """
    Loads config.json, or if it doesn't exist / is invalid JSON,
    writes out DEFAULT_GLOBAL_CONFIG and returns it.
    """
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("config.json", "w") as f:
            json.dump(DEFAULT_GLOBAL_CONFIG, f, indent=4)
        return DEFAULT_GLOBAL_CONFIG  # type: ignore


# pre-init functions
def get_config_defaults() -> dict:
    with open("config.json", "r") as f:
        return json.load(f)["template"]["guild"]


async def get_guild_config(guild_id: str | int) -> dict:
    try:
        async with aiofiles.open(f"data/guilds/{guild_id}.json", "r") as f:
            return json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


async def make_guild_config(guild_id: str | int, config: dict) -> None:
    os.makedirs("data/guilds", exist_ok=True)
    async with aiofiles.open(f"data/guilds/{guild_id}.json", "w") as f:
        await f.write(json.dumps(config, indent=4))


# example
# await set_guild_config_key(1234567890123456, "settings.prefix", "!")
async def set_guild_config_key(guild_id: str | int, key: str, value) -> bool:
    try:
        async with aiofiles.open(f"data/guilds/{guild_id}.json", "r") as f:
            config = json.loads(await f.read())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(
            f"{guild_id}'s config has encountered an error: {type(e).__name__}: {e}"
        )
        return False
        # config = get_config_defaults()

    keys = key.split(".")
    d = config
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value

    os.makedirs("data/guilds", exist_ok=True)
    async with aiofiles.open(f"data/guilds/{guild_id}.json", "w") as f:
        await f.write(json.dumps(config, indent=4))
    return True


def state_to_id(state: str) -> str:
    euid = state.split("@")[0]
    return base64.b64decode(euid).decode()


async def get_prefix(
    bot: Codygen | commands.Bot | commands.AutoShardedBot | None = None,
    message: discord.Message | None = None,
) -> str | None:
    default_prefix = get_global_config().get("default_prefix", ">")
    if not bot or not message or not message.guild:
        return default_prefix
    bot = cast(Codygen, bot)
    if not hasattr(bot, "db"):
        logger.warning("tried to get prefix before fully initialized")
        return default_prefix
    con: aiosqlite.Connection = bot.db

    cur: aiosqlite.Cursor = await con.cursor()
    try:
        res = await cur.execute(
            "SELECT prefix FROM guilds WHERE guild_id=?", (message.guild.id,)
        )
        prefix_row = await res.fetchone() or [default_prefix]
        prefix = prefix_row[0]
        if message is None or prefix is None:
            return default_prefix
        return prefix
    except Exception:
        return default_prefix


async def cleanup_cache():
    pass


async def custom_api_request(
    bot: commands.Bot,
    endpoint: str,
    method: str = "get",
    auth: bool = True,
):
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {}

    if auth:
        headers = {"Authorization": f"Bot {TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers) as response:
            return [response, await response.json()]


async def request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> aiohttp.ClientResponse:
    if headers is None:
        headers = {}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, **kwargs) as response:
            return response


async def request_with_json(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict[str, str]] = None,
    **kwargs: Any,
) -> aiohttp.ClientResponse:
    if headers is None:
        headers = {}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, **kwargs) as response:
            return await response.json()


REQUIRED_ENV = get_required_env()


#! database stuff
async def database() -> aiosqlite.Connection:
    """
    Opens a connection to the database, and saves it onto the client
    Checks if the database is present, and if it isnt, creates the database with tables.
    """
    shutil.copyfile("codygen.db", "codygen.db.backup")
    logger.info("loading database")
    con = await connect()
    await con.execute("PRAGMA journal_mode=WAL;")

    client.db = con

    async with con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cursor:
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
    if not table_names:
        logger.warning(
            "seems like its your first time starting codygen! creating database file..."
        )
        logger.warning(
            "if you want to convert your existing json data into a database, run db.py"
        )
        await con.close()
        await create_table()
        con = await connect()
    for name in table_names:
        logger.debug(f"loaded table {name}")
    return con


# load configs
try:
    with open("config.json", "r") as f:
        data = json.load(f)
except Exception:
    logger.error("could not find config, generating new configuration")
    pass
# command configs
data = get_global_config()
version = open("VERSION").read()
if not version:
    logger.error("something went wrong cant load version")
# bot definitions
intents = discord.Intents.all()


client = Codygen(
    command_prefix=get_prefix,
    intents=intents,
    status=discord.Status.idle,
    help_command=None,
    allowed_contexts=app_commands.AppCommandContext(
        guild=True, dm_channel=True, private_channel=True
    ),
    allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
)
tree = client.tree
dotenv.load_dotenv()

client.ipc = ipcx.Server(
    cast(commands.Bot, client),
    secret_key=os.getenv("IPC_KEY"),
    port=20001,
    multicast_port=20002,
)
client.log = logging.getLogger("discord.ext.ipcx")


async def refresh_commands() -> list[dict]:
    if not client.user:
        raise CodygenError("user doesnt exist")
    uid = cast(int, client.user.id)
    client.full_commands = await get_command(TOKEN, uid, name="*")
    if not isinstance(client.full_commands, list):
        raise CodygenError("commands didn't load")
    return client.full_commands


async def on_ipc_ready(self):
    logger.info("started dashboard (ipc)")


async def on_ipc_error(self, endpoint, error):
    logger.error("error in %s: %s", endpoint, error)


# client custom vars
# these get passed to cogs
flor = Color
client.version = version
client.refresh_commands = refresh_commands
# load env
dotenv.load_dotenv()
TOKEN = cast(str, os.getenv("CLIENT_TOKEN"))
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")


# events
def verify_dec():
    """
    Checks for certain things that could prevent a command from sending
    """

    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return True
        cur: aiosqlite.Cursor = await ctx.bot.db.cursor()
        row = await (
            await cur.execute(
                "SELECT prefix_enabled FROM guilds WHERE guild_id=?", (ctx.guild.id,)
            )
        ).fetchone()

        prefix_enabled = bool(row[0]) if row else False

        if prefix_enabled is None:
            prefix_enabled = False

        if ctx.interaction is not None:
            return True

        return prefix_enabled

    return commands.check(predicate)


def recursive_update(existing_config, template_config):
    def merge(d1, d2):
        result = d1.copy()
        for key, value in d2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = merge(result[key], value)
            else:
                result.setdefault(key, value)
        return result

    return merge(existing_config, template_config)


async def verify(ctx) -> bool:
    if ctx.guild is None:
        return True
    cur: aiosqlite.Cursor = await ctx.bot.db.cursor()
    row = await (
        await cur.execute(
            "SELECT prefix_enabled FROM guilds WHERE guild_id=?", (ctx.guild.id,)
        )
    ).fetchone()

    prefix_enabled = bool(row[0]) if row else False

    if prefix_enabled is None:
        prefix_enabled = False

    if ctx.interaction is not None:
        return True

    return prefix_enabled


@client.event
async def on_command(ctx: commands.Context):
    if not ctx.interaction:
        async with ctx.typing():
            await asyncio.sleep(2.5)
    command = cast(commands.Command, ctx.command)
    if not await verify(ctx):
        return False
    logger.info(
        f"{command.qualified_name} has been used by {ctx.author.global_name} ({ctx.author.id})!"
    )


@client.check
async def is_module_enabled(ctx: commands.Context):
    if ctx.guild is None:
        logger.debug("allowing command: case 1")
        return True
    if ctx.cog:
        if ctx.cog.qualified_name.lower() == "jishaku":
            logger.debug("allowing command: case 2")
            return True

    if not ctx.cog:
        logger.debug("allowing command: case 3")
        return True
    if (
        ctx.command
        and ctx.command.name == "init"
        and ctx.cog.qualified_name == "settings"
    ):
        return True
    if getattr(ctx.cog, "hidden", False):
        return True
    con: aiosqlite.Connection = ctx.bot.db
    cur: aiosqlite.Cursor = await con.cursor()
    logger.debug(f"cog: {ctx.cog.qualified_name}")
    res = await cur.execute(
        f"SELECT {ctx.cog.qualified_name.lower()} FROM modules WHERE guild_id=?",
        (ctx.guild.id,),
    )
    row = await res.fetchone()
    is_enabled = bool(row[0]) if row else False

    if not is_enabled:
        await ctx.reply(
            view=Message(
                "## this command comes from a disabled module.",
                accent_color=Color.negative,
            ),
            ephemeral=True,
        )
        return False
    return True


@client.event
async def on_command_error(ctx: commands.Context, error):
    if not ctx.command:
        return
    error = error.original if isinstance(error, commands.CommandInvokeError) else error
    logger.error(
        f"{ctx.author.name} ({ctx.author.id}) has encountered a {type(error).__name__} while running {ctx.command.qualified_name}: {error}"
    )
    tb = "".join(format_exception(type(error), error, error.__traceback__))
    logger.error(tb)
    if isinstance(
        error,
        commands.MissingPermissions
        | app_commands.MissingPermissions
        | commands.NotOwner,
    ):
        e = Message(
            message="### you don't have permissions to run this command.",
            accent_color=Color.negative,
        )
        await ctx.reply(view=e, ephemeral=True)
    if isinstance(error, commands.CheckFailure | commands.errors.CheckFailure):
        return
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, ext.errors.CodygenUserError):
        e = Message(
            message=f"### error\n{error}\n",
            accent_color=Color.negative,
        )
        await ctx.send(view=e, ephemeral=True)
    else:
        header = "an unexpected error occured."
        if isinstance(
            error,
            ext.errors.MissingEnvironmentVariable | ext.errors.MisconfigurationError,
        ):
            header = "this server's configuration has malfunctioned."

        e = Message(
            message=f"## {header}\n"
            "please report this to the administrators of this server, and the [developers of this bot.](https://github.com/tjf1dev/codygen/issues).\n"
            f"### error\n```\n{type(error).__name__}: {error}```\n"
            f"### command\n```\n{ctx.command.qualified_name}```\n"
            f"### version\n```\n{version}```",
            accent_color=Color.negative,
        )
        await ctx.send(view=e, ephemeral=True)

        # optional: raise error (doesn't really fit here since this is the handler)
        # raise commands.errors.CommandError(str(error))


loaded_cogs = set()


client.start_time = time.time()


@client.event
async def on_ready():
    client.db = await database()
    await client.ipc.start()
    user = cast(discord.User, client.user)

    logger.debug("starting dashboard (ipc)")
    client.full_commands = await get_command(TOKEN, user.id, name="*")
    global start_time
    if getattr(client, "already_ready", False):
        return
    client.already_ready = True

    client.start_time = time.time()
    await refresh_commands()
    start_time = time.time()
    logger.info("loading modules..")
    await client.load_extension("jishaku")  # jsk #* pip install jishaku
    config = get_global_config()
    blacklist = config["cogs"]["blacklist"]
    for filename in os.listdir("modules"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            if cog_name in loaded_cogs:
                logger.warning(f"skipping duplicate load of {cog_name}")
                continue
            elif cog_name in blacklist:
                logger.warning(f"skipping blacklisted module {cog_name}")
                continue
            loaded_cogs.add(cog_name)
            try:
                logger.debug(f"loading {cog_name}")
                await client.load_extension(f"modules.{cog_name}")
            except asyncio.TimeoutError:
                logger.error(f"timeout while loading {cog_name}")

    logger.info(f"bot started as {Fore.LIGHTMAGENTA_EX}{user.name}{Fore.RESET}")
    admin_cog = client.get_cog("admin")
    if not admin_cog:
        return

    admin_group = admin_cog.admin  # type:ignore
    if not cache_commands_task.is_running():
        cache_commands_task.start()

    @commands.is_owner()
    @admin_group.command(name="sync", description="syncs app commands")
    async def sync(ctx: commands.Context, flags: str | Any = ""):
        flags = parse_flags(flags)
        suffix = ""
        local_sync = flags.get("l") or flags.get("L")
        global_sync = flags.get("G") or flags.get("g")
        forced = flags.get("f")

        logger.debug(
            f"attempting sync; local: {local_sync}; global: {global_sync}; forced: {forced}"
        )
        if (not local_sync and not global_sync) or not flags:
            e = Message(
                message="## usage \nflags:\n- -l: sync locally\n- -G: sync globally (for all servers)\n- -f: force (allow global sync)",
                accent_color=Color.negative,
            )
            await ctx.reply(view=e, ephemeral=True, mention_author=False)

            return
        if global_sync and not forced:
            e = Message(
                message="## failed \ncannot sync globally without the `-f` flag",
                accent_color=Color.negative,
            )
            await ctx.reply(view=e, ephemeral=True, mention_author=False)
            return
        if local_sync:
            await tree.sync(guild=ctx.guild)
            suffix += "this"
        if not global_sync:
            suffix += " server"
        if global_sync:
            if local_sync:
                suffix += " and"
            suffix += " all servers"
            await tree.sync()
            await cache_commands(client)

        e = Message(
            message=f"# success\n{len(client.full_commands)} commands synced for `{suffix}`.",
            accent_color=Color.positive,
        )
        await ctx.reply(view=e, ephemeral=True, mention_author=False)


@tasks.loop(seconds=15.0)
async def cache_commands_task():
    try:
        async with aiofiles.open(".last_command_cache", "r") as f:
            content = await f.read()
        last_cache = json.loads(content).get("time")
        if not last_cache:
            raise ValueError("no cache found")
        if datetime.datetime.fromtimestamp(
            last_cache
        ) < datetime.datetime.now() - datetime.timedelta(days=1):
            logger.debug("caching commands - last cache was over a day ago")
            await cache_commands(client)
    except Exception:
        last_cache = int(time.time())
        logger.debug("caching commands - no cache file found")
        await cache_commands(client)


def main():
    ensure_env()
    client.run(TOKEN)


if __name__ == "__main__":
    logger.info("starting codygen")
    main()
