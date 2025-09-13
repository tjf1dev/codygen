from ext.utils import get_command, ensure_env, parse_commands
import os
import dotenv
import json
import time
from ext.logger import logger
from pathlib import Path
from models import Codygen

dotenv.load_dotenv()


async def cache_commands(bot: Codygen, _commands: list[dict] | None = None):
    """
    fetches the bot's commands and stores them in cache/commands.json and cache/commands/<timestamp>.json.
    also makes a .last_command_cache JSON file
    warning: only collects synced slash commands
    allows the commands to be passed manually for compatibility
    """
    ensure_env()
    logger.debug(f"caching commands in: {os.getcwd()}")

    base_cache = Path("cache/commands")
    docs_cache = Path("web/cache/commands")
    base_cache.mkdir(parents=True, exist_ok=True)
    docs_cache.mkdir(parents=True, exist_ok=True)

    CLIENT_TOKEN = os.getenv("CLIENT_TOKEN")
    CLIENT_ID = os.getenv("CLIENT_ID")
    assert CLIENT_TOKEN and CLIENT_ID is not None

    commands = _commands or parse_commands(
        await get_command(CLIENT_TOKEN, CLIENT_ID, name="*"), bot
    )

    ts = int(time.time())

    (Path("cache") / "commands.json").write_text(json.dumps(commands, indent=2))
    (base_cache / f"{ts}.json").write_text(json.dumps(commands, indent=2))
    Path(".last_command_cache").write_text(json.dumps({"time": time.time()}, indent=4))

    (Path("web/cache") / "commands.json").write_text(json.dumps(commands, indent=2))
    (docs_cache / f"{ts}.json").write_text(json.dumps(commands, indent=2))

    def trim(path: Path):
        files = sorted(path.glob("*.json"), key=lambda p: p.stem, reverse=True)
        for old in files[10:]:
            try:
                old.unlink()
            except Exception as e:
                logger.warning(f"could not delete {old}: {e}")

    trim(base_cache)
    trim(docs_cache)

    logger.info(f"{len(commands)} commands cached")
    return commands
