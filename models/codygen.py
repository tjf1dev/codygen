from discord.ext import commands
from typing import Any
import logging
import aiosqlite
from discord.ext import ipcx
from .emote import Emote


class Codygen(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    color: Any
    version: str
    refresh_commands: Any
    ipc: ipcx.Server
    log: logging.Logger
    release: bool
    already_ready: bool
    db: aiosqlite.Connection
    start_time: float
    full_commands: list | dict
    emotes: list[Emote]

    def emote(self, name: str):
        return next(em for em in self.emotes if em.name == name)
