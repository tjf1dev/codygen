from main import *
from discord.ext import commands, tasks
import asyncio, re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
def parse_msglink(link: str):
    match = re.match(r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)", link)
    if match:
        guild_id, channel_id, message_id = map(int, match.groups())
        return guild_id, channel_id, message_id
    return None
class utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "tools that can be helpful sometimes!"

    @tasks.loop(hours=24)
    async def countdown_loop(self):
        target_date = datetime(datetime.now().year, 6, 5)
        channel = self.bot.get_channel(1333785292351606830)
        now = datetime.now()
        if now > target_date:
            await channel.send("deltarune tomorrow :3 (it's out)")
            self.countdown_loop.stop()
        else:
            days_left = (target_date - now).days
            if days_left == 1:
                await channel.send("deltarune tomorrow")
            else:
                await channel.send(f"{days_left} days until deltarune")

    @countdown_loop.before_loop
    async def before_countdown(self):
        await self.bot.wait_until_ready()
        now = datetime.now()
        next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        seconds_until_midnight = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.countdown_loop.is_running():
            self.countdown_loop.start()
        logger.info(f"{self.__class__.__name__}: loaded.")

    @commands.hybrid_group(name="utility", description="tools that can be helpful sometimes!")
    async def utility(self, ctx):
        await ctx.reply("utility")

    @utility.command(name="pfp", description="get someone's pfp")
    async def pfp(self, ctx, user: discord.User = None):
        if user is None:
            user = ctx.author
        avatar = user.avatar.url
        embed = discord.Embed(color=0x8ff0a4)
        embed.set_image(url=avatar)
        await ctx.reply(embed=embed)
    @commands.has_permissions(manage_messages=True)
    @utility.group(name="status", description="status updates for various things")
    async def status(self, ctx):
        pass
    @commands.has_permissions(manage_messages=True)
    @status.command(name="post", description="status updates for various things, post update. timestamps are in CEST")
    async def post(self, ctx, initial: str, title: str= "Downtime", channel: discord.TextChannel = None, ping: discord.Role = None):
        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        if not channel:
            channel = ctx.channel
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")
        e = discord.Embed(
            title=title,
            description=f"-# `[{date} CEST • dynamic status updates by codygen]`\n"
                        f"`[{time}]` {initial}",
            color=0x4775ff,
        ).set_footer(
            text=f"{channel.id}"
        )
        content = ""
        if ping:
            content = ping.mention
        msg = await channel.send(content, embed=e)
        await ctx.reply(f"posted to {channel.mention}!\nlink: `{msg.jump_url}` ({msg.jump_url})", ephemeral=True)
    @commands.has_permissions(manage_messages=True)
    @status.command(name="add", description="add an event to a status.")
    async def add(self, ctx, link: str, content: str, ping: bool = False):
        parsed = parse_msglink(link)
        if not parsed:
            await ctx.reply("invalid link", ephemeral=True)
            return
        self.bot: commands.Bot
        gid, cid, mid = parsed
        channel: discord.TextChannel = self.bot.get_channel(cid)
        msg: discord.Message = await channel.fetch_message(mid)
        e = msg.embeds[0]
        if e.footer.text.startswith("00"):
            await ctx.reply("already closed")
            return
        if msg.author.id != self.bot.user.id or not e.footer.text == str(channel.id):
            await ctx.reply("i can't edit that message", ephemeral=True)
            return

        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")

        pingc = msg.content
        
        if not e:
            ctx.reply("message may be invalid, please double check", ephemeral=True)
            return
        desc = e.description or ""

        odate_match = re.search(r"\[(\d{2}/\d{2}/\d{2}) CEST", desc.splitlines()[0]) if desc else None
        desc += "\n"

        if not odate_match or odate_match.group(1) != date:
            desc += f"-# `[{date}]`"

        desc += f"`[{time}]` {content}"

        embed = discord.Embed(
            title=e.title,
            description=desc,
            color=e.color
        ).set_footer(
            text=f"{channel.id}"
        )
        await msg.edit(embed=embed)

        if ping and pingc.strip():
            await channel.send(pingc, reference=msg)
        await ctx.reply("updated!", ephemeral=True)
    @commands.has_permissions(manage_messages=True)
    @status.command(name="close", description="resolve status event.")
    async def add(self, ctx, link: str, color_override: bool = True, ping: bool = True):
        parsed = parse_msglink(link)
        if not parsed:
            await ctx.reply("invalid link", ephemeral=True)
            return
        self.bot: commands.Bot
        gid, cid, mid = parsed
        channel: discord.TextChannel = self.bot.get_channel(cid)
        msg: discord.Message = await channel.fetch_message(mid)
        e = msg.embeds[0]
        if e.footer.text.startswith("00"):
            await ctx.reply("already closed")
            return
        if msg.author.id != self.bot.user.id or not e.footer.text == str(channel.id):
            await ctx.reply("i can't edit that message", ephemeral=True)
            return

        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")

        pingc = msg.content
        
        desc = e.description or ""
            
        odate_match = re.search(r"\[(\d{2}/\d{2}/\d{2}) CEST", desc.splitlines()[0]) if desc else None
        desc += "\n"

        if not odate_match or odate_match.group(1) != date:
            desc += f"-# `[{date}]`"

        desc += f"`[{time} - resolved]`"

        embed = discord.Embed(
            title=e.title + " - resolved",
            description=desc,
            color=e.color if not color_override else 0x17ff7f
        ).set_footer(
            text=f"00{channel.id}"
        )
        await msg.edit(embed=embed)

        if ping and pingc.strip():
            await channel.send(pingc, reference=msg)
        await ctx.reply("closed!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(utility(bot))
