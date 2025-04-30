from main import *
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta

class utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "tools that can be helpful sometimes!"

    @tasks.loop(hours=24)
    async def countdown_loop(self):
        target_date = datetime(datetime.now().year, 6, 5)
        channel = self.bot.get_channel(1333785292351606830)
        now = datetime.now()
        if now > target_date:
            await channel.send("deltarune tomorrow :3 (it's out)")
            self.countdown_loop.stop()
        else:
            days_left = (target_date - now).days
            if days_left == 1:
                await channel.send("deltarune tomorrow")
            else:
                await channel.send(f"{days_left} days until deltarune")

    @countdown_loop.before_loop
    async def before_countdown(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds_until_midnight = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.countdown_loop.is_running():
            self.countdown_loop.start()
        logger.info(f"{self.__class__.__name__}: loaded.")

    @commands.hybrid_group(name="utility", description="tools that can be helpful sometimes!")
    async def utility(self, ctx):
        await ctx.reply("utility")

    @utility.command(name="pfp", description="get someone's pfp")
    async def pfp(self, ctx, user: discord.User = None):
        if user is None:
            user = ctx.author
        avatar = user.avatar.url
        embed = discord.Embed(color=0x8ff0a4)
        embed.set_image(url=avatar)
        await ctx.reply(embed=embed)

async def setup(bot):
    await bot.add_cog(utility(bot))
