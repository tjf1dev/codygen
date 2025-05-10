from main import *
import subprocess
class admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "commands for bot administrators. you need to be a team member to run any of these commands"


    #* THE FOLLOWING GROUP DOESNT HAVE A SLASH COMMAND AND ITS ON PURPOSE!!
    @commands.group(name="admin", description="commands for bot administrators. you need to be a team member to run any of these commands", invoke_without_command=True)
    async def admin(self,ctx: commands.Context):
        pass
    
    async def cog_load(self):
        logger.ok("loaded admin")
        version = get_global_config()["version"]
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"v{version}")
        self.bot: commands.Bot
        await self.bot.change_presence(activity=activity, status=discord.Status.idle)
    @commands.is_owner()
    @admin.group(name="status")
    async def status(self, ctx: commands.Context):
        pass
    @commands.is_owner()
    @status.command(name="refresh", description="refresh the status to default (version display)")
    async def refresh(self, ctx: commands.Context):
        activity = discord.Activity(type=discord.ActivityType.watching, name=f"v{version}")
        self.bot: commands.Bot
        await self.bot.change_presence(activity=activity, status=discord.Status.idle)
        await ctx.message.add_reaction("✅")
    @commands.is_owner()
    @status.command(name="set", description="set the bot's status")
    async def set(self, ctx: commands.Context, type: int = 0, status: int = 0, *, content: str):
        if type == 0: type = discord.ActivityType.playing
        if type == 1: type = discord.ActivityType.listening
        if type == 2: type = discord.ActivityType.watching
        if status == 0: status = discord.Status.online
        if status == 1: status = discord.Status.dnd
        if status == 2: status = discord.Status.idle
        if status == 3: status = discord.Status.invisible
        activity = discord.Activity(type=type, name=content)
        await self.bot.change_presence(activity=activity, status=status)
        await ctx.message.add_reaction("✅")
        
    @commands.is_owner()
    @admin.command(name="restart", description="fully restarts every instance of the bot") 
    async def restart(self,ctx: commands.Context):
        await ctx.message.add_reaction("🔄")
        async def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '🔄'
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=5.0, check=check)
        except asyncio.TimeoutError:
            await ctx.reply("-# timed out")
        else:
            await ctx.reply("-# restarting...")
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
    @commands.is_owner()
    @admin.command(name="update", description="Attempt to automatically update codygen through git.")
    async def update(self, ctx: commands.Context, version: str = None):
        try:
            logger.info(f"Attempting to update codygen to version: {version}")
            git_command = ["git", "pull"]
            result = subprocess.run(git_command, capture_output=True, text=True, check=True)
            uptodate = discord.Embed(
                description="codygen is already up to date.",
                color=Color.white
            )
            e = discord.Embed(
                description="codygen successfully updated.\nrestart now to apply changes.",
                color=Color.positive
            )
            if result.stdout.strip() == "Already up to date.":
                embed = uptodate
                content = None
            else:
                embed = e
                content = f"```{result.stdout}```"
            if version:
                async with aiofiles.open('config.json', 'r') as f:
                    data = json.loads(await f.read())
                    data["version"] = version
                async with aiofiles.open('config.json', 'w') as f: 
                    f.write(json.dumps(data, indent=4))
            await ctx.reply(content,embed=embed)
            
        except subprocess.CalledProcessError as e:
            await ctx.reply(f"```{e.stderr}```")
async def setup(bot):
    await bot.add_cog(admin(bot))
