import logger
import aiohttp
from typing import Dict, List, Any, cast
from models import Codygen


async def get_commands(token: str, client_id: str | int) -> List[Dict[str, Any]]:
    """
    short for get_command(name="*")
    """
    return cast(List[Dict[str, Any]], await get_command(token, client_id, name="*"))


async def get_command(
    token: str, client_id: str | int, id: int = 0, name: str = "", full_name: str = ""
) -> Dict | List[Dict[str, Any]]:
    """
    gets information about a command by name, full name or id
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
                data: list[dict[str, Any]] = await resp.json()
        if name == "*":
            logger.debug("command list downloaded")
            return data

        for command in data:
            if id in command["id"]:
                return command
            if full_name in command["full_name"]:
                return command
            if name in command["name"]:
                return command
        return {}
    except Exception:
        return {}


# TODO add custom value support
# TODO allow detailed command descriptions, with examples, previews, etc.
# TODO make the output the same for each command, and less messy
def parse_commands(commands, bot=None) -> list[dict]:
    """
    formats commands into a nice list
    disregards groups, context menus
    optionally adds cog information if bot is provided
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


def map_custom_commands_to_cogs(bot: Codygen):
    def get_full_command_name(cmd):
        return (
            f"{cmd.full_parent_name} {cmd.name}" if cmd.full_parent_name else cmd.name
        )

    # get all custom commands
    all_custom_commands = parse_commands(bot.full_commands)

    dpy_command_lookup = {}
    cog_lookup = {}

    for cog_name, cog in bot.cogs.items():
        if cog_name.lower() in ["jishaku"]:
            continue

        cog_commands = list(cog.walk_commands())
        for cmd in cog_commands:
            full_name = get_full_command_name(cmd)
            dpy_command_lookup[full_name] = cmd
            cog_lookup[full_name] = (cog, cog_name)

    mapped_commands = []

    for custom_cmd in all_custom_commands:
        cmd_full_name = custom_cmd["full_name"]

        dpy_cmd = dpy_command_lookup.get(cmd_full_name)
        cog_info = cog_lookup.get(cmd_full_name)

        if dpy_cmd and cog_info:
            cog, cog_name = cog_info
            mapped_cmd = {
                **custom_cmd,
                "cog": {
                    "name": cog_name,
                    "description": getattr(cog, "description", None),
                },
            }
            mapped_commands.append(mapped_cmd)

    return mapped_commands
