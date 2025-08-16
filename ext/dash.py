import quart
from quart import redirect, url_for, request
from quartcord import DiscordOAuth2Session, requires_authorization, Unauthorized
from discord.ext import ipcx
from logger import logger
import os
import time
import asyncio
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart_cors import cors
import functools

__import__("dotenv").load_dotenv()

secret = os.getenv("IPC_KEY")
if not secret:
    logger.error("no secret key found")
logger.debug(secret)
ipc = ipcx.Client(secret_key=secret, port=20001)

app = quart.Quart("codygen")
app = cors(
    app,
    allow_origin=["https://codygen.tjf1.dev", "https://codygenapi.tjf1.dev"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*", "GET", "POST", "PUT"],
)

app.secret_key = os.getenv("DASH_SALT")
app.config["DISCORD_CLIENT_ID"] = os.getenv("CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

discord = DiscordOAuth2Session(app, bot_token=os.getenv("CLIENT_TOKEN"))


@app.errorhandler(404)
def page_not_found(e):
    return quart.jsonify({"error": "page not found"}), 404


@app.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    return {"error": "unauthorized"}, 401


@app.before_request
async def log_request():
    request._start_time = time.monotonic()


@app.after_request
async def req(response):
    duration = time.monotonic() - request._start_time
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    method = request.method
    path = request.path
    status = response.status_code
    size = response.content_length or 0
    logger.info(f"{ip} {method} {path} {status} ({size} {duration:.4f}s)")
    return response


@app.route("/login", methods=["GET"])
async def login():
    return await discord.create_session(scope=["guilds email identify"])


@app.route("/callback", methods=["GET"])
async def callback():
    try:
        token = await discord.callback()
        response = redirect("https://codygen.tjf1.dev/dash")
        import json

        response.set_cookie(
            "discord_token",
            json.dumps(token),
            httponly=True,
            secure=True,
            samesite="Lax",
            domain="tjf1.dev",
        )
        return response
    except Exception as e:
        logger.error(f"error during oauth callback: {str(e)}")
        return "failed"


class TTLCache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.cache = {}

    def get(self, key):
        value, timestamp = self.cache.get(key, (None, 0))
        if time.monotonic() - timestamp < self.ttl:
            return value
        self.cache.pop(key, None)
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.monotonic())


# Define cache
guilds_cache = TTLCache(ttl=120)
shared_guilds_cache = TTLCache(ttl=120)
all_shared_cache = TTLCache(ttl=120)
commands_cache = TTLCache(ttl=120)
channels_cache = TTLCache(ttl=120)

# Generic decorator


def cache_response(cache, key_func):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs)
            cached = cache.get(key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator


@app.route("/api/commands", methods=["GET"])
@cache_response(commands_cache, lambda: "commands")
async def get_commands():
    res = await ipc.request("commands")
    if not res:
        return {"error": "unknown error occured"}, 500
    return res


@requires_authorization
@app.route("/api/me", methods=["GET"])
async def me():
    user = await discord.fetch_user()
    return user.to_json()


@requires_authorization
@app.route("/api/me/guilds", methods=["GET"])
@cache_response(guilds_cache, lambda: getattr(quart.g, "user_id", None))
async def me_guilds():
    _user = await discord.fetch_user()
    quart.g.user_id = _user.id
    guilds = await _user.get_guilds()
    return [g.to_json() for g in guilds]


@requires_authorization
@app.route("/api/me/guilds/shared", methods=["GET"])
@cache_response(shared_guilds_cache, lambda: getattr(quart.g, "user_id", None))
async def shared_guilds():
    _user = await discord.fetch_user()
    quart.g.user_id = _user.id
    guilds = await _user.get_guilds()
    user = [guild.id for guild in guilds]
    shared = await ipc.request("shared_guilds", user=user)
    if not shared:
        return quart.Response(
            quart.jsonify({"error": "internal error in IPC"}), status=500
        )
    return shared


@requires_authorization
@app.route("/api/me/guilds/all_shared", methods=["GET"])
@cache_response(all_shared_cache, lambda: getattr(quart.g, "user_id", None))
async def all_guilds_with_shared():
    _user = await discord.fetch_user()
    quart.g.user_id = _user.id
    guilds = await _user.get_guilds()
    user_guild_ids = {guild.id for guild in guilds}
    shared = await ipc.request("shared_guilds", user=list(user_guild_ids))
    shared_ids = {
        str(g["id"]) if isinstance(g, dict) and "id" in g else g for g in (shared or [])
    }
    result = []
    for guild in guilds:
        data = guild.to_json()
        data["shared"] = str(guild.id) in shared_ids
        result.append(data)
    return result


@requires_authorization
@app.route("/api/me/guilds/<int:guild>", methods=["GET"])
async def get_guild(guild: int):
    _user = await discord.fetch_user()
    guilds = await _user.get_guilds()
    user = [g.to_json() for g in guilds]
    res = await ipc.request("get_guild", guild_id=guild, user_guilds=user)
    res["config"]["levelup_channel"] = str(res["config"]["levelup_channel"])
    if not res:
        return {"error": "guild not found"}, 404
    return res


@requires_authorization
@app.route("/api/me/guilds/<int:guild>/channels", methods=["GET"])
@cache_response(channels_cache, lambda guild: f"channels:{guild}")
async def get_guild_channels(guild: int):
    _user = await discord.fetch_user()
    guilds = await _user.get_guilds()
    user = [g.to_json() for g in guilds]
    res = await ipc.request("get_channels", guild_id=guild, user_guilds=user)
    if isinstance(res, dict):
        if res.get("error"):
            return res, 401
    if not res:
        return {"error": "guild not found"}, 404
    return res


@requires_authorization
@app.route("/api/me/guilds/<int:guild>", methods=["PUT"])
async def put_guild(guild: int):
    data = await quart.request.json
    _user = await discord.fetch_user()
    guilds = await _user.get_guilds()
    user = [g.to_json() for g in guilds]
    res = await ipc.request("put_guild", guild_id=guild, user_guilds=user, data=data)
    if not res:
        return {"error": "guild not found"}, 404
    return res


@app.route("/invite", methods=["GET"])
async def invite():
    data = request.args
    link = await ipc.request("add_bot")
    if data.get("guild"):
        link += (
            f"&guild_id={data['guild']}&scope=bot applications.commands&permissions=8"
        )
    return redirect(link)


config = Config()
# config.bind = ["0.0.0.0:8998"]
config.bind = ["127.0.0.1:8998"]
config.access_log_format = ""
config.forwarded_allow_ips = "127.0.0.1"
config.debug = True


@app.route("/stats", methods=["GET"])
async def stats():
    data = await ipc.request("stats")
    return data


async def main():
    await serve(app, config)


asyncio.run(main())
