from discord.ext import commands
from discord import app_commands
import discord
import os
import aiohttp
from ext import errors, views
from main import logger, Color, verify, get_global_config
from ext.views import HelpHomeView, Ping


class codygen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "core codygen features"

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @verify()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="ping", description="shows how well is codygen doing!"
    )
    async def ping(self, ctx: commands.Context):
        await ctx.reply(view=Ping(self.bot), ephemeral=False)

    @verify()
    @commands.hybrid_command(
        name="help", description="shows useful info about the bot."
    )
    async def help(self, ctx: commands.Context):
        await self.bot.refresh_commands()
        await ctx.reply(view=HelpHomeView(self.bot), ephemeral=True)

    @verify()
    @commands.hybrid_command(
        name="add", description="lets you add codygen to your server or profile"
    )
    async def add(self, ctx: commands.Context):
        bid = os.getenv("CLIENT_ID")
        guild = (
            f"https://discord.com/oauth2/authorize?client_id={bid}&integration_type=0"
        )
        user = (
            f"https://discord.com/oauth2/authorize?client_id={bid}&integration_type=1"
        )
        e = discord.Embed(
            description="# add codygen\n"
            f"## [server]({guild})\n"
            "use the link above to invite codygen to your server.\n"
            f"## [user install]({user})\n"
            "use this link to install codygen to your profile. you will be able to use it's commands anywhere\n\n"
            f"-# [about codygen](https://github.com/tjf1dev/codygen)",
            color=Color.accent,
        )
        await ctx.reply(embed=e, ephemeral=False)

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="changelog",
        description="view recent updates to codygen",
    )
    async def changelog(self, ctx: commands.Context):
        repo: str = get_global_config().get("github", "")
        if not len(repo.split("/")) == 2:
            raise errors.MisconfigurationError(
                f"github: please make sure the value is in the format or AUTHOR/REPO, e.g tjf1dev/codygen, debug: {repo.split('/')}"
            )
        api_url = f"https://api.github.com/repos/{repo}/commits"
        if self.bot.version.endswith("alpha"):
            api_url += "?sha=alpha"
        headers = {}
        token = os.getenv("GITHUB_PAT")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=headers) as res:
                    if res.status != 200:
                        text = await res.text()
                        raise errors.DefaultError(f"HTTP {res.status}: {text}")
                    data = await res.json()
            except aiohttp.ClientConnectionError as e:
                raise errors.DefaultError(f"connection closed while reading json: {e}")
            except aiohttp.ContentTypeError:
                raise errors.DefaultError("response is not json")
            except Exception as e:
                raise errors.DefaultError(f"unexpected error parsing json: {e}")
        await ctx.reply(view=views.ChangelogLayout(self.bot, data))

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="about",
        description="view detailed information about codygen, including contributors, etc.",
    )
    async def about(self, ctx: commands.Context):
        repo: str = get_global_config().get("github", "")
        if not repo:
            logger.warning(
                "github repository path has changed from commands.about.repo to github (at root of config). please update this, the old functionality will be removed in a future update"
            )
            repo: str = get_global_config()["commands"].get("about", {"repo": ""})[
                "repo"
            ]
        if not len(repo.split("/")) == 2:
            raise errors.MisconfigurationError(
                f"github: please make sure the value is in the format or AUTHOR/REPO, e.g tjf1dev/codygen, debug: {repo.split('/')}"
            )
        api_url = f"https://api.github.com/repos/{repo}/contributors"
        headers = {}
        token = os.getenv("GITHUB_PAT")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=headers) as res:
                    if res.status != 200:
                        text = await res.text()
                        raise errors.DefaultError(f"HTTP {res.status}: {text}")
                    data = await res.json()
            except aiohttp.ClientConnectionError as e:
                raise errors.DefaultError(f"connection closed while reading json: {e}")
            except aiohttp.ContentTypeError:
                raise errors.DefaultError("response is not json")
            except Exception as e:
                raise errors.DefaultError(f"unexpected error parsing json: {e}")

        contributors = ""
        for c in data:
            co = c["contributions"]
            contributors += f"[`{c['login']}`](<{c['html_url']}>): {co} contribution{'s' if co > 1 else ''}\n"
        await ctx.reply(view=views.AboutLayout(self.bot, contributors))


async def setup(bot):
    await bot.add_cog(codygen(bot))
