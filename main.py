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
from typing import AsyncGenerator, Optional, Dict, Any
from colorama import Fore
from ext.colors import Color
from ext.logger import logger
from db import connect, create_table
from ext.utils import get_command
from discord.ext import ipcx
from ext.ui_base import Message

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
        return DEFAULT_GLOBAL_CONFIG


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
            f"{guild_id}'s config has encountered an error: {type(e).__name__}: {e}")
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


async def get_prefix(bot: commands.Bot = None, message: discord.Message = None) -> str:
    default_prefix = get_global_config().get("default_prefix", ">")
    con: aiosqlite.Connection = bot.db
    cur: aiosqlite.Cursor = await con.cursor()
    try:
        res = await cur.execute("SELECT prefix FROM guilds WHERE guild_id=?",
                                (message.guild.id,))
        prefix_row = await res.fetchone()
        prefix = prefix_row[0]
        if message is None or prefix is None:
            return commands.when_mentioned_or(default_prefix)
        return prefix
    except Exception:
        return default_prefix


async def cleanup_cache():
    pass


async def custom_api_request(
    bot: commands.Bot,
    endpoint: str,
    method: str = aiohttp.ClientSession.get,
    auth: bool = True,
):
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {}

    if auth:
        headers = {"Authorization": f"Bot {TOKEN}"}

    async with aiohttp.ClientSession() as session:
        async with session.request(method.__name__, url, headers=headers) as response:
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
    async with con.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
    if not table_names:
        logger.warning(
            "seems like its your first time starting codygen! creating database file...")
        logger.warning(
            "if you want to convert your existing json data into a database, run db.py")
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
            "Missing environment variables: " + ", ".join(missing) +
            "\nA `.env.template` file has been created.\n" +
            "→ Copy it to `.env` and fill in the real values before restarting.\n" +
            "For more details on how to configure the bot, please refer to the official documentation:\n"
            + f"https://github.com/tjf1dev/codygen#self-hosting.{Fore.RESET}")
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
version = data["version"]
# bot definitions
intents = discord.Intents.all()

client = commands.AutoShardedBot(
    command_prefix=get_prefix,
    intents=intents,
    status=discord.Status.idle,
    help_command=None,
    allowed_contexts=app_commands.AppCommandContext(guild=True,
                                                    dm_channel=True,
                                                    private_channel=True),
    allowed_installs=app_commands.AppInstallationType(guild=True, user=True),
    shard_ids=[0, 1, 2, 3, 4],
    shard_count=5,
    shard_connect_timeout=60)
tree = client.tree
dotenv.load_dotenv()
client.ipc = ipcx.Server(client,
                         secret_key=os.getenv("IPC_KEY"),
                         port=20001,
                         multicast_port=20002)
client.log = logging.getLogger("discord.ext.ipcx")


async def refresh_commands() -> dict:
    client.full_commands = await get_command(TOKEN, client.user.id, name="*")
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
TOKEN = os.getenv("CLIENT_TOKEN")  # bot token
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")


# views
class HelpSelect(discord.ui.Select):

    def __init__(self, bot):
        options = []
        bot = self.bot
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                if cog_name.lower() in ["jishaku"]:
                    pass
                else:
                    description = getattr(cog, "description", "no description available.")
                    options.append(
                        discord.SelectOption(label=cog_name.lower(),
                                             description=description.lower()))
        else:
            # add a fallback option if no cogs are loaded
            options.append(
                discord.SelectOption(label="No Modules Loaded",
                                     description="Failed to load module list."))
        super().__init__(placeholder="Select a cog",
                         max_values=1,
                         min_values=1,
                         options=options)

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
                description=
                f"module {self.values[0]} (cogs.{self.values[0]}) failed to load.",
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
                description = (command.description if command.description != "" else
                               "Figure it out yourself (no description provided)")
                embed.add_field(name=command.name,
                                value=f"```{description}```",
                                inline=False)
            await interaction.response.edit_message(embed=embed,
                                                    view=HelpHomeView(client))


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
            await interaction.response.send_message("Couldn't send DM to user.",
                                                    ephemeral=True)
        await interaction.response.send_message(f"Response sent: {self.response.value}",
                                                ephemeral=True)


# events
def verify():
    """
    Checks for certain things that could prevent a command from sending
    """

    async def predicate(ctx: commands.Context):
        if ctx.guild is None:
            return True
        cur: aiosqlite.Cursor = await ctx.bot.db.cursor()
        prefix_enabled_res = await cur.execute(
            "SELECT prefix_enabled FROM guilds WHERE guild_id=?", (ctx.guild.id,))
        prefix_enabled_row = await prefix_enabled_res.fetchone()
        prefix_enabled = prefix_enabled_row[0]

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
            if (key in result and isinstance(result[key], dict) and
                    isinstance(value, dict)):
                result[key] = merge(result[key], value)
            else:
                result.setdefault(key, value)
        return result

    return merge(existing_config, template_config)


