import quart
import os
import aiofiles
import aiohttp
import hashlib
import base64
import json
from quart import render_template

from ext.logger import logger

# import ext.errors
from main import ensure_env

app = "codygen"


def state_to_id(state: str) -> str:
    euid = state.split("@")[0]
    return base64.b64decode(euid).decode()


app = quart.Quart("codygen")


@app.route("/callback")
async def callback():
    try:
        logger.debug("received callback")
        token = quart.request.args.get("token")
        state = quart.request.args.get("state")
        uid = state_to_id(state)
        try:
            api_key = os.environ["LASTFM_API_KEY"]
            secret = os.environ["LASTFM_SECRET"]
        except KeyError:
            # raise ext.errors.MisconfigurationError(f"Misconfiguration of last.fm application configuration fields in .env file: LASTFM_SECRET and/or LASTFM_API_KEY")
            logger.error(
                f"Misconfiguration of last.fm application configuration fields in .env file: LASTFM_SECRET and/or LASTFM_API_KEY"
            )
            output = {
                "error": "Misconfigured bot configuration",
                "details": ".env file appears to have missing LASTFM_SECRET and/or LASTFM_API_KEY, contact the bot administrator for more details.",
            }
            return output
        if not token or not uid:
            return {
                "error": "Missing parameters",
                "details": "Token or state is missing",
            }
        params = {"api_key": api_key, "method": "auth.getSession", "token": token}
        sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
        sig_string = sorted_params + secret
        api_sig = hashlib.md5(sig_string.encode("utf-8")).hexdigest()
        url = "http://ws.audioscrobbler.com/2.0/"
        params.update({"api_sig": api_sig, "format": "json"})

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
        logger.info(f"{uid}'s data is {data}")
        try:
            async with aiofiles.open("data/last.fm/users.json", "r") as f:
                content = await f.read()
                json_data = json.loads(content)
            json_data[uid] = data
            async with aiofiles.open("data/last.fm/users.json", "w") as f:
                await f.write(json.dumps(json_data, indent=4))
        except Exception as e:
            logger.error(f"An error occured while trying to authenticate {uid}: {e}")

        if "session" in data:
            return await render_template("success.html")
        else:
            logger.error(f"Session key missing: {data}")
            return {"error": "Session key missing", "details": str(data)}
    except Exception as e:
        return {
            "error": "An internal error occured",
            "code": "500",
            "type": str(type(e)),
            "content": e,
        }


@app.route("/invite")
async def invite():
    bid = os.getenv("APP_ID")
    url = f"https://discord.com/oauth2/authorize?client_id={bid}&permissions=8&scope=applications.commands+bot"
    return quart.redirect(url)


@app.route("/")
async def root():
    return {"status": "codygen is online"}


ensure_env()
app.run(port=os.getenv("WEB_PORT"))
