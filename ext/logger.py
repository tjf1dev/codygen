import logging, os, datetime
from colorama import Fore

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.LIGHTBLACK_EX,
        'INFO': Fore.BLUE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
        'OK': Fore.GREEN
    }
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Fore.RESET}"
        record.msg = f"{log_color}{record.msg}{Fore.RESET}"
        return super().format(record)
    
logger = logging.getLogger(__name__)
if logger.hasHandlers():
    logger.handlers.clear()

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter('%(asctime)s %(funcName)s [ %(levelname)s ] %(message)s'))

logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)

for h in discord_logger.handlers:
    discord_logger.removeHandler(h)

logging.getLogger('discord.http').setLevel(logging.CRITICAL)

# file logging
if not os.path.exists("logs"):
    os.makedirs("logs")

log_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")

file_handler = logging.FileHandler(f"logs/{log_filename}")
file_handler.setFormatter('%(asctime)s %(funcName)s [ %(levelname)s ] %(message)s')

latest_handler = logging.FileHandler("logs/latest.log", mode='w')
latest_handler.setFormatter('%(asctime)s %(funcName)s [ %(levelname)s ] %(message)s')

logger.addHandler(file_handler)
logger.addHandler(latest_handler)