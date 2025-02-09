from main import *


class admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands for bot administratiors. you need to be a team member to run any of these commands"

    @commands.hybrid_group(name="admin", description="commands for bot administratiors. you need to be a team member to run any of these commands", invoke_without_command=True)
    async def admin(self,ctx):
        pass
    
    @commands.is_owner()
    @admin.command(name="restart", description="fully restarts every instance of the bot") 
    async def restart(self,ctx):
        await ctx.reply("restarting bot...")
        exit()
    @commands.is_owner()
    @admin.command(name="regen_config", description="regenerates the config for current guild.")
    # use -g flag for global. DEFENITELY NOT RECOMMENDED WIPES EVERY CONFIG PLEASE DONT
    async def regen_config(self,ctx, *, flags=None):
        if flags == f"-g {GLOBAL_REGEN_PASSWORD}":
            await ctx.reply("regenerating global config. please note that this is not recommended. change the password in the .env file after the regen is done.")
            time.sleep(5)
            await ctx.reply("finished regen")
        try:
            if flags != None:

                if flags.startswith("-g"):
                    await ctx.reply("invalid password, maybe it was changed?")
        except Exception as e:
            pass
        else:
            with open("config.json","r") as f:
                data = json.load(f)
                guilds = data["guilds"]
                guilds[str(ctx.guild.id)] = get_config_defaults("guild")
            with open("config.json","w") as f:
                json.dump(data,f,indent=4)
                
            await ctx.reply(f"config for {ctx.guild.name} regenerated successfully")
    @commands.is_owner()
    @admin.command(name="reload",description="reload a module. usage: reload <module>")
    async def reload(ctx, module: str):
        await client.reload_extension(module)
        await ctx.reply(f"reloaded {module}")

async def setup(bot):
    await bot.add_cog(admin(bot))