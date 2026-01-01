import aiohttp
from PIL import Image
from io import BytesIO
import discord
import os
import requests
import json
from discord.ext import commands
from discord import app_commands
from main import Color, logger
import aiofiles
from ext.ui_base import Message
import ext.errors
from typing import cast
from models import Cog
from views import fmLayout, lastfmMessageWithLogin


async def get_average_color(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.read()
            img = Image.open(BytesIO(content)).convert("RGB")
            pixels = list(img.getdata())  # type: ignore
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return (r, g, b)


class fm(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = (
            "use your Last.fm integration to check what you're listening to."
        )
        self.allowed_contexts = discord.app_commands.allowed_contexts(True, True, True)
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    async def fetch_now_playing(self, username, raw: bool = False):
        """Fetches the currently playing track, scrobble count, and track play count for a Last.fm user."""
        api_key = os.environ["LASTFM_API_KEY"]
        base_url = "http://ws.audioscrobbler.com/2.0/"

        # Fetch recent tracks
        params_tracks = {
            "method": "user.getrecenttracks",
            "user": username,
            "api_key": api_key,
            "format": "json",
            "limit": 1,
        }
        response_tracks = requests.get(base_url, params=params_tracks)
        data_tracks = response_tracks.json()

        if "error" in data_tracks:
            return None, data_tracks["message"]  # Handle API errors

        tracks = data_tracks.get("recenttracks", {}).get("track", [])
        if not tracks:
            return None, "No recent tracks found."

        now_playing = tracks[0]
        artist = now_playing["artist"]["#text"]
        track_name = now_playing["name"]
        album = now_playing["album"]["#text"]
        url = now_playing["url"]
        is_now_playing = now_playing.get("@attr", {}).get("nowplaying") == "true"
        params_info = {
            "method": "user.getinfo",
            "user": username,
            "api_key": api_key,
            "format": "json",
        }
        response_info = requests.get(base_url, params=params_info)
        data_info = response_info.json()

        if "error" in data_info:
            return None, data_info["message"]

        scrobble_count = data_info.get("user", {}).get("playcount", "Unknown")
        params_track_info = {
            "method": "track.getInfo",
            "api_key": api_key,
            "artist": artist,
            "track": track_name,
            "user": username,
            "format": "json",
        }
        response_track_info = requests.get(base_url, params=params_track_info)
        data_track_info = response_track_info.json()

        if "error" in data_track_info:
            track_scrobble_count = "Unknown"
        else:
            track_scrobble_count = data_track_info.get("track", {}).get(
                "userplaycount", "0"
            )
        if raw:
            return data_track_info
        return {
            "artist": artist,
            "track": track_name,
            "album": album,
            "image": data_track_info["track"]["album"]["image"][
                len(data_track_info["track"]["album"]["image"]) - 1
            ]["#text"],
            "url": url,
            "now_playing": is_now_playing,
            "scrobble_count": scrobble_count,
            "track_scrobble_count": track_scrobble_count,
        }, None

    @commands.hybrid_group(
        name="lastfm",
        description="all commands with the last.fm api.",
        with_app_command=True,
    )
    async def lastfm(self, ctx: commands.Context):
        pass

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @lastfm.command(
        name="logout",
        description="remove your last.fm data from the bot",
        with_app_command=True,
    )
    async def logout(self, ctx: commands.Context):
        user_file = "data/last.fm/users.json"
        try:
            async with aiofiles.open(user_file, "r") as f:
                content = await f.read()
            data = json.loads(content)
        except FileNotFoundError:
            await ctx.reply(
                view=Message("## you are not logged in with last.fm."), ephemeral=True
            )

            return

        user_id_str = str(ctx.author.id)
        if user_id_str not in data:
            await ctx.reply(
                view=lastfmMessageWithLogin("## you are not logged in with last.fm."),
                ephemeral=True,
            )
            return

        data.pop(user_id_str)
        async with aiofiles.open(user_file, "w") as f:
            await f.write(json.dumps(data, indent=4))

        await ctx.reply(
            view=Message(
                "## your last.fm data has been removed successfully.\nyou can log back in anytime"
            ),
            ephemeral=True,
        )

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="fm", description="see what you're listening to.", with_app_command=True
    )
    async def fm(self, ctx: commands.Context):
        try:
            async with aiofiles.open(
                "data/last.fm/users.json", "r"
            ) as f:  # TODO make the lastfm login a db thing
                content = await f.read()
                data = json.loads(content)
                username = (
                    data.get(str(ctx.author.id), {}).get("session", {}).get("name", {})
                )
                if not username:
                    await ctx.reply(
                        view=lastfmMessageWithLogin(
                            "## Not logged in!\nuse the button below to authenticate with last.fm",
                            accent_color=Color.negative,
                        ),
                        ephemeral=True,
                    )
                    return
            track_info_raw = await self.fetch_now_playing(username)
            if not track_info_raw:
                raise ext.errors.LastfmLoggedOutError()
            else:
                track_info = cast(dict, track_info_raw[0])
            # if not ctx.interaction:
            #     logger.warning("interaction doesnt exist for some reason")
            #     return
            await ctx.reply(view=fmLayout(track_info), mention_author=False)
        except FileNotFoundError:
            view = lastfmMessageWithLogin(
                "## Not logged in!\nPlease use the button below to authenticate with Last.fm"
            )
            await ctx.reply(view=view, ephemeral=True)
        # except Exception as err:
        #     view = lastfmMessageWithLogin(
        #         f"## An error occured!\nPlease report this to the bot developers. you can also try authenticating again\n```{type(err).__name__}: {str(err)}```",
        #         accent_colour=Color.negative,
        #     )
        #     await ctx.reply(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(fm(bot))
