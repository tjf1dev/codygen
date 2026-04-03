from fastapi import FastAPI, Depends, Request, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi_discord import DiscordOAuthClient, RateLimited, Unauthorized, User, Guild
from fastapi_discord.models import GuildPreview
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from discord.ext import ipcx
from web.ipcxc import IPCXC
from typing import List
import logger
import os
import uvicorn
import json

with open("VERSION") as f:
    VERSION = f.read()
    f.close()
TESTING = VERSION.endswith("alpha")

_client: ipcx.Client
client: IPCXC


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    await discord.init()
    _client = ipcx.Client(secret_key=os.getenv("IPC_KEY"), port=25000)
    client = IPCXC(_client)
    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "https://codygen.tjf1.dev",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


discord = DiscordOAuthClient(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("DISCORD_REDIRECT_URI"),
    scopes=("identify", "email", "guilds"),
)


@app.get("/api/login")
def login():
    return RedirectResponse(discord.oauth_login_url)


@app.get(
    "/api/me",
    dependencies=[Depends(discord.requires_authorization)],
)
async def get_user(user: User = Depends(discord.user)):
    return user.model_dump()


@app.get(
    "/api/me/guilds",
    dependencies=[Depends(discord.requires_authorization)],
    response_model=List[GuildPreview],
)
async def get_guilds(guilds: List = Depends(discord.guilds)):
    return guilds


@app.get(
    "/api/guilds/shared",
    dependencies=[Depends(discord.requires_authorization)],
)
async def get_guilds_shared(
    user: User = Depends(discord.user), guilds: list[Guild] = Depends(discord.guilds)
):
    bot_guilds = await client.request("list_guilds")

    bot_guild_ids = [str(g["id"]) for g in bot_guilds.ipc_content]
    shared_guilds = []
    for guild in guilds:
        if guild.id in bot_guild_ids:
            data = json.loads(guild.model_dump_json())
            shared_guilds.append(data)
    return shared_guilds


@app.get(
    "/api/guilds/{guild_id}",
    dependencies=[Depends(discord.requires_authorization)],
)
async def get_guilds_id(
    guild_id: int,
    user: User = Depends(discord.user),
    guilds: list[Guild] = Depends(discord.guilds),
):
    data = await client.request(
        "get_guild",
        guild_id=guild_id,
        user_guilds=[json.loads(g.model_dump_json()) for g in guilds],
    )

    return data


@app.put(
    "/api/guilds/{guild_id}",
    dependencies=[Depends(discord.requires_authorization)],
)
async def put_guilds_id(
    request: Request,
    guild_id: int,
    user: User = Depends(discord.user),
    guilds: list[Guild] = Depends(discord.guilds),
):
    content = await request.json()
    data = await client.request(
        "put_guild",
        guild_id=guild_id,
        data=content,
        user_guilds=[json.loads(g.model_dump_json()) for g in guilds],
    )

    if data.ipc_content.get("error"):
        return JSONResponse(data, 400)
    return data


@app.get("/api/commands")
async def get_commands():
    return await client.request("commands")


@app.get("/api/modules")
async def get_modules():
    return await client.request("modules")


@app.exception_handler(RateLimited)
async def rate_limit_error_handler(_, e: RateLimited):
    return JSONResponse(
        {"error": "RateLimited", "retry": e.retry_after, "message": e.message},
        status_code=429,
    )


@app.exception_handler(Unauthorized)
async def unauthorized_error_handler(_, e: Unauthorized):
    return JSONResponse(
        {"error": "Unauthorized"},
        status_code=401,
    )


@app.get("/api/callback")
async def callback(code: str, response: Response):
    token, refresh_token = await discord.get_access_token(code)
    url = os.getenv("DASH_CALLBACK_URL") or ""
    response = RedirectResponse(url=url)
    response.set_cookie(
        key="access_token", value=token, httponly=False, samesite="lax", path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


@app.get("/api")
async def root():
    return {"version": VERSION}


@app.get("/api/stats")
async def stats():
    data = await client.request("stats")
    return data


def main():
    logger.info("starting api")
    uvicorn.run("web.web:app", port=8648, reload=TESTING)


if __name__ == "__main__":
    main()
