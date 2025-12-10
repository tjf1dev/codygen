import discord
from discord.ext import commands
from discord import app_commands
from main import logger, Color
from models import Cog


class moderation(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands to help you manage your community."
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="moderation", description="commands to help you manage your community."
    )
    async def moderation(self, ctx: commands.Context): ...

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    # @commands.command(name="bans", description="view the server's banned people")

    @commands.hybrid_command(name="bans", description="view the server's banned people")
    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    async def moderation_bans(self, ctx: commands.Context):
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return
        bans = [entry async for entry in ctx.guild.bans()]
        if len(bans) == 1:
            msg = f"is {len(bans)} person"
        else:
            msg = f"are {len(bans)} people"
        e = discord.Embed(
            title=f"there {msg} banned in {ctx.guild.name}", color=Color.negative
        )
        if len(bans) == 0:
            e.description = "no one is banned in this server"
        for ban in bans:
            e.add_field(
                name=f"{ban.user} ({ban.user.id})",
                value=f"```{ban.reason}```",
                inline=False,
            )

        await ctx.reply(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(moderation(bot))
