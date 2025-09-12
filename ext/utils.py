import base64
import datetime
import aiohttp
from ext.logger import logger

import discord
from typing import AsyncGenerator
from ext.colors import Color
import asyncio


def state_to_id(state: str) -> str:
    euid = state.split("@")[0]
    return base64.b64decode(euid).decode()


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
                    "dpy_description": cmd.description or "",
                    "dpy_help": cmd.help or "",
                    "dpy_usage": str(cmd.usage) if cmd.usage else "",
                    "dpy_brief": cmd.brief or "",
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
                    for sub_option in option["options"]:  # looking for type 2's
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


def timestamp(unix: str, mode: str = "R", inf_text: str = "never") -> str:
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
            key = t[1:]
            value = True
            if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                value = parts[i + 1]
                i += 1
            flags[key] = value
        i += 1
    return flags
