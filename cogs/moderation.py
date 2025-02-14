from main import *

class moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands to help you manage your community."
    
    @commands.hybrid_group(name="moderation",description="commands to help you manage your community.")
    async def moderation(self,ctx):
        pass
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @verify()
    @moderation.command(name="viewbanned", description="View banned people.")
    async def viewbanned(self,ctx):
        if ctx.author.guild_permissions.ban_members and ctx.author != None:
            bans = [entry async for entry in ctx.guild.bans()]
            if len(bans) == 1:
                msg = f"is {len(bans)} person"
            else:
                msg = f"are {len(bans)} people"
            e = discord.Embed(
                title=f"there {msg} banned in {ctx.guild.name}",
                color=0xff0000
            )
            if len(bans) == 0:
                e.description = "no one is banned in this server"
            for ban in bans:
                e.add_field( 
                    name=f"{ban.user} ({ban.user.id})",
                    value=f"```{ban.reason}```",
                    inline=False
                    )
            
            await ctx.reply(embed=e,ephemeral=True)      
        else:
            await ctx.reply("you dont have permission to do this",ephemeral=True)

async def setup(bot):
    await bot.add_cog(moderation(bot))