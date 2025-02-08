# written by a random gay fox and the cutest proot ever
# awwwww :33 ~proot

# our links
# tjf1: https://github.com/tjf1dev
# cody: https://github.com/theridev

# feel free to read this terrible code, we are not responsible for any brain damage caused by this.

import discord, os,dotenv,random,json,time
from discord.ext import commands
from colorama import Fore

# pre-init functions
def get_prefix(bot=None, message=None):
    try:
        with open("config.json","r") as f:
            data = json.load(f)
            guild = data["guilds"][str(message.guild.id)]
            prefix = guild["prefix"]["prefix"]
            if message == None or prefix == None:
                return ">"
            return prefix

    except Exception as e:
        return ">"
# definitions

activity = discord.Activity(type=discord.ActivityType.watching, name="silly people :3")
client = commands.Bot(command_prefix=get_prefix,intents=discord.Intents.all(), status=discord.Status.online, activity=activity, help_command=None)
tree = client.tree
dotenv.load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")

# command configs

# words used for /awawawa
words = ["awawawawawawa",":3","uwu","owo",">~<"]

# events

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return  # Silently ignore check failures
    await ctx.send(f"An error occurred: {error}")  # Handle other errors normally

@client.event
async def on_ready():
    print(f"bot started as {Fore.LIGHTMAGENTA_EX}{client.user.name}{Fore.RESET}")
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if client.user.mentioned_in(message):
        e = discord.Embed(
            title=f"{client.user.name}",
            description=f"my prefix for this server is: `{get_prefix(message=message)}`, or you can use slash commands!",
            color=0xff00ff
        )
        await message.reply(embed=e)
    await client.process_commands(message)
def verify():
    async def predicate(ctx):
        try:
            with open("config.json","r") as f:
                data = json.load(f)
                guild = data["guilds"][str(ctx.guild.id)]
                prefix_enabled = guild["prefix"]["prefix_enabled"]
        except Exception as e:
            prefix_enabled = True
        if ctx.interaction is not None:
            return True
        if prefix_enabled == False:
            return False
        return True 
    return commands.check(predicate)


@verify()
@client.hybrid_command(name="ping", description="shows the bot latency and other stuff idk lol")
async def ping(ctx):
    e = discord.Embed(
        title="codygen",
        description=f"hii :3 bot made by `tjf1` and `codydafoxie`",
        color=0xff00ff
    )
    e.add_field(
        name="commands",
        value=f"`serving {len(tree.get_commands())} commands`",
    )
    await ctx.reply(embed=e, ephemeral=True, mention_author=False)
@client.hybrid_command(name="help", description="shows the bot latency and other stuff idk lol")
async def help_command(ctx):
    await ctx.reply("do you really think we were gonna make a real help command? yes, we will. soon")
@verify()
@commands.is_owner()
@client.hybrid_command(name="sync",description="syncs app commands")
async def sync(ctx, *, flags=None):
    if flags == "-g":
        success = discord.Embed(
            title=f"successfully synced {len(tree.get_commands())} commands for all guilds!",
            color=0x00ff00
        )
        await tree.sync()
    else:
        success = discord.Embed(
            title=f"successfully synced {len(tree.get_commands())} commands for this guild!",
            color=0x00ff00
        )
        await tree.sync(guild=await client.fetch_guild(1333785291584180244))

    await ctx.reply(embed=success,ephemeral=True,mention_author=False)
@verify()
@tree.command(name="test",description="test command")
async def test(interaction: discord.Interaction):
    await interaction.reply.send_message("test command",ephemeral=True)

@verify()
@client.hybrid_command(name="viewbanned", description="View banned people.")
async def viewbanned(ctx):
    if ctx.author.guild_permissions.ban_members and ctx.author != None:
        bans = [entry async for entry in ctx.guild.bans()]
        e = discord.Embed(
            title=f"banned people in {ctx.guild.name}",
            color=0xff0000
        )
        if len(bans) == 0:
            e.description = "no one is banned in this server"
        for ban in bans:
            e.add_field( # cody: last seen at line 134
                name=f"{ban.user}",
                value=f"reason: {ban.reason}",
                inline=False
                )
        
        await ctx.reply(embed=e)      
    else:
        await ctx.reply("you dont have permission to do this",ephemeral=True)

@verify()
@client.hybrid_command(name="awawawa",description="awawawawawawa")
async def awawawa(ctx):
    await ctx.reply(random.choice(words),ephemeral=True)

