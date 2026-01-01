import base64
import datetime
import aiohttp
import aiosqlite
import asyncio
from ext.logger import logger
import os
import sys
import discord
from typing import Tuple, Optional, Any, List, AsyncGenerator
from models import Codygen
from ext.ui_base import Message
from ext.colors import Color
import hmac
import hashlib
import ext.errors


def state_to_id(state: str) -> str:
    euid = state.split("@")[0]
    return base64.b64decode(euid).decode()


def lfm_generate_state_hash(user_id: int, secret: str) -> str:
    user_bytes = str(user_id).encode()
    secret_bytes = secret.encode()
    digest = hmac.new(secret_bytes, user_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)[:12].decode()


def lfm_generate_full_state(user_id: int) -> str:
    salt = os.getenv("STATE_SALT")
    if not salt:
        raise ext.errors.MissingEnvironmentVariable("STATE_SALT")
    hash = lfm_generate_state_hash(user_id, salt)
    id_enc = base64.b64encode(str(user_id).encode()).decode()
    return f"{id_enc}@{hash}"


# TODO add custom value support
# TODO allow detailed command descriptions, with examples, previews, etc.
# TODO make the output the same for each command, and less messy
def parse_commands(commands, bot=None) -> list[dict]:
    """
    Formats commands into a nice list
    Disregards groups, context menus
    Optionally adds cog information if bot is provided
    """

    def get_full_command_name(cmd):
        return (
            f"{cmd.full_parent_name} {cmd.name}" if cmd.full_parent_name else cmd.name
        )

    valid_cmds = []

    dpy_command_lookup = {}
    if bot:
        for cog_name, cog in bot.cogs.items():
            if cog_name.lower() in ["jishaku"]:
                continue

            cog_commands = list(cog.walk_commands())
            for cmd in cog_commands:
                full_name = get_full_command_name(cmd)
                dpy_command_lookup[full_name] = {
                    "cog_name": cog_name,
                    "cog_description": getattr(cog, "description", "") or "",
                    "description": cmd.description or "",
                }

    # command_type = my custom type for commands
    # parent
    # 0 - regular parent (not group) command
    # 3 - context menu (those get ignored in this case)
    # 6 - unknown
    # not parent
    # 1 - subcommand from a group
    # 2 - sub-subcommand
    # 5 - group with a parent
    for cmd in commands:
        command_type = (
            0  # here we set to regular command, because we cant tell what it is yet
        )
        if cmd["type"] == 3:  # context menu
            command_type = 3
        elif cmd["type"] != 1:
            command_type = 6

        options = cmd.get("options", None)
        # if it doesnt have any options and the type is 1, its 100% sure its regular command (type 0)
        # if it does...
        if options:
            for option in options:
                if option["type"] == 1:
                    subcommand_data = {
                        "name": option["name"],
                        "full_name": f"{cmd['name']} {option['name']}",
                        "parent": {"name": cmd["name"]},
                        "command": option,
                        "id": cmd["id"],
                        "is_subcommand": 1,
                    }
                    # Add cog info if available
                    if bot and subcommand_data["full_name"] in dpy_command_lookup:
                        subcommand_data.update(
                            dpy_command_lookup[subcommand_data["full_name"]]
                        )
                    valid_cmds.append(subcommand_data)

                if option["type"] == 2:  # group with a parent
                    for sub_option in option.get("options", {}):  # looking for type 2's
                        if sub_option["type"] == 1:  # sub-subcommand
                            sub_option_parent = option["name"]
                            option_parent = cmd["name"]
                            sub_sub_data = {
                                "name": sub_option["name"],
                                "full_name": f"{option_parent} {sub_option_parent} {sub_option['name']}",
                                "parent": {
                                    "name": sub_option_parent,
                                    "parent": {"name": option_parent},
                                },
                                "command": sub_option,
                                "id": cmd["id"],
                                "is_subcommand": 2,
                            }
                            # Add cog info if available
                            if bot and sub_sub_data["full_name"] in dpy_command_lookup:
                                sub_sub_data.update(
                                    dpy_command_lookup[sub_sub_data["full_name"]]
                                )
                            valid_cmds.append(sub_sub_data)
        else:
            if command_type == 0:
                cmd["command"] = cmd.copy()
                cmd["command"].pop("command", None)  # compatibility
                cmd["full_name"] = cmd["name"]  # also compatibility
                cmd["is_subcommand"] = 0
                # Add cog info if available
                if bot and cmd["full_name"] in dpy_command_lookup:
                    cmd.update(dpy_command_lookup[cmd["full_name"]])
                valid_cmds.append(cmd)

    return valid_cmds


