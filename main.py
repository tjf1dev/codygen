#
#
#
#                        █████                                        
#                       ░░███                                         
#   ██████   ██████   ███████  █████ ████  ███████  ██████  ████████  
#  ███░░███ ███░░███ ███░░███ ░░███ ░███  ███░░███ ███░░███░░███░░███ 
# ░███ ░░░ ░███ ░███░███ ░███  ░███ ░███ ░███ ░███░███████  ░███ ░███ 
# ░███  ███░███ ░███░███ ░███  ░███ ░███ ░███ ░███░███░░░   ░███ ░███ 
# ░░██████ ░░██████ ░░████████ ░░███████ ░░███████░░██████  ████ █████
#  ░░░░░░   ░░░░░░   ░░░░░░░░   ░░░░░███  ░░░░░███ ░░░░░░  ░░░░ ░░░░░ 
#                               ███ ░███  ███ ░███                    
#                              ░░██████  ░░██████                     
#                               ░░░░░░    ░░░░░░                      
#
#
#
# 
# codygen - a bot that does actually everything :sob:
# written by a random gay fox and the cutest proot ever
#
#
# "I love tjf1"
# - cody, 9/2/2025
#
# our links
# tjf1 (the cutest proot): https://github.com/tjf1dev
# cody: https://github.com/theridev
#
# feel free to read this terrible code, we are not responsible for any brain damage caused by this.

# importing the modules
import discord, os,dotenv, random, json, time, csv, psutil, datetime, logging, requests, asyncio,io,traceback
from discord.ext import commands
from discord import app_commands
from colorama import Fore # this module is so fore!!!


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

def get_guild_config(guild_id):
    try:
        with open(f"data/guilds/{guild_id}.json","r") as f:
            guild = json.load(f)
            return guild
    except FileNotFoundError:
        return None
    
def set_guild_config_key(guild_id,key,value):
    try:
        with open(f"data/guilds/{guild_id}.json","r") as f:
            guild = json.load(f)
            guild[key] = value
        with open(f"data/guilds/{guild_id}.json","w") as f:
            json.dump(guild,f,indent=4)
            return True
    except FileNotFoundError:
        return False
def get_global_config():
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return None
def get_config_defaults(type="guild"):
    with open("config.json","r") as f:
        data = json.load(f)
        if type == "guild":
            return data["template"]["guild"]
    return None
# setup logging
import logging
from colorama import Fore
logger = logging.getLogger(__name__)

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Fore.LIGHTBLACK_EX,
        'INFO': Fore.BLUE,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
        'OK': Fore.GREEN
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, Fore.WHITE)
        record.levelname = f"{log_color}{record.levelname}{Fore.RESET}"
        record.msg = f"{log_color}{record.msg}{Fore.RESET}"
        return super().format(record)

