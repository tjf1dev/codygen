from discord.ext import commands
from discord import app_commands
import discord
import psutil
import os
import time
import aiohttp
import ext
import sys
from datetime import timedelta
from main import logger, Color, verify, version, get_global_config
from ext.views import HelpHomeView
1

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
        client = self.bot
        e = discord.Embed(
            title=f"codygen v{version}",
            description="### hii :3 bot made by `tjf1`\nuse </help:1338168344506925108> for command list +more",
            color=Color.accent,
        )
        e.set_thumbnail(url=self.bot.user.avatar.url)
        e.add_field(
            name="ping", value=f"`{round(self.bot.latency * 1000)} ms`", inline=True
        )
        current_time = time.time()
        difference = int(round(current_time - self.bot.start_time))
        uptime = str(timedelta(seconds=difference))
        e.add_field(name="uptime", value=f"`{uptime}`", inline=True)
        process = psutil.Process(os.getpid())
        ram_usage = process.memory_info().rss / 1024**2
        total_memory = psutil.virtual_memory().total / 1024**2
        e.add_field(
            name="ram usage",
            value=f"`{ram_usage:.2f} MB / {total_memory:.2f} MB`",
            inline=True,
        )
        cpu_usage = psutil.cpu_percent(interval=1)
        e.add_field(name="cpu usage", value=f"`{cpu_usage}%`", inline=True)
        # nerdy ahh logic
        commands_list = [
            command.name
            for command in client.commands
            if not isinstance(command, commands.Group)
        ] + [
            command.name
            for command in client.tree.walk_commands()
            if not isinstance(command, commands.Group)
        ]
        for cog in client.cogs.values():
            for command in cog.get_commands():
                if not isinstance(command, commands.Group):
                    commands_list.append(command.name)
        for command in client.walk_commands():
            if not isinstance(command, commands.Group):
                commands_list.append(command.name)
            else:
                for subcommand in command.walk_commands():
                    commands_list.append(subcommand.name)
        e.add_field(
            name="commands",
            value=f"`codygen has {len(set(commands_list))} commands`",
            inline=True,
        )
        e.add_field(
            name="servers",
            value=f"`codygen is in {len(client.guilds)} servers.`",
            inline=True,
        )
        e.add_field(
            name="users", value=f"`serving {len(client.users)} users.`", inline=True
        )
        e.add_field(
            name="system info",
            value=f"`running discord.py {discord.__version__} on python {sys.version.split()[0]}`",
            inline=True,
        )
        e.add_field(
            name=f"shard id: {ctx.guild.shard_id}",
            value="\n".join([f"`shard {s}: {l*1000:.0f} ms`" for s, l in self.bot.latencies])
        )
        await ctx.reply(embed=e, ephemeral=False)

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
            raise ext.errors.MisconfigurationError(
                f"github: please make sure the value is in the format or AUTHOR/REPO, e.g tjf1dev/codygen, debug: {repo.split("/")}"
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
                        raise ext.errors.DefaultError(f"HTTP {res.status}: {text}")
                    data = await res.json()
            except aiohttp.ClientConnectionError as e:
                raise ext.errors.DefaultError(
                    f"connection closed while reading json: {e}"
                )
            except aiohttp.ContentTypeError:
                text = await res.text()
                raise ext.errors.DefaultError(f"response is not json: {text}")
            except Exception as e:
                raise ext.errors.DefaultError(f"unexpected error parsing json: {e}")
        await ctx.reply(view=ext.views.ChangelogLayout(self.bot, data))

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
            raise ext.errors.MisconfigurationError(
                f"github: please make sure the value is in the format or AUTHOR/REPO, e.g tjf1dev/codygen, debug: {repo.split("/")}"
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
                        raise ext.errors.DefaultError(f"HTTP {res.status}: {text}")
                    data = await res.json()
            except aiohttp.ClientConnectionError as e:
                raise ext.errors.DefaultError(
                    f"connection closed while reading json: {e}"
                )
            except aiohttp.ContentTypeError:
                text = await res.text()
                raise ext.errors.DefaultError(f"response is not json: {text}")
            except Exception as e:
                raise ext.errors.DefaultError(f"unexpected error parsing json: {e}")

        contributors = ""
        for c in data:
            co = c["contributions"]
            contributors += f"[`{c["login"]}`](<{c["html_url"]}>): {co} contribution{"s" if co > 1 else ""}\n"
        await ctx.reply(view=ext.views.AboutLayout(self.bot, contributors))


async def setup(bot):
    await bot.add_cog(codygen(bot))