async def verify_alt(guild_id, interaction) -> bool:
    """
    verify() but instead of a decorator its a function
    """
    prefix_enabled = await get_guild_config(guild_id)["prefix"]["prefix_enabled"]
    if not prefix_enabled:
        prefix_enabled = False
    if interaction is not None:
        return True
    return prefix_enabled


@client.event
async def on_command(ctx: commands.Context):
    if not ctx.interaction:
        await ctx.typing()
    logger.info(
        f"{ctx.command.qualified_name} has been used by {ctx.author.global_name} ({ctx.author.id})!"
    )


@client.check
async def is_module_enabled(ctx: commands.Context):
    if ctx.guild is None:
        return True
    if ctx.cog:
        if ctx.cog.qualified_name.lower() == "jishaku":
            return True
    if not ctx.cog:
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
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.MissingPermissions):
        e = discord.Embed(
            title="you don't have permissions to run this command.",
            color=Color.negative,
        )
        await ctx.reply(embed=e, ephemeral=True)
    if isinstance(error, KeyError):
        e = (discord.Embed(
            title="this server's configuration has malfunctioned.",
            description=
            "please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen) and the administrators of this server.",
            color=Color.lblue,
        ).add_field(name="error", value=f"```{error}```").add_field(
            name="command",
            value=f"```{ctx.command.full_parent_name}```",
            inline=False,
        ).add_field(name="version", value=f"```{version}```", inline=True))
        await ctx.send(embed=e, ephemeral=False)  # Handle other errors normally

        raise commands.errors.CommandError(str(error))
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        e = (discord.Embed(
            title="an error occurred while trying to run this command",
            description=
            "please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen)",
            color=Color.negative,
        ).add_field(name="error",
                    value=f"```{error}```").add_field(name="command",
                                                      value=f"```{ctx.command.name}```",
                                                      inline=False).add_field(
                                                          name="version",
                                                          value=f"```{version}```",
                                                          inline=True))
        await ctx.send(embed=e, ephemeral=True)  # Handle other errors normally
        logger.error(
            f"{ctx.author.name} ({ctx.author.id}) has encountered a {type(error).__name__}: {error}"
        )
        raise commands.errors.CommandError(str(error))


async def setup_guild(guild: discord.Guild,
                      gtype: int = 1) -> AsyncGenerator[list[discord.Embed], bool] | None:
    """
    Setup (initalize) a guild.
    Replaces on_guild_join and /settings init functions, and is shared between them.
    Returns embeds in realtime.
    Arguments:
        guild: `discord.Guild` object with the guild to setup.
        type: 1 = already existing guild, 2 = newly added guild
    """
    logger.debug(f"now setting up {guild.id}...")
    if gtype == 2:
        e = discord.Embed(
            title=
            f"Welcome to codygen! The bot has been successfully added to {guild.name}.",
            description=
            "## Support\n> Please join our [support server](https://discord.gg/WyxN6gsQRH).\n## Issues and bugs\n> Report all issues or bugs in the [issues tab](https://github.com/tjf1dev/codygen) of our GitHub repository.\n-# initializer v2",
            color=Color.white,
        )
        e2 = discord.Embed(
            title="codygen will now attempt to automatically initizalize in your server.",
            description=
            "> please wait, it can take a while.\n> note: if codygen dosen't update you on the progress of the initialization, you will need to do it yourself: run the </settings init:1340646304073650308> command in your guild.",
            color=Color.purple,
        )
    else:
        e = discord.Embed(
            title="hello! welcome (back) to codygen!",
            description=
            "## Support\n> Please join our [support server](https://discord.gg/WyxN6gsQRH).\n## Issues and bugs\n> Report all issues or bugs in the [issues tab](https://github.com/tjf1dev/codygen) of our GitHub repository.\n-# initializer v2",
            color=Color.white,
        )
        e2 = discord.Embed(
            title="codygen will now attempt to initizalize *(update)* in your server.",
            description="> please wait, it can take a while.",
            color=Color.purple,
        )

    yield [e, e2]
    await asyncio.sleep(2)
    bot_member = guild.me
    required_permissions = discord.Permissions(
        manage_roles=True,
        manage_channels=True,
        manage_guild=True,
        view_audit_log=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        mention_everyone=True,
        use_external_emojis=True,
        add_reactions=True,
    )
    if not bot_member.guild_permissions.is_superset(required_permissions):
        missing_perms = [
            perm for perm, value in required_permissions
            if not getattr(bot_member.guild_permissions, perm)
        ]
        error_embed = discord.Embed(
            title="Init Failed: Missing Permissions",
            description=
            f"### Missing the following permissions: `{', '.join(missing_perms)}`\nPlease fix the permissions and try again!",
            color=Color.negative,
        )
        yield [error_embed]
        logger.debug("yielded error_embed")
        return
    guild_config_path = f"data/guilds/{guild.id}.json"
    gconf = await get_guild_config(guild.id)
    if not gconf:
        config_already_made = False
    else:
        config_already_made = True

    conf = get_global_config()
    template_config = conf["template"]["guild"]

    if not config_already_made:
        os.makedirs(os.path.dirname(guild_config_path), exist_ok=True)
        await make_guild_config(guild.id, template_config)
    else:
        existing_config = await get_guild_config(guild.id)
        updated_config: dict = recursive_update(existing_config, template_config)
        updated_config["timestamp"] = time.time()
        await make_guild_config(guild.id, updated_config)
    stage2 = discord.Embed(
        title="Initialization Finished!",
        description="No errors found",
        color=Color.positive,
    )
    stage2.add_field(
        name="Tests Passed",
        value="Permissions\n> The bot has sufficient permissions to work!\n"
        f"Config\n> {'A configuration file already exists and has been updated with missing keys' if config_already_made else 'A configuration file has been created for your guild!'}",
    )
    yield [stage2]
    logger.debug(f"...finished setting up {guild.id}")


