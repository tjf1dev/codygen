import discord
import aiohttp
from discord.ext import commands
from discord import app_commands
from PIL import Image
from io import BytesIO
from ext.logger import logger
from views import UserInfoLayout, ServerInfoLayout
from ext.utils import parse_commands
from ext.ui_base import Message


async def avg_color(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.read()
    img = Image.open(BytesIO(data)).convert("RGB")
    img = img.resize((1, 1))
    average_color = img.getpixel((0, 0))
    return average_color


class info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "pretty self explanatory"

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.hybrid_group(
        name="info", description="get information about certain things"
    )
    async def info(self, ctx: commands.Context):
        pass

    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @info.command(name="user", description="view information about a user")
    @app_commands.describe(user="user to check")
    async def user(
        self, ctx: commands.Context, user: discord.Member | discord.User | None = None
    ):
        if not user:
            user = ctx.author
        await ctx.reply(
            view=UserInfoLayout(user),
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @info.command(
        name="server",
        description="view information about the current server",
        aliases=["guild"],
    )
    async def guild(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return
        roles = guild.roles
        members = guild.members
        channels = guild.channels
        bots = []
        users = []
        for m in members:
            if m.bot:
                bots.append(m)
            else:
                users.append(m)
        voice_channels = []
        text_channels = []
        other_channels = []
        for c in channels:
            if c.type == discord.ChannelType.voice:
                voice_channels.append(c)
            if c.type == discord.ChannelType.text:
                text_channels.append(c)
            else:
                if c.type != discord.ChannelType.category:
                    other_channels.append(c)

        await ctx.reply(
            view=ServerInfoLayout(
                guild,
                len(roles),
                len(channels),
                len(text_channels),
                len(voice_channels),
                len(other_channels),
                len(members),
                len(bots),
                len(users),
            ),
            mention_author=False,
        )

    @commands.command(
        name="commands", description="lists all commands from the custom api request"
    )
    async def command(self, ctx: commands.Context):
        raw_commands = ctx.bot.full_commands
        text = ""
        cmds = parse_commands(raw_commands)
        for cmd in cmds:
            # text += f"type: {cmd["is_subcommand"]}"
            if cmd["is_subcommand"] == 0:  # no
                text += f"</{cmd['name']}:{cmd['id']}>\n{cmd['command'].get('description', '')}\n"
            if cmd["is_subcommand"] == 1:  # yes
                text += f"</{cmd['parent']['name']} {cmd['name']}:{cmd['id']}>\n{cmd['command'].get('description', '')}\n"
            if cmd["is_subcommand"] == 2:  # sub-subcommand
                text += f"</{cmd['parent']['parent']['name']} {cmd['parent']['name']} {cmd['name']}:{cmd['id']}>\n{cmd['command'].get('description', '')}\n"
        await ctx.reply(view=Message(text))


async def setup(bot):
    await bot.add_cog(info(bot))
