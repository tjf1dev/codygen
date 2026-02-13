from discord.ext import commands
from typing import Any, Mapping
import logging
import aiosqlite
from discord.ext import ipcx
from .emote import Emote
from .module import Module
from collections.abc import Callable


class Codygen(commands.AutoShardedBot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cogs = {}

    version: str
    release: bool

    db: aiosqlite.Connection
    get_modules: Callable[[], Mapping[str, Module]]

    start_time: float
    already_ready: bool

    color: Any
    log: logging.Logger
    emotes: list[Emote]
    cogs: Mapping[str, Module]  # type: ignore
    ipc: ipcx.Server

    refresh_commands: Any
    full_commands: list[dict[str, Any]]
    parsed_commands: list[dict[str, Any]]

    def emote(self, name: str):
        return next(em for em in self.emotes if em.name == name)

    def module(self, name: str):
        return next(m for n, m in self.cogs.items() if n == name)
