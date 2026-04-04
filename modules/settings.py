from discord.ext import commands
from discord import app_commands
from ext.ui_base import Message
import discord
from main import Color, get_prefix, logger
import aiosqlite
import json
from typing import cast
from models import Codygen
from views import InitStartLayout, SettingsModulesLayout
from PIL import Image
from io import BytesIO
from ext.utils import setup_guild
from ext.commands import parse_commands
from models import Module
from ext.config import DEFAULT_MODULE_STATE


def recursive_update(original: dict, template: dict) -> dict:
    """Recursively update a dictionary with missing keys from a template."""
    for key, value in template.items():
        if isinstance(value, dict):
            original[key] = recursive_update(original.get(key, {}), value)
        else:
            original.setdefault(key, value)
    return original


class settings(Module):
    def __init__(self, bot, **kwargs):
        super().__init__(hidden=False, default=True, **kwargs)
        self.bot = cast(Codygen, bot)
        self.description = "settings to manage your bot instance."
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="settings",
        description="settings to manage your bot instance.",
        with_app_command=True,
    )
    async def settings(self, ctx: commands.Context):
        pass

    @app_commands.allowed_contexts(True, False, False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @settings.command(name="modules", description="manage the server's modules")
    async def modules(self, ctx: commands.Context):
        if not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        msg = await ctx.reply(
            view=Message(f"{ctx.bot.emote('loading')} loading modules..."),
            ephemeral=True,
        )

        global_modules_res = await (
            await db.execute("SELECT name FROM pragma_table_info('modules');")
        ).fetchall()
        global_module_names = [
            m["name"] for m in global_modules_res if m["name"] != "guild_id"
        ]
        global_modules = [ctx.bot.get_cog(m) for m in global_module_names]

        # this gets the currently enabled modules for that guild
        res = await (
            await db.execute("SELECT * FROM modules WHERE guild_id=?", (ctx.guild.id,))
        ).fetchone()
        if not res:
            settings = {}
            for module in global_modules:
                module = cast(Module, module)
                if module.hidden is True:
                    continue
                settings[module.__cog_name__] = module.default
        else:
            settings = {}
            for module in global_modules:
                module = cast(Module, module)
                if module.hidden is True:
                    continue

                settings[module.__cog_name__] = bool(res[module.__cog_name__])

        logger.debug(res)
        await msg.edit(
            view=SettingsModulesLayout(self.bot, settings, ctx.author.id), content=""
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(
        name="init",
        description="check if the bot has valid permissions and create a config.",
    )
    async def init(self, ctx: commands.Context):
        if not ctx.interaction and self.bot.release:
            commands = parse_commands(self.bot.full_commands)
            init_command_id = next(
                (m["id"] for m in commands if m["full_name"] == "settings init"), 0
            )
            await ctx.reply(
                view=Message(
                    f"## a prefixed command won't work for this.\nplease use the </settings init:{init_command_id}> command instead."
                )
            )
            return

        async def prepare_header_image(path: str):
            with Image.open(path) as img:
                new_size = (round(img.width / 2), round(img.height / 2))
                img = img.resize(new_size)
                byte_io = BytesIO()
                img.save(byte_io, format="PNG")
                byte_io.seek(0)
                return discord.File(byte_io, filename="header.png")

        await ctx.reply(
            view=InitStartLayout(self, self.bot),
            ephemeral=True,
            file=await prepare_header_image("assets/images/bannername.png"),
        )

    @commands.has_guild_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(prefix="The new prefix to set")
    @settings.command(
        name="prefix",
        description="view the current prefix and change it.",
    )
    async def prefix(self, ctx: commands.Context, prefix: str | None = None):
        if not ctx.guild:
            return
        old = await get_prefix(self.bot, ctx.message)
        con: aiosqlite.Connection = self.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        e = Message(
            f"# prefix\n{f'the current prefix in this server is: `{old}`' if old else 'there is no prefix set.'}",
            accent_color=Color.white,
        )
        e2 = Message(
            f"# prefix\nprefix updated to: `{prefix}`",
            accent_color=Color.positive,
        )

        if not prefix:
            await ctx.reply(view=e, mention_author=False)
            return

        await cur.execute(
            "UPDATE guilds SET prefix = ? WHERE guild_id = ?", (prefix, ctx.guild.id)
        )
        await cur.execute(
            "UPDATE guilds SET prefix_enabled = 1 WHERE guild_id = ?",
            (ctx.guild.id,),
        )
        await con.commit()
        await ctx.reply(view=e2)

    @commands.has_guild_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @settings.command(name="remove_prefix", description="remove the current prefix")
    async def remove_prefix(self, ctx: commands.Context):
        if not ctx.guild:
            return
        await self.bot.db.execute(
            "UPDATE guilds SET prefix_enabled = 0 WHERE guild_id = ?",
            (ctx.guild.id,),
        )
        await self.bot.db.commit()
        await ctx.reply(
            view=Message(
                "# prefix successfully disabled.\n- use /settings prefix to enable it again"
            )
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        owner = guild.owner
        if not owner:
            return
        try:
            gen = setup_guild(self.bot, guild, gtype=2)
            async for view in gen:
                await owner.send(view=view)
        except Exception as e:
            logger.error(f"An error occurred while trying to setup {guild.name}: {e}")


async def setup(bot):
    await bot.add_cog(settings(bot))
