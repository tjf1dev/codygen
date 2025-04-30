# codygen - a bot that does actually everything :sob:
#
# tjf1: https://github.com/tjf1dev
#
# feel free to read this terrible code, i am not responsible for any brain damage caused by this.
# importing the modules
import discord, os,dotenv, random, json, time, flask, psutil, datetime, logging, requests, asyncio,hashlib,io, sys
from discord.ext import commands
from discord import app_commands
from colorama import Fore 

DEFAULT_GLOBAL_CONFIG = open("config.json.template").read()

def get_global_config():
    """
    Loads config.json, or if it doesn't exist / is invalid JSON,
    writes out DEFAULT_GLOBAL_CONFIG and returns it.
    """
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open("config.json", "w") as f:
            json.dump(DEFAULT_GLOBAL_CONFIG, f, indent=4)
        return DEFAULT_GLOBAL_CONFIG

# pre-init functions
def get_config_defaults():
    with open(f"config.json","r") as f:
        return json.load(f)["template"]["guild"]
def get_guild_config(guild_id):
    try:
        with open(f"data/guilds/{guild_id}.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
def set_guild_config_key(guild_id, key, value):
    config = get_guild_config(guild_id)
    
    keys = key.split(".")
    d = config
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value
    
    os.makedirs("data/guilds", exist_ok=True)
    with open(f"data/guilds/{guild_id}.json", "w") as f:
        json.dump(config, f, indent=4)

# example
# set_guild_config_key(123456789, "settings.prefix", "!")

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
def custom_api_request(bot,endpoint:str,method:str=requests.get,auth:bool=True):
    url = f"https://discord.com/api/v10{endpoint}"
    if auth:
        headers={
            "Authorization":f"Bot {TOKEN}"
        }
    else:
        headers={}
    req = method(url,headers=headers)
    return req
# Utility function: recursively update a dictionary with missing keys from a template.
# def recursive_update(original: dict, template: dict) -> dict:
#     for key, value in template.items():
#         if isinstance(value, dict):
#             original[key] = recursive_update(original.get(key, {}), value)
#         else:
#             original.setdefault(key, value)
#     return original
# def get_guild_config(guild_id):
#     try:
#         with open(f"data/guilds/{guild_id}.json","r") as f:
#             guild = json.load(f)
#             return guild
#     except FileNotFoundError:
#         return None
# def set_guild_config_key(guild_id,key,value):
#     try:
#         with open(f"data/guilds/{guild_id}.json","r") as f:
#             guild = json.load(f)
#             guild[key] = value
#         with open(f"data/guilds/{guild_id}.json","w") as f:
#             json.dump(guild,f,indent=4)
#             return True
#     except FileNotFoundError:
#         return False
# def get_global_config():
#     try:
#         with open("config.json", "r") as f:
#             data = json.load(f)
#             return data
#     except FileNotFoundError:
#         return None
# def get_config_defaults(type="guild"):
#     with open("config.json","r") as f:
#         data = json.load(f)
#         if type == "guild":   
#             return data["template"]["guild"]
#     return None

# Required .env configurations
def get_required_env():
    r = []
    with open(".env.template","r") as f:
        lines = f.readlines()
        for l in lines:
            r.append(l.split("=")[0])
REQUIRED_ENV = get_required_env()

def ensure_env():
    """
    Checks that all REQUIRED_ENV keys exist and are non-empty.
    (so the user can copy it to .env and fill in real values),
    then exits with a meaningful message.
    """
    missing = []
    for key in REQUIRED_ENV.items():
        val = os.getenv(key)
        if not val:
            missing.append(key)

    if missing:
        logger.error(
            f"Missing environment variables: "
            + ", ".join(missing)
            + "\nI have generated a `.env.template` in this folder.\n"
            + "\n By default, you may not see files that have a dot in them, so enable listing of hidden files to see it.\n"
            + f"→ Copy it to `.env` and fill in the real values before restarting.\n"
            + f"For more details on how to configure the bot, please refer to the official documentation:\n"
            + f"https://github.com/tjf1dev/codygen#self-hosting.{Fore.RESET}"
        )
        sys.exit(1)


# flask flask flask flask
app = flask.Flask("codygen")
logger = logging.getLogger(__name__)

app = flask.Flask("codygen")

@app.route("/callback")
def callback():
    token = flask.request.args.get("token")
    uid = flask.request.args.get("user")
    try:
        api_key = os.environ['LASTFM_API_KEY']
        secret = os.environ['LASTFM_SECRET']
    except KeyError:
        logger.error(f"Misconfiguration of last.fm application configuration fields in .env file: LASTFM_SECRET and/or LASTFM_API_KEY")
        output = {
           "error": "Misconfigured bot configuration",
           "details": ".env file appears to have missing LASTFM_SECRET and/or LASTFM_API_KEY, contact the bot administrator for more details."
        }
        return output
    if not token or not uid:
        return {"error": "Missing parameters", "details": "Token or user ID is missing"}
    params = {
        'api_key': api_key,
        'method': 'auth.getSession',
        'token': token
    }
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    sig_string = sorted_params + secret
    api_sig = hashlib.md5(sig_string.encode('utf-8')).hexdigest()
    url = "http://ws.audioscrobbler.com/2.0/"
    params.update({'api_sig': api_sig, 'format': 'json'})

    r = requests.get(url, params=params)
    data = r.json()

    logger.info(f"{uid}'s data is {data}")
    try:
        with open("data/last.fm/users.json","r") as f:
            json_data = json.load(f)
        json_data[uid] = data
        with open("data/last.fm/users.json","w") as f:
            json.dump(json_data, f,indent=4)
    except Exception as e:
        logger.error(f"An error occured while trying to authenticate {uid}: {e}")

    if 'session' in data:
        return flask.render_template("success.html")
    else:
        logger.error(f"Session key missing: {data}")
        return {"error": "Session key missing", "details": str(data)}

@app.route("/")
def root():
    return({"status":"codygen is online"})
# setup logging
import logging
from colorama import Fore
import threading
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
def recursive_update(existing_config, template_config):
    def merge(d1, d2):
        result = d1.copy()
        for key, value in d2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge(result[key], value)
            else:
                result.setdefault(key, value)
        return result

    return merge(existing_config, template_config)
if logger.hasHandlers():
    logger.handlers.clear()
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter('%(asctime)s [ %(levelname)s ] %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False
# disable discord.py logging
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
for h in discord_logger.handlers:
    discord_logger.removeHandler(h)
logging.getLogger('discord.http').setLevel(logging.CRITICAL)
if not os.path.exists("logs"):
    os.makedirs("logs")
# setup file logging
log_filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
file_handler = logging.FileHandler(f"logs/{log_filename}")
latest_handler = logging.FileHandler("logs/latest.log", mode='w')  # overwrite the latest log on each run
file_handler.setFormatter(ColorFormatter('%(asctime)s [ %(levelname)s ] %(message)s'))
latest_handler.setFormatter(ColorFormatter('%(asctime)s [ %(levelname)s ] %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(latest_handler)
# ensure the 'logs' directory exists
# load configs
try:
    with open("config.json","r") as f:
        data = json.load(f)
except Exception as e:
    print(f"{Fore.LIGHTRED_EX}could not find config, generating new configuration{Fore.RESET}")
    pass
# command configs
data = get_global_config()
words = data["commands"]["awawawa"]["words"]
version = data["version"]
# bot definitions
intents = discord.Intents.all()
activity = discord.Activity(type=discord.ActivityType.watching, name=f"v{version}")
client = commands.AutoShardedBot(
    command_prefix=get_prefix,
    intents=intents,
    status=discord.Status.idle,
    activity=activity,
    help_command=None,
    allowed_contexts=app_commands.AppCommandContext(guild=True,dm_channel=True,private_channel=True),
    allowed_installs=app_commands.AppInstallationType(guild=True,user=True)
)
tree = client.tree
# load env
dotenv.load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") # bot token
GLOBAL_REGEN_PASSWORD = os.getenv("GLOBAL_REGEN_PASSWORD")
# views
class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        options = []
        bot = client
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                if cog_name.lower() in ["jishaku"]:
                    pass
                else:
                    description = getattr(cog, "description", "no description available.")
                    options.append(discord.SelectOption(label=cog_name.lower(), description=description.lower()))
        else:
            # add a fallback option if no cogs are loaded
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
class supportReply(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(SupportButton())
class SupportButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Start conversation", style=discord.ButtonStyle.primary)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SupportModal())
class SupportModal(discord.ui.Modal, title='Reply to Support Ticket'):
    response = discord.ui.TextInput(label='Response', style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        original_user_id = interaction.message.content.splitlines()[0]
        ticket_id = interaction.message.content.splitlines()[1]
        user = await client.fetch_user(int(original_user_id))
        try:
            e = discord.Embed(
                title=f"New reponse for ticket {ticket_id}",
                description=f"```{self.response.value}```"
            )
            await user.send(embed=e)
            e2 = discord.Embed(
                title=f"{ticket_id} - reply sent",
                description=f"```{self.response.value}```",
                color=0x00eb71
            )
            await interaction.response.send_message(embed=e2)
        except discord.errors.Forbidden:
            await interaction.response.send_message("Couldn't send DM to user.", ephemeral=True)
        await interaction.response.send_message(f'Response sent: {self.response.value}', ephemeral=True)
# events
def verify():
    async def predicate(ctx):
        # if ctx.guild is None:
        #     return True
        # prefix_enabled = get_guild_config(ctx.guild.id)["prefix"]["prefix_enabled"]
        # if prefix_enabled == None:
        #     prefix_enabled == False
        # if ctx.interaction is not None:
        #     return True
        # return prefix_enabled
        return True # fuck off
    return commands.check(predicate)
def verify_alt(guild_id,interaction):
        prefix_enabled = get_guild_config(guild_id)["prefix"]["prefix_enabled"]
        if prefix_enabled == None:
            prefix_enabled == False
        if interaction is not None:
            return True
        return prefix_enabled
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return 
    if isinstance(error, commands.MissingPermissions):
        e = discord.Embed(
            title="you don't have permissions to run this command.",
            color=0xff0000
        )
        await ctx.reply(embed=e,ephemeral=True)
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
        await ctx.send(embed=e,ephemeral=True)  # Handle other errors normally
        raise commands.errors.CommandError(str(error))
loaded_cogs = set()
@client.event
async def on_guild_join(guild):
    # stage 0
    e = discord.Embed(
        title=f"Welcome to codygen! The bot has been successfully added to {guild.name}.",
        description="## Support\n> Please join our [support server](https://discord.gg/WyxN6gsQRH).\n## Issues and bugs\n> Report all issues or bugs in the [issues tab](https://github.com/tjf1dev/codygen) of our GitHub repository.",
        color=0xffffff
    )
    e2 = discord.Embed(
        title="codygen will now attempt to automatically initizalize in your server.",
        description="> please wait, it can take a while.\n> note: if codygen dosen't update you on the progress of the initialization, you will need to do it yourself: run the </settings init:1340646304073650308> command in your guild.",
        color=0xd600a1
    )
    await guild.owner.send(embeds=[e,e2])
    bot_member = guild.me
    required_permissions = discord.Permissions(
        manage_roles=True,
        manage_channels=True,
        manage_guild=True,
        view_audit_log=True,
        read_messages=True,
        send_messages=True,
        manage_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        mention_everyone=True,
        use_external_emojis=True,
        add_reactions=True
    )
    if not bot_member.guild_permissions.is_superset(required_permissions):
        missing_perms = [
            perm for perm, value in required_permissions
            if not getattr(bot_member.guild_permissions, perm)
        ]
        error_embed = discord.Embed(
            title="Init Failed: Missing Permissions",
            description=f"### Missing the following permissions: `{', '.join(missing_perms)}`\nPlease fix the permissions and try again!",
            color=0xff0000
        )
        await guild.owner.send(embed=error_embed)
        return
    guild_config_path = f"data/guilds/{guild.id}.json"
    config_already_made = os.path.exists(guild_config_path)
    with open("config.json", "r") as f:
        template_config = json.load(f)["template"]["guild"]
    if not config_already_made:
        os.makedirs(os.path.dirname(guild_config_path), exist_ok=True)
        with open(guild_config_path, "w") as f:
            json.dump(template_config, f, indent=4)
    else:
        with open(guild_config_path, "r") as f:
            existing_config = json.load(f)
        updated_config = recursive_update(existing_config, template_config) #todo fix the thing lol
        with open(guild_config_path, "w") as f:
            json.dump(updated_config, f, indent=4)
    stage2 = discord.Embed(
        title="Initialization Finished!",
        description="No errors found",
        color=0x00ff00
    )
    stage2.add_field(
        name="Tests Passed",
        value="Permissions\n> The bot has sufficient permissions to work!\n"
                f"Config\n> {'A configuration file already exists and has been updated with missing keys' if config_already_made else 'A configuration file has been created for your guild!'}"
    )
    await guild.owner.send(embed=stage2)
@client.event
async def on_ready():
    global start_time
    if getattr(client, "already_ready", False):
        return
    client.already_ready = True
    client.start_time = time.time()
    await client.load_extension('jishaku') # jsk #* pip install jishaku
    config = get_global_config()
    blacklist = config["cogs"]["blacklist"]
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            cog_name = filename[:-3]
            if cog_name in loaded_cogs:
                logger.warning(f"Skipping duplicate load of {cog_name}")
                continue
            elif cog_name in blacklist:
                logger.warning(f"Skipping blacklisted cog {cog_name}")
                continue
            loaded_cogs.add(cog_name)
            logger.debug(f"loaded {cog_name}")
            try:
                await client.load_extension(f"cogs.{cog_name}")
            except asyncio.TimeoutError:
                print(f"Timeout while loading {cog_name}")
    logger.info(f"bot started as {Fore.LIGHTMAGENTA_EX}{client.user.name}{Fore.RESET}")
    start_time = time.time()
# @client.event
# async def on_message(message):
#     if message.author.bot:
#         return
#     if message.content == f"<@{client.user.id}>":
#         if verify_alt(message.guild.id,message.interaction) != True:
#             e = discord.Embed(
#                 title=f"hi! im codygen :3",
#                 description=f"### try using </help:1338168344506925108>! prefixed commands are disabled in this server.",
#                 color=0xff00ff
#             )
#         else:
#             e = discord.Embed(
#                 title=f"hi! im codygen :3",
#                 description=f"### try using </help:1338168344506925108>! the prefix for this server is: `{get_guild_config(message.guild.id)["prefix"]["prefix"]}`",
#                 color=0xff00ff
#             )
#         await message.reply(embed=e)
#     await client.process_commands(message)
@verify()
@app_commands.allowed_contexts(guilds=True,dms=True,private_channels=True)
@app_commands.allowed_installs(guilds=True,users=True)
@client.hybrid_command(name="ping", description="shows how well is codygen doing!") 
async def ping(ctx):
    e = discord.Embed(
        title=f"codygen v{version}",
        description=f"### hii :3 bot made by `tjf1`\nuse </help:1338168344506925108> for more info",
        color=0xff00ff
    )
    e.add_field(
        name="ping",
        value=f"`{round(client.latency * 1000)} ms`",
        inline=True
    )
    current_time = time.time()
    difference = int(round(current_time - start_time))
    uptime = str(datetime.timedelta(seconds=difference))
    e.add_field(
        name="uptime",
        value=f"`{uptime}`",
        inline=True
    )
    process = psutil.Process(os.getpid())
    ram_usage = process.memory_info().rss / 1024 ** 2
    total_memory = psutil.virtual_memory().total / 1024 ** 2
    e.add_field(
        name="ram usage",
        value=f"`{ram_usage:.2f} MB / {total_memory:.2f} MB`",
        inline=True
    )
    cpu_usage = psutil.cpu_percent(interval=1)
    e.add_field(
        name="cpu usage",
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
        value=f"`codygen has {len(set(commands_list))} commands`",
        inline=True
    )
    e.add_field(
        name="servers",
        value=f"`codygen is in {len(client.guilds)} servers.`",
        inline=True
    )
    e.add_field(
        name="users",
        value=f"`serving {len(client.users)} users.`",
        inline=True
    )
    e.add_field(
        name="system info",
        value=f"`running discord.py {discord.__version__} on python {sys.version.split()[0]}`",
        inline=True
    )    
    await ctx.reply(embed=e,ephemeral=False)
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
@client.hybrid_command(
    name="help",
    description="shows useful info about the bot."
)
async def help_command(ctx):
    embed = discord.Embed(
        title="codygen",
        description="**teap: a copy of this document can be found on [our documentation](https://github.com/tjf1dev/codygen/wiki)!**\nuse the menu's below to search for commands and their usages.", # teap
        color=0xffffff
    )
    await ctx.reply(embed=embed, view=HelpHomeView(client),ephemeral=True)
@app_commands.allowed_installs(guilds=False,users=True)
@app_commands.allowed_contexts(guilds=False,dms=True,private_channels=True)
@client.hybrid_command(name="support",description="contact the bot developers.")
async def support(ctx,topic:str):
    ticket_id=f"{ctx.author.name}{random.randint(1000000,9999999)}"
    # user side
    e = discord.Embed(
        title="ticket has been sent.",
        description="please note that it may take a few days to receive a response.\nyou will recieve a DM from codygen if you do.\nfor faster response time, please join our [server](<https://discord.gg/WyxN6gsQRH>).",
        color=0xffffff
    ).add_field(
        name="ticket ID (please keep this for reference.)",
        value=f"```{ticket_id}```"
    )
    msg = discord.Embed(
        title="your message",
        description=f"{topic}",
        color=0x5f5f5f
    )
    await ctx.reply(embeds=[e,msg],ephemeral=True)
    await ctx.author.send(embeds=[e,msg]) # dm
    # dev side
    e2 = discord.Embed(
        title="New support ticket",
        description=f"```{topic}```",
        color=0x00eb71
    ).add_field(
        name="User",value=f"Name: {ctx.author.name} ({ctx.author.mention})\nID: {ctx.author.id}"
    ).add_field(
        name="Ticket",
        value=f"ID: `{ticket_id}`"
    )
    channel_id = get_global_config()["support"]["channel"]
    channel = await client.fetch_channel(channel_id)
    await channel.send(f"{ctx.author.id}\n{ticket_id}", embed=e2, view=supportReply())
if __name__ == "__main__":
    ensure_env()
    def run_app():
        app.run("0.0.0.0",port=4887)

    threading.Thread(target=run_app).start()
    client.run(TOKEN)
