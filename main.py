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
import sys
import aiohttp
import logging
import shutil
import aiosqlite
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, Any
from colorama import Fore
from ext.colors import Color
from ext.logger import logger
from db import connect, create_table
from ext.utils import get_command
from discord.ext import ipcx
from ext.ui_base import Message
from models import Codygen
from typing import cast
from ext.errors import CodygenError

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
) -> str:
    default_prefix = get_global_config().get("default_prefix", ">")
    if not bot or not message or not message.guild:
        return default_prefix
    bot = cast(Codygen, bot)
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


def get_required_env() -> list:
    r = []
    with open(".env.template", "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("#") or not line or line == "\n":
                continue
            r.append(line.split("=")[0])
    return r


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


def ensure_env():
    """
    Checks that all REQUIRED_ENV keys exist and are non-empty.
    (so the user can copy it to .env and fill in real values),
    then exits with a meaningful message.
    """
    missing = []
    for key in REQUIRED_ENV:
        val = os.getenv(key)
        if not val:
            missing.append(key)

    if missing:
        logger.error(
            "Missing environment variables: "
            + ", ".join(missing)
            + "\nA `.env.template` file has been created.\n"
            + "→ Copy it to `.env` and fill in the real values before restarting.\n"
            + "For more details on how to configure the bot, please refer to the official documentation:\n"
            + f"https://github.com/tjf1dev/codygen#self-hosting.{Fore.RESET}"
        )
        sys.exit(1)


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
client.color = Color
client.version = version
client.refresh_commands = refresh_commands
# load env
dotenv.load_dotenv()
TOKEN = cast(str, os.getenv("CLIENT_TOKEN"))
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")


# views
class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        options = []
        self.bot = bot
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                if cog_name.lower() in ["jishaku"]:
                    pass
                else:
                    description = getattr(
                        cog, "description", "no description available."
                    )
                    options.append(
                        discord.SelectOption(
                            label=cog_name.lower(), description=description.lower()
                        )
                    )
        else:
            # add a fallback option if no cogs are loaded
            options.append(
                discord.SelectOption(
                    label="No Modules Loaded", description="Failed to load module list."
                )
            )
        super().__init__(
            placeholder="Select a cog", max_values=1, min_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"codygen - {self.values[0]}", color=Color.white)
        if self.values[0] == "No Modules Loaded":
            fail = discord.Embed(
                title="failed to load the list of modules",
                description="please report this issue.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
            return
        cog = client.get_cog(self.values[0])
        if cog is None:
            fail = discord.Embed(
                title="failed to load :broken_heart:",
                description=f"module {self.values[0]} (cogs.{self.values[0]}) failed to load.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
            return
        elif len(cog.get_commands()) == 0:
            fail = discord.Embed(
                title="its quiet here...",
                description=f"cogs.{self.values[0]} doesnt have any commands.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
        else:
            for command in cog.walk_commands():
                description = (
                    command.description
                    if command.description != ""
                    else "Figure it out yourself (no description provided)"
                )
                embed.add_field(
                    name=command.name, value=f"```{description}```", inline=False
                )
            await interaction.response.edit_message(
                embed=embed, view=HelpHomeView(client)
            )


class HelpWiki(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Documentation",
            style=discord.ButtonStyle.link,
            url="https://github.com/tjf1dev/codygen/wiki",
        )


class HelpHomeView(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(HelpSelect(bot))
        self.add_item(HelpWiki())


class supportReply(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(SupportButton())


class SupportButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Start conversation", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SupportModal())


class SupportModal(discord.ui.Modal, title="Reply to Support Ticket"):
    response = discord.ui.TextInput(label="Response", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        # user_id = interaction.user.id
        if not interaction.message:
            return
        original_user_id = interaction.message.content.splitlines()[0]
        ticket_id = interaction.message.content.splitlines()[1]
        user = await client.fetch_user(int(original_user_id))
        try:
            e = discord.Embed(
                title=f"New reponse for ticket {ticket_id}",
                description=f"```{self.response.value}```",
            )
            await user.send(embed=e)
            e2 = discord.Embed(
                title=f"{ticket_id} - reply sent",
                description=f"```{self.response.value}```",
                color=Color.positive,
            )
            await interaction.response.send_message(embed=e2)
        except discord.errors.Forbidden:
            await interaction.response.send_message(
                "Couldn't send DM to user.", ephemeral=True
            )
        await interaction.response.send_message(
            f"Response sent: {self.response.value}", ephemeral=True
        )


# events
def verify():
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


async def verify_alt(guild_id, interaction) -> bool:
    """
    verify() but instead of a decorator its a function
    """
    prefix_enabled = (await get_guild_config(guild_id))["prefix"]["prefix_enabled"]
    if not prefix_enabled:
        prefix_enabled = False
    if interaction is not None:
        return True
    return prefix_enabled


@client.event
async def on_command(ctx: commands.Context):
    if not ctx.interaction:
        await ctx.typing()
    command = cast(commands.Command, ctx.command)
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
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.MissingPermissions):
        e = discord.Embed(
            title="you don't have permissions to run this command.",
            color=Color.negative,
        )
        await ctx.reply(embed=e, ephemeral=True)
    if isinstance(error, KeyError):
        e = (
            discord.Embed(
                title="this server's configuration has malfunctioned.",
                description="please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen) and the administrators of this server.",
                color=Color.lblue,
            )
            .add_field(name="error", value=f"```{error}```")
            .add_field(
                name="command",
                value=f"```{ctx.command.full_parent_name}```",
                inline=False,
            )
            .add_field(name="version", value=f"```{version}```", inline=True)
        )
        await ctx.send(embed=e, ephemeral=False)  # Handle other errors normally

        raise commands.errors.CommandError(str(error))
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        e = (
            discord.Embed(
                title="an error occurred while trying to run this command",
                description="please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen)",
                color=Color.negative,
            )
            .add_field(name="error", value=f"```{error}```")
            .add_field(name="command", value=f"```{ctx.command.name}```", inline=False)
            .add_field(name="version", value=f"```{version}```", inline=True)
        )
        await ctx.send(embed=e, ephemeral=True)  # Handle other errors normally
        logger.error(
            f"{ctx.author.name} ({ctx.author.id}) has encountered a {type(error).__name__}: {error}"
        )
        raise commands.errors.CommandError(str(error))


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

    @commands.is_owner()
    @admin_group.command(name="sync", description="syncs app commands")
    async def sync(ctx: commands.Context, flags: str = ""):
        # get it flagl because flags and the s is string and l is list hahaha
        flagl = list(flags.strip("-"))
        e = discord.Embed(
            title=f"successfully synced {len(tree.get_commands())} commands for all guilds!",
            color=Color.positive,
        )
        e1 = discord.Embed(
            title=f"successfully synced {len(tree.get_commands())} commands for this guild!",
            color=Color.positive,
        )
        # used for when you want to sync globally but still have the guild first
        e2 = discord.Embed(
            title=f"successfully synced {len(tree.get_commands())} commands for this guild and all guilds!",
            color=Color.positive,
        )
        embed: discord.Embed
        if "g" in flagl:
            embed = e
            await tree.sync()
            logger.info("syncing global")
        elif "g" in flagl and "a" in flagl:
            embed = e2
            await tree.sync(guild=ctx.guild)
            await tree.sync()
            logger.info("syncing guild and global")
        else:
            embed = e1
            await tree.sync(guild=ctx.guild)
            logger.info("syncing guild")
        await ctx.reply(embed=embed, ephemeral=True, mention_author=False)

    start_time = time.time()

    # async def run_quart():
    #     pass
    #     # await app.run_task(host="0.0.0.0", port=4888) #todo allow changing port

    # async def main():
    #     await asyncio.gather(run_quart(), ) and cog_name != "admin"


@tasks.loop(seconds=5.0)
async def heartbeart(self):
    # logger.debug("heartbeat ping")
    return


def main():
    ensure_env()
    client.run(TOKEN)


if __name__ == "__main__":
    logger.info("starting codygen")
    main()
