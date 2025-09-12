from discord.ext import commands
from typing import Any
import logging
import aiosqlite
from discord.ext import ipcx


class Codygen(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    color: Any
    version: str
    refresh_commands: Any
    ipc: ipcx.Server
    log: logging.Logger
    already_ready: bool
    db: aiosqlite.Connection
    start_time: float
    full_commands: list | dict
