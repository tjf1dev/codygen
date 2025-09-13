import logging
import os
import datetime
from colorama import Fore
from typing import cast


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.LIGHTBLACK_EX,
        "INFO": Fore.BLUE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
        "OK": Fore.GREEN,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Fore.RESET}"
        record.msg = f"{log_color}{record.msg}{Fore.RESET}"
        return super().format(record)


OK_LEVEL = 25
logging.addLevelName(OK_LEVEL, "OK")


class ExtLogger(logging.Logger):
    def ok(self, message, *args, **kwargs):
        if self.isEnabledFor(OK_LEVEL):
            self._log(OK_LEVEL, message, args, stacklevel=2, **kwargs)


logging.setLoggerClass(ExtLogger)
logger = cast(ExtLogger, logging.getLogger(__name__))
if logger.hasHandlers():
    logger.handlers.clear()

handler = logging.StreamHandler()

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
handler.setFormatter(
    ColorFormatter(
        "%(asctime)s [ %(levelname)s ] %(message)s (%(funcName)s)",
        datefmt="%d/%m/%Y %H:%M:%S",
    )
)

file_formatter = logging.Formatter(
    "%(asctime)s [ %(levelname)s ] %(message)s: (%(funcName)s)",
    datefmt="%d/%m/%Y %H:%M:%S",
)

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.INFO)
logging.getLogger("discord.http").setLevel(logging.INFO)
colorless_formatter = "%(asctime)s [ %(levelname)s ] %(funcName)s: %(message)s"
# file logging
if not os.path.exists("logs"):
    os.makedirs("logs")

log_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")

file_handler = logging.FileHandler(f"logs/{log_filename}")
latest_handler = logging.FileHandler("logs/latest.log", mode="w")
file_handler.setFormatter(file_formatter)
latest_handler.setFormatter(file_formatter)

logger.addHandler(file_handler)
logger.addHandler(latest_handler)