async def get_xp(user: discord.Member, bot: Codygen):
    query = await (
        await bot.db.execute(
            "SELECT xp FROM users WHERE guild_id=? AND user_id=?",
            (user.id, user.guild.id),
        )
    ).fetchone()
    if query:
        return query[0]


async def get_command(
    token: str, client_id: str | int, id: int = 0, name: str = ""
) -> dict | list[dict]:
    """
    gets information about a command by name or id
    one of those is required
    set name to * for all commands
    dedicated to discord.py since you cannot include command ids in your classes
    if pycord can do it why cant you
    """
    url = f"https://discord.com/api/v10/applications/{client_id}/commands"
    headers = {"Authorization": f"Bot {token}"}
    try:
        if not name and not id:
            logger.error("either name or id is required")
            return {}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as resp:
                data: list = await resp.json()
        if name == "*":
            logger.debug("command list downloaded")
            return data

        for command in data:
            if id in command["id"]:
                return command
            if name in command["name"]:
                return command
        return {}
    except Exception:
        return {}


def iso_to_unix(iso_str: str) -> int:
    """
    Convert an ISO 8601 UTC timestamp string to a Unix timestamp.

    Args:
        iso_str (str): ISO timestamp, e.g. '2025-06-28T16:50:11Z'

    Returns:
        int: Unix timestamp (e.g. 1751129411)
    """
    if iso_str.endswith("Z"):
        iso_str = iso_str.replace("Z", "+00:00")

    dt = datetime.datetime.fromisoformat(iso_str)
    return int(dt.timestamp())


def timestamp(unix: str | int | float, mode: str = "R", inf_text: str = "never") -> str:
    """
    Converts a unix timestamp into a Discord timestamp
    """
    if unix == -1:
        return inf_text
    return f"<t:{int(unix)}:{mode}>"


def _old_xp_to_level(xp):
    level = 1
    xp_needed = 100
    increment = 50

    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed += increment

    return level


def adjusted_xp_cost(level: int, base_xp: float = 50, exponent: float = 1.24) -> float:
    return base_xp * (level**exponent)


def level_to_xp(level: int, base_xp: float = 50, exponent: float = 1.24) -> int:
    total_xp = 0
    for lvl in range(1, level + 1):
        total_xp += adjusted_xp_cost(lvl, base_xp, exponent)
    return round(total_xp)


def xp_to_level(xp: int | float, base_xp: float = 50, exponent: float = 1.24) -> int:
    level = 1
    while True:
        cost = adjusted_xp_cost(level, base_xp, exponent)
        if xp < cost:
            break
        xp -= cost
        level += 1
    return level


