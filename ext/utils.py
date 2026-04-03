import base64
import datetime
import aiosqlite
import asyncio
import logger
import os
import sys
import discord
from ext.commands import get_command
from typing import Tuple, Optional, Any, List, AsyncGenerator
from ext.config import DEFAULT_MODULE_OVERRIDE, DEFAULT_MODULE_STATE
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


def iso_to_unix(iso_str: str) -> int:
    """
    convert an ISO 8601 UTC timestamp string to a Unix timestamp.
    used for deprecated database types. (we use unix timestamps now)

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


def percentage_from_string(string):
    hash_object = hashlib.sha256(string.encode())
    hex_digest = hash_object.hexdigest()
    int_value = int(hex_digest, 16)
    number = (int_value % 100) + 1
    return number


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


def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


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
    error = None
    config_already_made = False
    ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
    try:
        await db.execute(
            "INSERT INTO guilds (guild_id, timestamp) VALUES (?, ?)", (guild.id, ts)
        )
        logger.debug("made default guild data")
        config_already_made = False
    except Exception as e:
        logger.warning(
            f"failed when inserting guild data for {guild.id}; {type(e).__name__}: {e}"
        )
        if str(e).startswith("UNIQUE constraint failed"):
            config_already_made = True
        else:
            error = e
    try:
        cog_names = bot.get_modules().keys()
        columns = ["guild_id", *cog_names]
        placeholders = ", ".join("?" for _ in columns)
        values = [
            guild.id,
            *(DEFAULT_MODULE_OVERRIDE.get(c, DEFAULT_MODULE_STATE) for c in cog_names),
        ]
        logger.debug(f"{cog_names} {bot.cogs} {columns} {placeholders}")

        await db.execute(
            f"INSERT INTO modules ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        logger.debug("made default module data")
    except Exception as e:
        if isinstance(e, aiosqlite.OperationalError):
            if str(e).startswith("table modules has no column named"):
                logger.error(
                    f"database is outdated. please use ./codygen db add_column or ./codygen db recreate to add the '{str(e).split()[len(str(e).split()) - 1]}' column."
                )
        logger.warning(
            f"failed when inserting module data for {guild.id}; {type(e).__name__}: {e}"
        )
        if str(e).startswith("UNIQUE constraint failed"):
            config_already_made = True
        else:
            error = e
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

    modules_command = "/settings modules"
    modules_command_id = next(
        (m["id"] for m in bot.parsed_commands if m["full_name"] == "settings modules"),
        0,
    )

    if modules_command_id:
        modules_command = f"</settings modules:{modules_command_id}>"

    stage2 = Message(
        message=f"# initialization finished!\n> no errors found\npermissions\n> the bot has sufficient permissions to work!\nconfig\n> {'a configuration already exists and has been updated!' if config_already_made else 'a configuration has been created for your guild!'}\n"
        f"\n> **warning**\n> most commands won't work unless their modules are enabled.\n> run {modules_command} in the server to configure modules, or use the dashboard.",
        accent_color=Color.positive,
    )
    if error:
        e = error
        stage2 = Message(
            message=f"# initialization failed: internal error\ntry again or file a bug report.\n-# `{type(e).__name__}: {e}`",
            accent_color=Color.negative,
        )
    yield stage2
    logger.debug(f"...finished setting up {guild.id}")