@verify()
@client.hybrid_command(name="randomword", description="get random word from english dictionary")
async def randomword(ctx):
    with open("words.txt", "r") as file:
        text = file.read()
        words = list(map(str, text.split()))
        await ctx.reply(random.choice(words))

@verify()
@client.hybrid_command(name="cute",description="cute command")
async def cute(ctx, user: discord.User=None):
    if user:
        await ctx.reply(f"{user.mention} is cute and silly :3")
    else:  
        await ctx.reply("you are cute and silly :3",ephemeral=True)

@verify()
@client.hybrid_command(name="wokemeter",description="see how WOKE someone is!")
async def wokemeter(ctx, user: discord.User=None):
    if user.id == 1266572586528280668:
        await ctx.reply(f"{user.mention} is 101% woke")
    if user == None:
        user = ctx.author
    if user.bot == True:
        await ctx.reply(f"bots cant be woke :broken_heart:")
    else:
        await ctx.reply(f"{user.mention} is {random.randint(80,100)}% woke")

@verify()
@client.hybrid_command(name="ship", description="SHIP TWO PEOPEL")
async def ship(ctx, user1: discord.User=None, user2: discord.User=None):
    if user2 == None:
        user2 = ctx.author
    if user1.id in [978596696156147754,1277351272147582990] and user2.id in [978596696156147754,1277351272147582990]:
        await ctx.reply(f"ship between {user1.mention} and {user2.mention} is ??? its too high idk")
    elif user1 == user2:
        await ctx.reply("awwwwwe you need love yourself :3 100%")
    else:
        await ctx.reply(f"ship between {user1.mention} and {user2.mention} is {random.randint(0,100)}%")
        
@verify()
@client.hybrid_command(name="whosthecutest", description="who is the cutest")
async def whosthecutest(ctx):
    await ctx.reply(r"<@978596696156147754>")

@client.hybrid_command(name="pfp", description="Get someones pfp")
async def pfp(ctx, user: discord.User=None):
    if user == None:
        user = ctx.author
    avatar = user.avatar.url
    embed = discord.Embed(color=0x8ff0a4)
    embed.set_image(url=avatar)
    await ctx.reply(embed=embed)

@client.hybrid_group(name="settings", description="settings command")
async def settings(ctx):
    pass

@commands.is_owner()
@settings.command(name="toggle_prefix", description="toggle if prefixed commands are enabled in this guild. -e to enable, -d to disable")
async def toggle_prefix(ctx, *, flags=None):
        if flags == "-e":
            with open("config.json","r") as f:
                data = json.load(f)
                guild = data["guilds"][str(ctx.guild.id)]
                guild["prefix"]["prefix_enabled"] = True
            with open("config.json","w") as f:
                json.dump(data,f,indent=4)
            await ctx.reply("prefixed commands have been enabled for this server!",ephemeral=True)
        if flags == "-d":
            with open("config.json","r") as f:
                data = json.load(f)
                guild = data["guilds"][str(ctx.guild.id)]
                guild["prefix"]["prefix_enabled"] = False
            with open("config.json","w") as f:
                json.dump(data,f,indent=4)
            await ctx.reply("prefixed commands have been disabled for this server!",ephemeral=True)
            
@commands.is_owner()
@settings.command(name="set_prefix", description="change the prefix for this guild. wont work if prefixed commands are disabled. set flag to your new prefix.")
async def set_prefix(ctx, *, flags=None):
        with open("config.json","r") as f:
            data = json.load(f)
            guild = data["guilds"][str(ctx.guild.id)]
            guild["prefix"]["prefix"] = flags
        with open("config.json","w") as f:
            json.dump(data,f,indent=4)
        await ctx.reply(f"the prefix for this server has been set to `{flags}`!",ephemeral=True)
        
@commands.is_owner()
@settings.command(name="regen_config", description="regenerates the config for current guild.")
# use -g flag for global. DEFENITELY NOT RECOMMENDED WIPES EVERY CONFIG PLEASE DONT
async def regen_config(ctx, *, flags=None):
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
            guilds[str(ctx.guild.id)] = {"prefix":{"prefix":">","prefix_enabled":True}}
        with open("config.json","w") as f:
            json.dump(data,f,indent=4)
            
        await ctx.reply(f"config for {ctx.guild.name} regenerated successfully")
# run bot or smth idk
client.run(TOKEN)

