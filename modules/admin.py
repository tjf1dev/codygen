import discord
import asyncio
from discord.ext import commands
from main import (
    logger,
    version,
)
import aiofiles
from ext.ui_base import Message
from models import Codygen
from typing import cast


class admin(commands.Cog):
    def __init__(self, bot):
        self.bot = cast(Codygen, bot)  # pyright: ignore[reportAttributeAccessIssue]
        self.description = "commands for bot administrators. for development purposes"
        self.allowed_contexts = discord.app_commands.allowed_contexts(True, True, True)

    # * THE FOLLOWING GROUP DOESNT HAVE A SLASH COMMAND AND ITS ON PURPOSE!!
    @commands.is_owner()
    @commands.group(
        name="admin",
        description="commands for bot administrators. for development purposes",
        invoke_without_command=True,
        aliases=["a"],
    )
    async def admin(self, ctx: commands.Context):
        pass

    async def cog_load(self):
        logger.ok("loaded admin")
        version = self.bot.version  # type:ignore
        activity = discord.Activity(
            type=discord.ActivityType.watching, name=f"v{version}"
        )
        self.bot: Codygen
        await self.bot.change_presence(activity=activity, status=discord.Status.idle)

    async def manage_modules(self, modules: str, action: str) -> list[str]:
        selected = modules.split()
        success = []
        data = list(self.bot.cogs.keys())
        if modules == "*":
            for cog in data:
                ext_name = "modules" + "." + cog
                try:
                    if action == "reload":
                        await self.bot.unload_extension(ext_name)
                        await self.bot.load_extension(ext_name)
                    elif action == "load":
                        await self.bot.load_extension(ext_name)
                    elif action == "unload":
                        await self.bot.unload_extension(ext_name)
                    else:
                        continue
                    success.append(ext_name)
                except Exception:
                    continue
            return success
        for cog in selected:
            try:
                split = cog.split(".")
                prefix = split[0] if len(split) > 1 else "modules"
                ext_name = f"{prefix}.{cog}"

                if action == "reload":
                    await self.bot.unload_extension(ext_name)
                    await self.bot.load_extension(ext_name)
                elif action == "load":
                    await self.bot.load_extension(ext_name)
                elif action == "unload":
                    await self.bot.unload_extension(ext_name)
                else:
                    continue

                success.append(ext_name)
            except Exception:
                continue

        return success

    @commands.is_owner()
    @admin.group(name="status")
    async def status(self, ctx: commands.Context):
        pass

    @admin.command(
        name="list", description="lists the current loaded modules.", aliases=["ls"]
    )
    @commands.is_owner()
    async def admin_modules_list(self, ctx: commands.Context):
        cogs = self.bot.cogs
        out = ""
        out += f"## {len(cogs)} loaded modules\n"
        for name, cog in cogs.items():
            out += f"**{name}** {cog.description or 'no description provided.'}\n"
        await ctx.reply(view=Message(out))

    @admin.command(name="reload", aliases=["r"])
    @commands.is_owner()
    async def admin_modules_reload(self, ctx: commands.Context, *, modules: str):
        success = await self.manage_modules(modules, "reload")
        out = f"### {'✅ ' if len(success) > 0 else ''}{len(success)} module{'s' if len(success) != 1 else ''} reloaded\n"
        for cog in success:
            out += f"`{cog}`\n"
        await ctx.reply(view=Message(out))

    @admin.command(name="load", aliases=["l"])
    @commands.is_owner()
    async def admin_modules_load(self, ctx: commands.Context, *, modules: str):
        success = await self.manage_modules(modules, "load")
        out = f"### {'✅ ' if len(success) > 0 else ''}{len(success)} module{'s' if len(success) != 1 else ''} loaded\n"
        for cog in success:
            out += f"`{cog}`\n"
        await ctx.reply(view=Message(out))

    @admin.command(name="unload", aliases=["u"])
    @commands.is_owner()
    async def admin_modules_unload(self, ctx: commands.Context, *, modules: str):
        success = await self.manage_modules(modules, "unload")
        out = f"### {'✅ ' if len(success) > 0 else ''}{len(success)} module{'s' if len(success) != 1 else ''} unloaded\n"
        for cog in success:
            out += f"`{cog}`\n"
        await ctx.reply(view=Message(out))

    @commands.is_owner()
    @admin.command(name="checkpoint", description="makes a WAL checkpoint")
    async def checkpoint(self, ctx: commands.Context):
        db = self.bot.db
        await db.execute("PRAGMA wal_checkpoint(FULL);")
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @status.command(
        name="reset", description="set the status to default (version display)"
    )
    async def admin_status_refresh(self, ctx: commands.Context):
        activity = discord.Activity(
            type=discord.ActivityType.watching, name=f"v{version}"
        )
        self.bot: Codygen
        await self.bot.change_presence(activity=activity, status=discord.Status.idle)
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @admin.command(
        name="update",
        description="refreshes the version. use after updates in development",
    )
    async def update(self, ctx: commands.Context):
        self.bot: Codygen
        file = await aiofiles.open("VERSION")
        before = self.bot.version  # noqa: F841
        self.bot.version = await file.read()
        activity = discord.Activity(
            type=discord.ActivityType.watching, name=f"v{self.bot.version}"
        )
        await self.bot.change_presence(activity=activity, status=discord.Status.idle)
        await ctx.reply(
            view=Message(
                f"running {f'~~v{before}~~ ' if before != self.bot.version else ''}v{self.bot.version} {'(unchanged)' if before == self.bot.version else ''}"
            )
        )

    @commands.is_owner()
    @status.command(name="set", description="set the bot's status")
    async def set(
        self,
        ctx: commands.Context,
        content: str,
        type: int | discord.ActivityType = 0,
        status: int | discord.Status = 0,
    ):
        if content == "?":
            await ctx.reply(
                view=Message(
                    "usage: admin status set <content> [type] [status]\n- type:\n  - 0 (default) - playing\n  - 1 - listening\n  - 2 - watching\n- status:\n  - 0 (default) - online\n  - 1 - dnd\n  - 2 - idle\n  - 3 - offline"
                )
            )
            return
        if type == 1:
            type = discord.ActivityType.listening
        if type == 2:
            type = discord.ActivityType.watching
        else:
            type = discord.ActivityType.playing

        if status == 1:
            status = discord.Status.dnd
        if status == 2:
            status = discord.Status.idle
        if status == 3:
            status = discord.Status.invisible
        else:
            status = discord.Status.online
        activity = discord.Activity(type=type, name=content)
        await self.bot.change_presence(activity=activity, status=status)
        await ctx.message.add_reaction("✅")

    @commands.is_owner()
    @admin.command(
        name="restart", description="fully restarts every instance of the bot"
    )
    async def restart(self, ctx: commands.Context):
        await ctx.message.add_reaction("➡️")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "➡️"
                and reaction.message.id == ctx.message.id
            )

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=5.0, check=check
            )
        except asyncio.TimeoutError:
            await ctx.reply("-# timed out")
        else:
            await ctx.reply("-# restarting...")
            exit()

    # @commands.is_owner()
    # @admin.command(
    #     name="git_update",
    #     description="Attempt to automatically update codygen through git.",
    # )
    # async def git_update(self, ctx: commands.Context, version: str | None = None):
    #     try:
    #         logger.info(f"Attempting to update codygen to version: {version}")
    #         git_command = ["git", "pull"]
    #         result = subprocess.run(
    #             git_command, capture_output=True, text=True, check=True
    #         )
    #         uptodate = discord.Embed(
    #             description="codygen is already up to date.", color=Color.white
    #         )
    #         e = discord.Embed(
    #             description="codygen successfully updated.\nrestart now to apply changes.",
    #             color=Color.positive,
    #         )
    #         if result.stdout.strip() == "Already up to date.":
    #             embed = uptodate
    #             content = None
    #         else:
    #             embed = e
    #             content = f"```{result.stdout}```"
    #         if version:
    #             async with aiofiles.open("config.json", "r") as f:
    #                 data = json.loads(await f.read())
    #                 data["version"] = version
    #             async with aiofiles.open("config.json", "w") as f:
    #                 await f.write(json.dumps(data, indent=4))
    #         await ctx.reply(content, embed=embed)

    #     except subprocess.CalledProcessError as e:
    #         await ctx.reply(f"```{e.stderr}```")


async def setup(bot):
    await bot.add_cog(admin(bot))
