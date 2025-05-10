from main import *
class admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands for bot administrators. you need to be a team member to run any of these commands"


    #* THE FOLLOWING GROUP DOESNT HAVE A SLASH COMMAND AND ITS ON PURPOSE!!
    @commands.group(name="admin", description="commands for bot administrators. you need to be a team member to run any of these commands", invoke_without_command=True)
    async def admin(self,ctx: commands.Context):
        pass
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @commands.is_owner()
    @admin.command(name="restart", description="fully restarts every instance of the bot") 
    async def restart(self,ctx: commands.Context):
        await ctx.message.add_reaction("✅")
        exit()
    @commands.is_owner()
    @admin.command(name="regen_config", description="regenerates the config for current guild.")
    # use -g flag for global. #! DEFINITELY NOT RECOMMENDED WIPES EVERY CONFIG PLEASE DON'T
    async def regen_config(self, ctx: commands.Context, *, flags=None):
        if flags == f"-g {GLOBAL_REGEN_PASSWORD}":
            await ctx.reply("regenerating global config. please note that this is not recommended. change the password in the .env file after the regeneration is done.")
            time.sleep(5)
            for filename in os.listdir("data/guilds"):
                file_path = os.path.join("data/guilds", filename)
                if os.path.isfile(file_path):
                    with open(file_path, "w") as f:
                        json.dump(get_config_defaults("guild"), f, indent=4)
            await ctx.reply("finished regen")
        else:
            with open(f"data/guilds/{ctx.guild.id}.json", "w") as f:
                json.dump(get_config_defaults("guild"), f, indent=4)
            await make_guild_config(ctx.guild.id, get_config_defaults()["guild"]) #TODO THIS WILL CHANGE WITH THE NEW CONFIG SYSTEM I WILL FORGET ABOUT THIS
            await ctx.reply(f"config for {ctx.guild.name} regenerated successfully")
    @commands.is_owner()
    @admin.command(name="purgetickets",description="purges all tickets in the guild. not recommended if there are active tickets. NOTE: THIS DOES NOT REMOVE CHANNELS")
    async def purgetickets(self,ctx: commands.Context):
        try:
            with open(f"data/guilds/{ctx.guild.id}.json","r") as f:
                data = json.load(f)
                tickets = data["stats"]["ticket"]
                data["stats"]["ticket"] = []

            with open(f"data/guilds/{ctx.guild.id}.json","w") as f:
                json.dump(data,f,indent=4)
                await ctx.reply("done")
        except Exception as e:
            await ctx.reply(f"error: {str(e)}")

async def setup(bot):
    await bot.add_cog(admin(bot))
