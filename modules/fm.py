import base64
import hmac
import aiohttp
import hashlib
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


async def get_average_color(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.read()
            img = Image.open(BytesIO(content)).convert("RGB")
            pixels = list(img.getdata())
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return (r, g, b)


class fmSection(discord.ui.Section):
    def __init__(self, track_info: dict):
        accessory = discord.ui.Thumbnail(media=track_info["image"])

        super().__init__(accessory=accessory)
        display_text = (
            f"## [{track_info['track']}]({track_info['url']})\n"
            f"{track_info['artist']} {"• " if track_info.get('album', None) else ""}{track_info.get('album', '')}\n"
            f"{track_info['track_scrobble_count']} scrobbles, "
            f"{track_info['scrobble_count']} total"
        )

        self.add_item(discord.ui.TextDisplay(display_text))


class fmActionRow(discord.ui.ActionRow):
    def __init__(self, track_info: dict):
        super().__init__()
        self.voted_users = {}  # {user_id: "up" or "down"}

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        emoji="<:downvote:1388512428484198482>",
        label="0",
    )
    async def downvote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        user_id = interaction.user.id
        upvote_button = next(b for b in self.children if b.emoji.name == "upvote")

        current_vote = self.voted_users.get(user_id)

        if current_vote == "down":
            self.voted_users.pop(user_id)
            button.label = str(int(button.label) - 1)
        elif current_vote == "up":
            self.voted_users[user_id] = "down"
            button.label = str(int(button.label) + 1)
            upvote_button.label = str(int(upvote_button.label) - 1)
        else:
            self.voted_users[user_id] = "down"
            button.label = str(int(button.label) + 1)

        await interaction.edit_original_response(view=self.view)

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        emoji="<:upvote:1388512426059759657>",
        label="0",
    )
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user_id = interaction.user.id

        downvote_button = next(b for b in self.children if b.emoji.name == "downvote")

        current_vote = self.voted_users.get(user_id)

        if current_vote == "up":
            # if interaction.user.id == 978596696156147754:
            #     button.label = str(int(button.label) + 100)
            #     return
            self.voted_users.pop(user_id)
            button.label = str(int(button.label) - 1)
        elif current_vote == "down":
            self.voted_users[user_id] = "up"
            button.label = str(int(button.label) + 1)
            downvote_button.label = str(int(downvote_button.label) - 1)
        else:
            self.voted_users[user_id] = "up"
            button.label = str(int(button.label) + 1)

        await interaction.edit_original_response(view=self.view)


class fmLayout(discord.ui.LayoutView):
    def __init__(
        self, interaction: discord.Interaction, track_info: dict, timeout=None
    ):
        super().__init__()
        container = discord.ui.Container()
        container.add_item(fmSection(track_info))
        # if interaction.guild:
        container.add_item(fmActionRow(track_info))
        self.add_item(container)


class lastfmMessageWithLogin(discord.ui.LayoutView):
    def __init__(self, message, **container_options):
        super().__init__()
        container = discord.ui.Container(**container_options)
        self.add_item(container)
        container.add_item(discord.ui.TextDisplay(message))
        container.add_item(lastfmAuthPromptActionRow())


class lastfmAuthPromptActionRow(discord.ui.ActionRow):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Login", style=discord.ButtonStyle.secondary)
    async def auth_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            view = lastfmAuthFinal(interaction)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"{type(e)}: {e}")


class lastfmLoggedOutError(discord.ui.LayoutView):
    def __init__(self):
        super().__init__()

        container = discord.ui.Container()
        container.add_item(
            discord.ui.TextDisplay("## Not logged in!\nAuthorize with the button below")
        )
        container.add_item(lastfmAuthPromptActionRow)
        self.add_item()


class lastfmAuthFinalActionRow(discord.ui.ActionRow):
    def __init__(self, interaction: discord.Interaction):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                label="Authenticate",
                url=f"https://www.last.fm/api/auth?api_key={os.environ['LASTFM_API_KEY']}&cb={os.environ['LASTFM_CALLBACK_URL']}?state={generate_full_state(interaction.user.id)}",
            )
        )


class lastfmAuthFinal(discord.ui.LayoutView):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=None)
        container = discord.ui.Container()
        container.add_item(
            discord.ui.TextDisplay(
                f"## last.fm authentication\npress the button below to safely authenticate with last.fm as {interaction.user.name}"
            )
        )
        container.add_item(lastfmAuthFinalActionRow(interaction))
        self.add_item(container)


def generate_full_state(user_id: int) -> str:
    hash = generate_state_hash(user_id, os.getenv("STATE_SALT"))
    id_enc = base64.b64encode(str(user_id).encode()).decode()
    return f"{id_enc}@{hash}"


def generate_state_hash(user_id: int, secret: str) -> str:
    user_bytes = str(user_id).encode()
    secret_bytes = secret.encode()
    digest = hmac.new(secret_bytes, user_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)[:12].decode()


class fm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = (
            "Use your Last.fm integration to check what you're listening to."
        )

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

    @commands.is_owner()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @lastfm.command(
        name="raw", description="view the raw data for your currently playing track"
    )
    async def fm_raw(self, ctx: commands.Context):
        with open("data/last.fm/users.json", "r") as f:
            data = json.load(f)
            username = (
                data.get(str(ctx.author.id), {}).get("session", {}).get("name", {})
            )

        track_info_raw = await self.fetch_now_playing(username, raw=True)
        track_info_raw = json.dumps(track_info_raw, indent=2)
        fields = [
            track_info_raw[i : i + 1000] for i in range(0, len(track_info_raw), 1000)
        ]

        e = discord.Embed(title="raw data", color=Color.accent_og)
        for i, field in enumerate(fields):
            e.add_field(
                name=f"part {i + 1}", value=f"```json\n{field}```", inline=False
            )

        e.set_footer(text=f"{len(track_info_raw)} characters")
        await ctx.reply(embed=e)

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
            async with aiofiles.open("data/last.fm/users.json", "r") as f:
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
                track_info = track_info_raw[0]
            # Create embed with track scrobble count
            # e = discord.Embed(
            #     description=f"## [{track_info['track']}]({track_info['url']})\n### by {track_info['artist']}, on {track_info['album']}\n{track_info['track_scrobble_count']} scrobbles • {track_info['scrobble_count']} total",
            #     color=Color.lblue,
            # )
            # e.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar.url)

            await ctx.reply(
                view=fmLayout(ctx.interaction, track_info), mention_author=False
            )
            # if ctx.guild is None:
            #     msg = await ctx.interaction.original_response()
            #     await msg.add_reaction("<:upvote:1388512426059759657>")
            #     await msg.add_reaction("<:downvote:1388512428484198482>")
        except FileNotFoundError:
            view = lastfmMessageWithLogin(
                "## Not logged in!\nPlease use the button below to authenticate with Last.fm"
            )
            await ctx.reply(view=view, ephemeral=True)
        except Exception as err:
            view = lastfmMessageWithLogin(
                f"## An error occured!\nPlease report this to the bot developers. you can also try authenticating again\n```{type(err).__name__}: {str(err)}```",
                accent_colour=Color.negative,
            )
            await ctx.reply(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(fm(bot))