def map_custom_commands_to_cogs(bot):
    """
    Maps custom commands to their corresponding discord.py commands and cogs.
    Returns only JSON-serializable data.

    Args:
        bot: The discord.py Bot instance

    Returns:
        list: A list of dictionaries with custom command data plus cog info (JSON-serializable)
        Structure: [
            {
                # All original custom command data (id, full_name, etc.)
                'id': '...',
                'full_name': '...',
                'description': '...',
                # Plus cog data (serializable only)
                'cog_name': str,
                'cog_description': str,
                'dpy_description': str,  # Description from discord.py command
                'dpy_help': str,         # Help text from discord.py command
                'dpy_usage': str,        # Usage from discord.py command
                'dpy_brief': str         # Brief description from discord.py command
            }
        ]
    """

    def get_full_command_name(cmd):
        return (
            f"{cmd.full_parent_name} {cmd.name}" if cmd.full_parent_name else cmd.name
        )

    # Get all custom commands
    all_custom_commands = parse_commands(bot.full_commands)

    # Create lookup dictionary for all discord.py commands
    dpy_command_lookup = {}
    cog_lookup = {}

    # Build lookup tables from all cogs
    for cog_name, cog in bot.cogs.items():
        if cog_name.lower() in ["jishaku"]:
            continue

        cog_commands = list(cog.walk_commands())
        for cmd in cog_commands:
            full_name = get_full_command_name(cmd)
            dpy_command_lookup[full_name] = cmd
            cog_lookup[full_name] = (cog, cog_name)

    # Map custom commands to discord.py commands and cogs (JSON-serializable only)
    mapped_commands = []

    for custom_cmd in all_custom_commands:
        cmd_full_name = custom_cmd["full_name"]

        # Find matching discord.py command and cog
        dpy_cmd = dpy_command_lookup.get(cmd_full_name)
        cog_info = cog_lookup.get(cmd_full_name)

        if dpy_cmd and cog_info:
            cog, cog_name = cog_info
            # Create new dict with all custom data plus serializable cog info
            mapped_cmd = {
                **custom_cmd,  # Spread all custom command data
                "cog_name": cog_name,
                "cog_description": getattr(cog, "description", "") or "",
            }
            mapped_commands.append(mapped_cmd)

    return mapped_commands


def parse_flags(s: str) -> dict[str, str | bool]:
    parts = s.split()
    flags: dict[str, str | bool] = {}
    i = 0
    while i < len(parts):
        t = parts[i]
        if t.startswith("--"):
            key = t[2:]
            value = True
            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                value = parts[i + 1]
                i += 1
            flags[key] = value
        elif t.startswith("-"):
            keys = list(t[1:])
            for key in keys:
                value = True
                if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                    value = parts[i + 1]
                    i += 1
                flags[key] = value
        i += 1
    return flags


def get_message_code(
    message: discord.Message,
) -> Tuple[
    int,
    Optional[Any],
    Optional[str],
    Optional[List[discord.Attachment]],
    Optional[discord.Message | Any],
]:
    """
    Returns a tuple describing the message:
    0: type code
        0 = content only
        1 = embeds + content
        2 = embeds only
        3 = attachments only
        4 = embeds + attachments
        5 = content + attachments
        6 = embeds + content + attachments
    1: embeds or None
    2: content or None
    3: attachments list or None
    4: replied_to message or None
    """
    embeds = message.embeds if message.embeds else None
    content = message.content if message.content else None
    attachments = message.attachments if message.attachments else None
    replied = message.reference.resolved if message.reference else None
    code = 0
    if embeds and content and attachments:
        code = 6
    elif embeds and content:
        code = 1
    elif embeds and attachments:
        code = 4
    elif content and attachments:
        code = 5
    elif embeds:
        code = 2
    elif attachments:
        code = 3
    elif content:
        code = 0
    return code, embeds, content, attachments, replied


def describe_message(message: discord.Message) -> str:
    """
    returns a user-friendly description of a discord.Message
    """
    parts = []

    if message.content:
        parts.append(f"```{message.content}```")

    if message.embeds:
        parts.append(f"-# Embeds: `{len(message.embeds)}`")

    if message.attachments:
        attach_list = ", ".join(a.filename for a in message.attachments)
        parts.append(f"-# Attachments ({len(message.attachments)}): `{attach_list}`")

    if not parts:
        return "-# [empty / unable to load]"

    return "\n".join(parts)


def get_required_env() -> list:
    r = []
    with open(".env.template", "r") as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("#") or not line or line == "\n":
                continue
            r.append(line.split("=")[0])
    return r


