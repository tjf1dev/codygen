from main import *

class utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "tools that can be helpful sometimes!"
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @commands.hybrid_group(name="utility",description="tools that can be helpful sometimes!")
    async def utility(self,ctx):
        await ctx.reply("utility")
    @utility.command(name="pfp", description="Get someones pfp")
    async def pfp(self,ctx, user: discord.User=None):
        if user == None:
            user = ctx.author
        avatar = user.avatar.url
        embed = discord.Embed(color=0x8ff0a4)
        embed.set_image(url=avatar)
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(utility(bot))