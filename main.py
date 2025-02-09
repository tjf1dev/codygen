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
import discord, os,dotenv, random, json, time, csv
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
    with open("config.json","r") as f:
        data = json.load(f)
        guild = data["guilds"][str(guild_id)]
        return guild
    
def get_value_from_guild_config(guild_id, key):
    with open("config.json","r") as f:
        data = json.load(f)
        guild = data["guilds"][str(guild_id)]
        return guild[key]
    
def set_value_from_guild_config(guild_id, key, value):
    with open("config.json","r") as f:
        data = json.load(f)
        guild = data["guilds"][str(guild_id)]
        guild[key] = value
    with open("config.json","w") as f:
        json.dump(data,f,indent=4)

def get_config_defaults(type="guild"):
    with open("config.json","r") as f:
        data = json.load(f)
        if type == "guild":
            return data["template"]["guild"]
    return None

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

activity = discord.Activity(type=discord.ActivityType.watching, name=f"version {version}")
client = commands.Bot(
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
        try:
            with open("../config.json","r") as f:
                data = json.load(f)
                guild = data["guilds"][str(ctx.guild.id)]
                prefix_enabled = guild["prefix_enabled"]
        except Exception as e:
            prefix_enabled = "true"
        if ctx.interaction is not None:
            return True
        if prefix_enabled == "false":
            print("prefixed commands are disabled.")
            return False
        if prefix_enabled == "true":
            print("prefixed commands are enabled.")
            return True
        
        return False 
    return commands.check(predicate)
# cody: last seen at line 134
# im alive, silly. - cody
# nope, you arent :c
# run bot or smth idk

        
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return 
    
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        e = discord.Embed(
            title="an error occurred while trying to run this command",
            description="please report this to the [developers of this bot.](https://github.com/tjf1dev/codygen)",
            color=0xff0000
        ).add_field(
            name="error",
            value=f"```{error}```"
        ).add_field(
            name="command",
            value=f"```{ctx.command.name}```", inline=False
        ).add_field(
            name="version",
            value=f"```{version}```", inline=True
        )
        await ctx.send(embed=e)  # Handle other errors normally

@client.event
async def on_ready():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            print(f"[ {Fore.GREEN}OK{Fore.RESET} ] Loading {Fore.BLUE}{filename}{Fore.RESET}") # fuckin
            await client.load_extension(f"cogs.{filename[:-3]}") # do you need await for this??? yes you do
    print(f"[ {Fore.GREEN}OK{Fore.RESET} ] bot started as {Fore.LIGHTMAGENTA_EX}{client.user.name}{Fore.RESET}")
@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content == f"<@!{client.user.id}>":
        e = discord.Embed(
            title=f"{client.user.name}",
            description=f"my prefix for this server is: `{get_prefix(message=message)}`, or you can use slash commands!",
            color=0xff00ff
        )
        await message.reply(embed=e)
    await client.process_commands(message)
@verify()
@client.hybrid_command(name="ping", description="shows the bot latency and other stuff idk lol") # can you write a better description? - cody / no i cant - tjf1
async def ping(ctx):
    e = discord.Embed(
        title="codygen",
        description=f"hii :3 bot made by `tjf1` and `codydafoxie`", # im the second one
        color=0xff00ff
    )
    e.add_field(
        name="commands",
        value=f"`serving {len(commands.tree.get_commands())} commands`",
    )
    await ctx.reply(embed=e, ephemeral=True, mention_author=False)
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
        description="**teap: a copy of this document can be found on [our documentation](https://github.com/tjf1dev/codygen/wiki)!**\nuse the menus below to search for commands and their usages.",
        color=0xffffff
    )
    await ctx.reply(embed=embed, view=HelpHomeView(client))

if __name__ == "__main__":
    client.run(TOKEN)