loaded_cogs = set()


@client.event
async def on_guild_join(guild):
    owner = guild.owner
    if not owner:
        return
    # try:
    #     async for embed in setup_guild(guild, gtype=2):
    #         await owner.send(embed=embed)
    # except Exception as e:
    #     logger.error(f"An error occurred while trying to setup {guild.name}: {e}")


client.start_time = time.time()


@client.event
async def on_ready():
    client.db = await database()
    client.ipc: ipcx.Server
    await client.ipc.start()
    logger.debug("starting dashboard (ipc)")
    client.full_commands = await get_command(TOKEN, client.user.id, name="*")
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
    logger.info(f"bot started as {Fore.LIGHTMAGENTA_EX}{client.user.name}{Fore.RESET}")
    admin_cog = client.get_cog("admin")
    if not admin_cog:
        return
    admin_group = admin_cog.admin

    @commands.is_owner()
    @admin_group.command(name="sync", description="syncs app commands")
    async def sync(ctx: commands.Context, flags: str = None):
        # get it flagl because flags and the s is string and l is list hahaha
        flagl = list(flags.strip("-"))
        e = discord.Embed(
            title=
            f"successfully synced {len(tree.get_commands())} commands for all guilds!",
            color=Color.positive,
        )
        e1 = discord.Embed(
            title=
            f"successfully synced {len(tree.get_commands())} commands for this guild!",
            color=Color.positive,
        )
        # used for when you want to sync globally but still have the guild first
        e2 = discord.Embed(
            title=
            f"successfully synced {len(tree.get_commands())} commands for this guild and all guilds!",
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

    # @client.event
    # async def on_message(message):
    #     if message.author.bot:
    #         return
    #     if message.content == f"<@{client.user.id}>":
    #         if verify_alt(message.guild.id,message.interaction) != True:
    #             e = discord.Embed(
    #                 title=f"hi! im codygen :3",
    #                 description=f"### try using </help:1338168344506925108>! prefixed commands are disabled in this server.",
    #                 color=0xff00ff
    #             )
    #         else:
    #             e = discord.Embed(
    #                 title=f"hi! im codygen :3",
    #                 description=f"### try using </help:1338168344506925108>! the prefix for this server is: `{await get_guild_config(message.guild.id)["prefix"]["prefix"]}`",
    #                 color=0xff00ff
    #             )
    #         await message.reply(embed=e)
    #     await client.process_commands(message)

    # async def run_quart():
    #     pass
    #     # await app.run_task(host="0.0.0.0", port=4888) #todo allow changing port

    # async def main():
    #     await asyncio.gather(run_quart(), ) and cog_name != "admin"


@tasks.loop(seconds=5.0)
async def heartbeart(self):
    logger.debug("heartbeat ping")


def main():
    ensure_env()
    client.run(TOKEN, root_logger=logger)


if __name__ == "__main__":
    logger.info("starting codygen")
    main()