# AHHH FUCK YOU
if logger.hasHandlers():
    logger.handlers.clear()

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter('%(asctime)s [ %(levelname)s ] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False

# Disable discord.py logging
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
for h in discord_logger.handlers:
    discord_logger.removeHandler(h)

logging.getLogger('discord.http').setLevel(logging.CRITICAL)

# load configs

try:
    with open("config.json","r") as f:
        data = json.load(f)
except Exception as e:
    print(f"{Fore.LIGHTRED_EX}could not find config{Fore.RESET}")
    pass



# command configs
words = data["commands"]["awawawa"]["words"]
version = data["version"]

# bot definitions

activity = discord.Activity(type=discord.ActivityType.watching, name=f"v{version}")
client = commands.AutoShardedBot(
    command_prefix=get_prefix,
    intents=discord.Intents.all(),
    status=discord.Status.online,
    activity=activity,
    help_command=None
)
tree = client.tree

# load env
dotenv.load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") # bot token
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")

# events

def verify():
    async def predicate(ctx):
        prefix_enabled = get_guild_config(ctx.guild.id)["prefix"]["prefix_enabled"]
        if prefix_enabled == None:
            prefix_enabled == False
        if ctx.interaction is not None:
            return True
        return prefix_enabled
    return commands.check(predicate)
def verify_alt(guild_id,interaction):
        prefix_enabled = get_guild_config(guild_id)["prefix"]["prefix_enabled"]
        if prefix_enabled == None:
            prefix_enabled == False
        if interaction is not None:
            return True
        return prefix_enabled
# cody: last seen at line 134
# im alive, silly. - cody
# nope, you arent :c
# run bot or smth idk

        
# @client.event
# async def on_command_error(ctx, error):
#     if isinstance(error, commands.CheckFailure):
#         return 
    
#     elif isinstance(error, commands.CommandNotFound):
#         return
#     else:
#         e = discord.Embed(
#             title="an error occurred while trying to run this command",
#             description="please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen)",
#             color=0xff0000
#         ).add_field(
#             name="error",
#             value=f"```{error}```"
#         ).add_field(
#             name="command",
#             value=f"```{ctx.command.name}```", inline=False
#         ).add_field(
#             name="version",
#             value=f"```{version}```", inline=True
#         )
#         await ctx.send(embed=e)  # Handle other errors normally
#         raise commands.errors.CommandError(str(error))
loaded_cogs = set()
@client.event
async def on_ready():
    if getattr(client, "already_ready", False):
        return
    client.already_ready = True
    client.start_time = time.time()
    await client.load_extension('jishaku') # jsk #* pip install jishaku
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            if cog_name in loaded_cogs:
                print(f"Skipping duplicate load of {cog_name}")
                continue  # Prevent duplicate loading
            loaded_cogs.add(cog_name)
            logger.debug(f"loaded {cog_name}")
            try:
                await client.load_extension(f"cogs.{cog_name}")
            except asyncio.TimeoutError:
                print(f"Timeout while loading {cog_name}")
    logger.info(f"bot started as {Fore.LIGHTMAGENTA_EX}{client.user.name}{Fore.RESET}")
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content == f"<@{client.user.id}>":
        if verify_alt(message.guild.id,message.interaction) != True:
            e = discord.Embed(
                title=f"hi! im codygen :3",
                description=f"### try using </help:1338168344506925108>! prefixed commands are disabled in this server.",
                color=0xff00ff
            )
        else:
            e = discord.Embed(
                title=f"hi! im codygen :3",
                description=f"### try using </help:1338168344506925108>! the prefix for this server is: `{get_guild_config(message.guild.id)["prefix"]["prefix"]}`",
                color=0xff00ff
            )
        await message.reply(embed=e)
    await client.process_commands(message)
@verify()
@client.hybrid_command(name="ping", description="shows how well is codygen doing!") # can you write a better description? - cody / no i cant - tjf1
async def ping(ctx):
    e = discord.Embed(
        title="codygen",
        description=f"### hii :3 bot made by `codydafoxie`, `tjf1`\nuse </help:1338168344506925108> for more info", # im the second one | nope your the first one :3
        color=0xff00ff
    )
    e.add_field(
        name="Ping",
        value=f"`{round(client.latency * 1000)} ms`",
        inline=True
    )
    current_time = time.time()
    difference = int(round(current_time - client.start_time))
    uptime = str(datetime.timedelta(seconds=difference))
    e.add_field(
        name="Uptime",
        value=f"`{uptime}`",
        inline=True
    )
    process = psutil.Process(os.getpid())
    ram_usage = process.memory_info().rss / 1024 ** 2
    total_memory = psutil.virtual_memory().total / 1024 ** 2
    e.add_field(
        name="RAM Usage",
        value=f"`{ram_usage:.2f} MB / {total_memory:.2f} MB`",
        inline=True
    )
    cpu_usage = psutil.cpu_percent(interval=1)
    e.add_field(
        name="CPU Usage",
        value=f"`{cpu_usage}%`",
        inline=True
    )
    # nerdy ahh logic
    commands_list = [command.name for command in client.commands if not isinstance(command, commands.Group)] + [
        command.name for command in client.tree.walk_commands() if not isinstance(command, commands.Group)
    ]

    for cog in client.cogs.values():
        for command in cog.get_commands():
            if not isinstance(command, commands.Group): 
                commands_list.append(command.name)

    for command in client.walk_commands():
        if not isinstance(command, commands.Group): 
            commands_list.append(command.name)
        else:
            for subcommand in command.walk_commands():
                commands_list.append(subcommand.name)

    e.add_field(
        name="commands",
        value=f"`serving {len(set(commands_list))} commands`",
    )
    await ctx.reply(embed=e,ephemeral=True)

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
        
class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        options = []
        bot = client
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                description = getattr(cog, "description", "No description available.")
                options.append(discord.SelectOption(label=cog_name, description=description))
        else:
            # Add a fallback option if no cogs are loaded
            options.append(discord.SelectOption(label="No Modules Loaded", description="Failed to load module list."))

        super().__init__(placeholder="Select a cog", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"codygen - {self.values[0]}",
            color=0xffffff
        )
        cog = client.get_cog(self.values[0])
        if cog == None:
            fail = discord.Embed(
                title="failed to load :broken_heart:",
                description=f"module {self.values[0]} (cogs.{self.values[0]}) failed to load.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=fail)
            return
        elif len(cog.get_commands()) == 0:
            fail = discord.Embed(
                title="its quiet here...",
                description=f"cogs.{self.values[0]} doesnt have any commands.",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=fail)
        else:
            for command in cog.walk_commands():
                embed.add_field(
                    name=command.name,
                    value=f"```{command.description}```",
                    inline=False
                )
            await interaction.response.edit_message(embed=embed,view=HelpHomeView(client))
class HelpWiki(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Documentation", style=discord.ButtonStyle.link, url="https://github.com/tjf1dev/codygen/wiki")
class HelpHomeView(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(HelpSelect(bot))
        self.add_item(HelpWiki())
@client.hybrid_command(
    name="help",
    description="shows useful info about the bot."
)
async def help_command(ctx):
    embed = discord.Embed(
        title="codygen",
        description="**teap: a copy of this document can be found on [our documentation](https://github.com/tjf1dev/codygen/wiki)!**\nuse the menus below to search for commands and their usages.", # teap
        color=0xffffff
    )
    await ctx.reply(embed=embed, view=HelpHomeView(client),ephemeral=True)

if __name__ == "__main__":
    client.run(TOKEN)