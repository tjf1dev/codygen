from discord.ext import commands
from discord import app_commands
from ext.ui_base import Message
import discord
from main import Color, get_prefix, logger
import aiosqlite
import json
from views import InitStartLayout, SettingsModulesLayout
from PIL import Image
from io import BytesIO
from ext import errors
from ext.utils import setup_guild

# enabling this allows using a prefixed command for /settings init
no_app_force = False


def recursive_update(original: dict, template: dict) -> dict:
    """Recursively update a dictionary with missing keys from a template."""
    for key, value in template.items():
        if isinstance(value, dict):
            original[key] = recursive_update(original.get(key, {}), value)
        else:
            original.setdefault(key, value)
    return original


class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "settings to manage your bot instance."

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="settings", description="settings to manage your bot instance."
    )
    async def settings(self, ctx: commands.Context):
        pass

    @app_commands.allowed_contexts(True, False, False)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @settings.group(name="modules", description="manage the server's modules")
    async def modules(self, ctx: commands.Context):
        if not ctx.guild:
            return
        db: aiosqlite.Connection = self.bot.db
        msg = await ctx.reply(
            view=Message(f"{ctx.bot.emote('loading')} loading modules..."),
            ephemeral=True,
        )
        res = await (
            await db.execute(
                "SELECT module_settings FROM guilds WHERE guild_id=?", (ctx.guild.id,)
            )
        ).fetchone()
        if not res:
            raise errors.CodygenError("module data uninitialized. try again")
        settings = json.loads(res[0])
        await msg.edit(
            view=SettingsModulesLayout(self.bot, settings, ctx.author.id), content=""
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(
        name="init",
        description="Check if the bot has valid permissions and create a config.",
    )
    async def init(self, ctx: commands.Context):
        # no_app_force = True
        if not ctx.interaction:
            if not no_app_force:
                await ctx.reply(
                    "## a prefixed command won't work for this.\n### please use the </settings init:1338195438494289964> command instead.",
                    ephemeral=True,
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
            view=InitStartLayout(self),
            ephemeral=True,
            file=await prepare_header_image("assets/images/bannername.png"),
        )

    @commands.has_guild_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(prefix="The new prefix to set")
    @settings.command(
        name="prefix", description="view the current prefix and change it."
    )
    async def prefix(self, ctx: commands.Context, prefix: str | None = None):
        if not ctx.guild:
            return
        old = await get_prefix(self.bot, ctx.message)
        con: aiosqlite.Connection = self.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        e = Message(
            f"# prefix\nthe current prefix in this server is: `{old}`",
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
        if cur.rowcount == 0:
            return

        await con.commit()
        await ctx.reply(view=e2)

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
