from main import *
import flask, base64, hmac

class lastfmAuthView(discord.ui.View):
    @discord.ui.button(label="Login", style=discord.ButtonStyle.primary)
    async def auth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = lastfmAuthFinal(interaction.user.id)
        e = discord.Embed(
            title="",
            description="## last.fm authentication\npress the button below to safely authenticate with last.fm",
            color=0xff0f77
        )
        await interaction.response.send_message(
            embed=e,
            view=view,
            ephemeral=True
        )
class lastfmAuthFinal(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="Authenticate",
                url=f"https://www.last.fm/api/auth?api_key={os.environ['LASTFM_API_KEY']}&cb={os.environ['LASTFM_CALLBACK_URL']}?state={generate_full_state(user_id)}"
            )
         )
def generate_full_state(user_id: int) -> str:
    hash = generate_state_hash(user_id, os.getenv("STATE_SALT"))
    id_enc = base64.b64encode(str(user_id).encode())
    return f"{id_enc}#{hash}"

def generate_state_hash(user_id: int, secret: str) -> str:
    user_bytes = str(user_id).encode()
    secret_bytes = secret.encode()
    digest = hmac.new(secret_bytes, user_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)[:12].decode()
import discord
import json
import requests
import os
from discord.ext import commands

class fm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Use your Last.fm integration to check what you're listening to."

    async def fetch_now_playing(self, username, raw:bool=False):
        """Fetches the currently playing track, scrobble count, and track play count for a Last.fm user."""
        api_key = os.environ["LASTFM_API_KEY"]
        base_url = "http://ws.audioscrobbler.com/2.0/"

        # Fetch recent tracks
        params_tracks = {
            "method": "user.getrecenttracks",
            "user": username,
            "api_key": api_key,
            "format": "json",
            "limit": 1
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
            "format": "json"
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
            "format": "json"
        }
        response_track_info = requests.get(base_url, params=params_track_info)
        data_track_info = response_track_info.json()

        if "error" in data_track_info:
            track_scrobble_count = "Unknown"
        else:
            track_scrobble_count = data_track_info.get("track", {}).get("userplaycount", "0")
        if raw:
            return data_track_info
        return {
            "artist": artist,
            "track": track_name,
            "album": album,
            "url": url,
            "now_playing": is_now_playing,
            "scrobble_count": scrobble_count,
            "track_scrobble_count": track_scrobble_count
        }, None

    @commands.hybrid_group(name="lastfm", description="all commands with the last.fm api.", with_app_command=True)
    async def lastfm(self, ctx):
        pass
    @commands.is_owner()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @lastfm.command(name="raw", description="view the raw data for your currently playing track")
    async def fm_raw(self, ctx):
        with open("data/last.fm/users.json", "r") as f:
            data = json.load(f)
            username = data.get(str(ctx.author.id), {}).get("session", {}).get("name", {})

        track_info_raw = await self.fetch_now_playing(username, raw=True)
        track_info_raw = json.dumps(track_info_raw, indent=2)
        fields = [track_info_raw[i:i+1000] for i in range(0, len(track_info_raw), 1000)]

        e = discord.Embed(title="raw data", color=0xff0000)
        for i, field in enumerate(fields):
            e.add_field(name=f"part {i+1}", value=f"```json\n{field}```", inline=False)

        e.set_footer(text=f"{len(track_info_raw)} characters")
        await ctx.reply(embed=e)
    @app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
    @app_commands.allowed_installs(guilds=True,users=True)
    @commands.hybrid_command(name="fm", description="see what you're listening to.", with_app_command=True)
    async def fm(self, ctx):
        try:
            with open("data/last.fm/users.json", "r") as f:
                data = json.load(f)
                username = data.get(str(ctx.author.id), {}).get("session",{}).get("name",{})
            track_info_raw = await self.fetch_now_playing(username)
            track_info = track_info_raw[0]
            # Create embed with track scrobble count
            e = discord.Embed(
                description=f"## [{track_info['track']}]({track_info['url']})\n### by {track_info['artist']}, on {track_info['album']}\n{track_info['track_scrobble_count']} scrobbles • {track_info['scrobble_count']} total",
                color=0x00ffbb
            )
            e.set_author(name=f"{ctx.author.name}",icon_url=ctx.author.avatar.url)

            await ctx.reply(embed=e)

        except Exception as err:
                if not username:
                    e = discord.Embed(
                        title="Not logged in!",
                        description="Please use the button below to authenticate with Last.fm",
                        color=0xff0000
                    )
                    view = lastfmAuthView(ctx.author.id)
                    await ctx.reply(embed=e, view=view, ephemeral=True)
                else:
                    e = discord.Embed(
                        title="An error has occured!",
                        description="Please report this to the bot developers. you can also try authenticating again",
                        color=0xff0000
                    ).add_field(
                        name=f"{type(err).__name__}",
                        value=str(err)
                    )
                    view = lastfmAuthView(ctx.author.id)
                    await ctx.reply(embed=e, view=view, ephemeral=True)
async def setup(bot):
    await bot.add_cog(fm(bot))
