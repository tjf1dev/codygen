import aiofiles
import json
import discord
import time
import os
import pathlib
import asyncio
from models import Emote
from ext.logger import logger
from models import Codygen
from ext.errors import UnknownEmoteError


def _get_emote(name: str, config: dict) -> Emote | None:
    """
    Loads an emote from the provided key in the emote cache dict, fetches it's id and returns Emote, or None

    :param name: the name of the emote
    :type name: str
    :param config: configuration dict
    :type config: dict
    :return: the emote
    :rtype: tuple[str, int] | None
    """
    emotes = config.get(os.getenv("CLIENT_ID"), {})
    emote = emotes.get(name, None)
    if emote:
        return Emote(emote["name"], emote["id"], emote["animated"])


async def get_emotes_async() -> list[Emote]:
    async with aiofiles.open("emotes.json", "r") as f:
        cnf_text = await f.read()
        cnf = json.loads(cnf_text)
        emotes = cnf.get(os.getenv("CLIENT_ID"), {})
        return [Emote(e["name"], e["id"], e["animated"]) for e in emotes.values()]


def get_emote_sync(name: str) -> Emote:
    """
    Gets the emote cache, runs _get_emote and returns the found emote
    This function **blocks** the event loop. It is only recommended for specific use cases.
    :param name: the name of the emote
    :type name: str
    :return: the emote, or None
    :rtype: Emote | None
    """
    with open("emotes.json", "r") as f:
        cnf_text = f.read()
        em = _get_emote(name, json.loads(cnf_text))
        if not em:
            raise UnknownEmoteError(name)
        return em


async def get_emote_async(name: str) -> Emote:
    """
    Gets the emote cache, runs _get_emote and returns the found emote

    :param name: the name of the emote
    :type name: str
    :return: the emote, or None
    :rtype: Emote | None
    """
    async with aiofiles.open("emotes.json", "r") as f:
        cnf_text = await f.read()
        em = _get_emote(name, json.loads(cnf_text))
        if not em:
            raise UnknownEmoteError(name)
        return em


async def create_emote(name: str, path: str, client: Codygen):
    logger.debug(f"creating emote '{name}' from {path}")
    async with aiofiles.open(path, "rb") as f:
        raw = await f.read()
    # name = pathlib.Path(path).stem
    emote = await client.create_application_emoji(name=name, image=raw)
    return emote


def get_emotes_from_assets():
    assets_path = pathlib.Path("assets") / "emotes"
    emotes_from_files = [pathlib.Path(em).stem for em in os.listdir(assets_path)]
    return emotes_from_files


async def check_if_all_emotes_exist(client: Codygen):
    if not client.user:
        return False

    emotes_from_files = get_emotes_from_assets()

    try:
        async with aiofiles.open("emotes.json", "r") as f:
            emotes_file = json.loads(await f.read())
    except Exception:
        emotes_file = {}

    emotes_from_json = emotes_file.get(str(client.user.id), {}).keys()

    return set(emotes_from_files).issubset(emotes_from_json)


async def create_emotes_from_assets(
    existing: list[discord.Emoji], client: Codygen
) -> list[discord.Emoji] | None:
    if not client.user:
        return
    if not existing:
        logger.debug("fetching emotes..")
        existing = await client.fetch_application_emojis()
    existing_emotes = existing
    assets_path = pathlib.Path.joinpath(pathlib.Path("assets"), pathlib.Path("emotes"))
    try:
        saved_emotes_file = json.loads(
            await (await aiofiles.open("emotes.json", "r")).read()
        )
    except Exception:
        saved_emotes_file = {}
    saved_emotes = saved_emotes_file.get(client.user.id, {})
    created = []
    for file in os.listdir(assets_path):
        if file in saved_emotes.keys():
            return
        name = pathlib.Path(file).stem
        if name in [em.name for em in existing_emotes]:
            continue
        em = await create_emote(
            name, str(pathlib.Path.joinpath(assets_path, pathlib.Path(file))), client
        )
        await asyncio.sleep(1)
        created.append(em)
        logger.debug(f"created emote {created}")
    return created


async def create_emotes_json_file(
    emotes: list[discord.Emoji] | list[Emote], client: Codygen
):
    if not client.user:
        return
    if not emotes:
        logger.debug("fetching emotes...")
        emotes = await client.fetch_application_emojis()
    emotes_dict = {}
    for emote in emotes:
        logger.debug(f"found emote {emote.name}")
        emotes_dict[emote.name] = {
            "name": emote.name,
            "id": emote.id,
            "animated": emote.animated,
        }
    try:
        original = json.loads(await (await aiofiles.open("emotes.json", "r")).read())
    except Exception:
        original = {}

    original["readme"] = (
        "this file contains data about emotes that the bot has automatically created. you do not need to modify this file, as this data will be generated upon startup."
    )
    original["modified"] = time.time()
    original[str(client.user.id)] = emotes_dict
    out_str = json.dumps(original, indent=4)
    await (await aiofiles.open("emotes.json", "w")).write(out_str)
