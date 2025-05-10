from main import *
import json
import os
import discord
from discord.ext import commands
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


    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="init_button")
    async def init_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="Access Denied",
                description="### You must have admin to run this, silly!",
                color=discord.Color.red()
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


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Settings commands to manage your bot instance."

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(name="settings", description="Settings commands to manage your bot instance.")
    async def settings(self, ctx: commands.Context):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="config", description="View the configuration for your guild")
    async def config(self, ctx: commands.Context):
        config = await get_guild_config(ctx.guild.id)
        path = f"data/guilds/{ctx.guild.id}.json"
        config_patched = {k: v for k, v in config.items() if k != "stats"}
        formatted_config = json.dumps(config_patched, indent=4)

        embed = discord.Embed(
            title="codygen's config",
            description=(
                f"path to your config file: `{path}`\n"
                f"current config: ```json\n{formatted_config}```\nmodify it using commands in /settings."
            ),
            color=Color.white
        )
        await ctx.reply(embed=embed, ephemeral=True)

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="init", description="Check if the bot has valid permissions and create a config.")
    async def init(self, ctx: commands.Context):
        # no_app_force = True
        if not ctx.interaction:
            if not no_app_force:
                await ctx.reply(
                    "## A prefixed command won't work for this.\n### Please use the </settings init:1338195438494289964> command instead.",
                    ephemeral=True
                )
                return
        embed = discord.Embed(
            title="",
            description="-# press the button below to start initialization."
        )
        await ctx.reply(embed=embed, ephemeral=True, view=InitHomeView())
    @commands.has_guild_permissions(administrator=True)
    @app_commands.describe(prefix="The new prefix to set")
    @settings.command(name="prefix", description="View the current prefix and change it.")
    async def prefix(self, ctx: commands.Context, prefix: str = None):
        old = await get_prefix(self.bot, ctx)
        
        e = discord.Embed(title="", description="# prefix\n" f"the current prefix in this server is: `{old}`", color=Color.white)
        fail = discord.Embed(title="", description="## something went wrong\ncodygen couldn't change your prefix. try again or contact us", color=Color.negative)
        e2 = discord.Embed(title="", description=f"# prefix\nprefix updated to: `{prefix}`", color=Color.positive)
        
        if not prefix:
            await ctx.reply(embed=e, mention_author=False)
            return
        
        c = await set_guild_config_key(ctx.guild.id, "prefix.prefix", prefix)
        
        if not c:
            await ctx.reply(embed=fail, mention_author=False)
            return
        await ctx.reply(embed=e2)
        
            
async def setup(bot):
    await bot.add_cog(Settings(bot))

