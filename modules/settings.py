from discord.ext import commands
from discord import app_commands
from ext.ui_base import Message
import discord
from main import Color, get_prefix, setup_guild, logger
import aiosqlite

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


class InitHomeView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(
        label="Start", style=discord.ButtonStyle.green, custom_id="init_button"
    )
    async def init_button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="Access Denied",
                description="### You must have admin to run this, silly!",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        button.disabled = True
        button.style = discord.ButtonStyle.secondary
        button.label = "Please wait..."
        await interaction.edit_original_response(view=InitHomeView())
        logger.debug(f"starting initialization for guild {interaction.guild.id}")
        async for embed in setup_guild(interaction.guild, gtype=1):
            await interaction.followup.send(embeds=list(embed), ephemeral=True)


class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Settings commands to manage your bot instance."

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="settings", description="Settings commands to manage your bot instance."
    )
    async def settings(self, ctx: commands.Context):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(
        name="config", description="view the configuration for your server"
    )
    async def config(self, ctx: commands.Context):
        await ctx.reply(
            view=Message(
                "due to data system migration, server configurations are currently disabled."
            ),
            ephemeral=True,
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
                    "## A prefixed command won't work for this.\n### Please use the </settings init:1338195438494289964> command instead.",
                    ephemeral=True,
                )
                return
        embed = discord.Embed(
            title="",
            description="initializing temporarily disabled due to data system changes",
        )
        await ctx.reply(embed=embed, ephemeral=True)

    @commands.has_guild_permissions(administrator=True)
    @app_commands.describe(prefix="The new prefix to set")
    @settings.command(
        name="prefix", description="View the current prefix and change it."
    )
    async def prefix(self, ctx: commands.Context, prefix: str = None):
        old = await get_prefix(self.bot, ctx)
        con: aiosqlite.Connection = self.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        e = Message(
            "# prefix\n" f"the current prefix in this server is: `{old}`",
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


async def setup(bot):
    await bot.add_cog(settings(bot))