def ensure_env():
    """
    Checks that all REQUIRED_ENV keys exist and are non-empty.
    (so the user can copy it to .env and fill in real values),
    then exits with a meaningful message.
    """
    missing = []
    REQUIRED_ENV = get_required_env()
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
            + "https://github.com/tjf1dev/codygen#self-hosting."
        )
        sys.exit(1)


def permissions_to_list(perms: discord.Permissions) -> list:
    enabled = [name.replace("_", " ").title() for name, value in perms if value]
    return enabled if enabled else ["[none]"]


async def setup_guild(
    bot: Codygen, guild: discord.Guild, gtype: int = 1
) -> AsyncGenerator[discord.ui.View | discord.ui.LayoutView, bool]:
    """
    Setup (initalize) a guild.
    Replaces on_guild_join and /settings init functions, and is shared between them.
    Returns embeds in realtime.
    Arguments:
        guild: `discord.Guild` object with the guild to setup.
        type: 1 = already existing guild, 2 = newly added guild
    """
    # gtype spoof for testing
    # gtype = 2
    logger.debug(f"now setting up {guild.id}...")
    message = ""
    if gtype == 2:
        message += f"## welcome! codygen has been successfully added to {guild.name}.\n"
    message += f"{'## ' if gtype != 2 else ''}codygen will now attempt to{' automatically' if gtype == 2 else ''} initizalize in your server.\n"
    message += "> please wait, it can take a while.\n"
    message += "## support\n> join our [support server](https://discord.gg/WyxN6gsQRH).\n## issues and bugs\n> report all issues or bugs in the [issues tab](https://github.com/tjf1dev/codygen) of our github repository\n"

    if gtype == 2:
        message += "-# if something goes wrong: try running the </settings init:1340646304073650308> command in your guild.\n"
    message += "-# initializer v3"
    e = Message(
        message=message,
        accent_color=Color.purple,
    )
    yield e
    await asyncio.sleep(2)
    logger.debug("attempting to insert database values")
    db: aiosqlite.Connection = bot.db
    try:
        await db.execute("INSERT INTO guilds (guild_id) VALUES (?)", (guild.id,))
        logger.debug("made default guild data")
        config_already_made = False
    except Exception as e:
        logger.warning(
            f"failed when inserting guild data for {guild.id}; {type(e).__name__}: {e}"
        )
        config_already_made = True
    try:
        await db.execute("INSERT INTO modules (guild_id) VALUES (?)", (guild.id,))
        logger.debug("made default module data")
    except Exception as e:
        logger.warning(
            f"failed when inserting module data for {guild.id}; {type(e).__name__}: {e}"
        )
        pass
    await db.commit()
    bot_member = guild.me
    required_permissions = discord.Permissions(
        manage_roles=True,
        manage_channels=True,
        manage_guild=True,
        view_audit_log=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
        kick_members=True,
        ban_members=True,
        create_instant_invite=True,
        change_nickname=True,
        manage_nicknames=True,
        send_messages_in_threads=True,
        create_public_threads=True,
        create_private_threads=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        mention_everyone=True,
        use_external_emojis=True,
        add_reactions=True,
    )
    if not bot_member.guild_permissions.is_superset(required_permissions):
        missing_perms = [
            perm
            for perm, value in required_permissions
            if not getattr(bot_member.guild_permissions, perm)
        ]
        permission_error = Message(
            message=f"# initialization failed: missing permissions\n### missing the following permissions: `{', '.join(missing_perms)}`\nplease fix the permissions and try again!",
            accent_color=Color.negative,
        )
        yield permission_error
        logger.debug("yielded permission_error")

    stage2 = Message(
        message=f"# initialization finished!\n> no errors found\npermissions\n> the bot has sufficient permissions to work!\nconfig\n> {'a configuration already exists and has been updated!' if config_already_made else 'a configuration has been created for your guild!'}\n"
        "\n> **warning**\n> most commands won't work unless their modules are enabled.\n> run /settings modules in the server to configure modules, or use the dashboard.",
        accent_color=Color.positive,
    )
    yield stage2
    logger.debug(f"...finished setting up {guild.id}")
