from main import *
import json


class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description="settings commands to manage your bot instance."

    @commands.hybrid_group(name="settings", description="settings commands to manage your bot instance.")
    async def settings(self,ctx):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="config",description="change the configs for your guild. usage: settings config <key> <value>")
    async def config(self,ctx, key, value):
        set_value_from_guild_config(ctx.guild.id, key, value)
        e = discord.Embed(
            title="config changed successfully",
            color=0x00ff00
        ).add_field(
            name=f"{key}",
            value=f"```{value}```"
        )
        await ctx.reply(embed=e)

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="viewconfig",description="view the configs for your guild.")
    async def viewconfig(self,ctx):
        e = discord.Embed(
            title=f"config for {ctx.guild.name}",
            color=0x00ff00
        )
        for key in get_guild_config(ctx.guild.id):
            e.add_field(
                name=f"{key}",
                value=f"```json\n{get_value_from_guild_config(ctx.guild.id, key)}```",inline=False
            )
        await ctx.reply(embed=e,ephemeral=True)
            

async def setup(bot):
    await bot.add_cog(settings(bot))