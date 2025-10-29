import re
import time
import os
import aiohttp
import discord
import aiosqlite
from models import Codygen
from discord.ext import commands
from discord import app_commands
from main import logger, Color
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image
from io import BytesIO
from typing import cast
from ext.ui_base import Message
from main import get_prefix


async def image_url_to_gif(url: str) -> str:
    os.makedirs("cache/converted", exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download image: {resp.status}")
            data = await resp.read()
    img = Image.open(BytesIO(data)).convert("RGBA")
    filename = f"{time.time()}.gif"
    output_path = os.path.join("cache", filename)
    img.save(output_path, format="GIF")
    return output_path


def parse_msglink(link: str):
    match = re.match(
        r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)",
        link,
    )
    if match:
        guild_id, channel_id, message_id = map(int, match.groups())
        return guild_id, channel_id, message_id
    return None


class MessageLayout(discord.ui.LayoutView):
    def __init__(self, message: str, **kwargs):
        super().__init__()

        accent_color = kwargs.get("accent_color", None)
        container = discord.ui.Container(accent_color=accent_color)
        container.add_item(discord.ui.TextDisplay(message))

        self.add_item(container)


class FailedToConvertLayout(MessageLayout):
    def __init__(self, **kwargs):
        super().__init__(
            "## No attachments found in this message.\nPlease make sure you select a message with an image to convert it into a GIF.",
            **kwargs,
        )


class GIFMediaGallery(discord.ui.MediaGallery):
    def __init__(self, attachments: list[discord.File]):
        super().__init__()

        for file in attachments:
            self.add_item(media=f"attachment://{file.filename}")


class GIFMediaLayout(discord.ui.LayoutView):
    def __init__(self, paths: list[discord.File], **kwargs):
        super().__init__()

        accent_color = kwargs.get("accent_color", None)
        container = discord.ui.Container(accent_color=accent_color)
        # container.add_item(discord.ui.TextDisplay(message))
        container.add_item(GIFMediaGallery(paths))

        self.add_item(container)


@app_commands.context_menu(name="Convert to GIF")
async def convert_to_gif(interaction: discord.Interaction, message: discord.Message):
    attachments = message.attachments
    await interaction.response.defer(ephemeral=True)

    if not attachments:
        await interaction.followup.send(view=FailedToConvertLayout(), ephemeral=True)
        return

    paths = []
    files = []
    for attachment in attachments:
        path = await image_url_to_gif(attachment.url)
        paths.append(path)
        files.append(discord.File(path))

    view = GIFMediaLayout(paths=files)
    await interaction.followup.send(files=files, view=view, ephemeral=True)
    for file in files:
        try:
            os.remove(file.fp.name)
        except Exception as e:
            logger.warning(f"Failed to delete {file.fp.name}: {e}")


class utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "helpful tools you might need"

    # hey, for self-hosted users: #! please don’t remove this command
    # i get it, you want your own bot, but at least give me some credit for this
    # if you really want your own bot, make one yourself
    # tip: codygen works under the MIT license.
    # you can do whatever you want with it, but if redestributing without credit is somewhat illegal
    # enjoy using codygen!
    @commands.command()
    async def whoami(self, ctx: commands.Context):
        await ctx.reply(
            embed=discord.Embed(
                title="",
                description="# codygen\n### made by [tjf1](https://tjf1dev/codygen)\nMIT licensed. you can do whatever, but don't remove credit if you're redistributing - it's required by the license, and somewhat illegal\n-# for more information, read LICENSE, or the comment above this command ([cog utility.py](<https://github.com/tjf1dev/codygen/blob/main/cogs/utility.py>))",
                color=Color.negative,
            )
        )

    async def cog_load(self):
        self.bot.tree.add_command(convert_to_gif)
        logger.debug("added convert to gif command")
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.hybrid_group(
        name="utility", description="tools that can be helpful sometimes!"
    )
    async def utility(self, ctx: commands.Context):
        await ctx.reply("utility")

    # TODO components v2-ify this
    @utility.command(name="pfp", description="get someone's pfp")
    async def pfp(
        self, ctx: commands.Context, user: discord.Member | discord.User | None = None
    ):
        if user is None:
            user = ctx.author
        avatar = user.display_avatar.url
        embed = discord.Embed(color=0x8FF0A4)
        embed.set_image(url=avatar)
        await ctx.reply(embed=embed)

    @app_commands.checks.has_permissions(manage_messages=True, manage_channels=True)
    @commands.has_guild_permissions(manage_messages=True, manage_channels=True)
    @utility.group(name="status", description="status updates for various things")
    async def status(self, ctx: commands.Context):
        pass

    @app_commands.checks.has_permissions(manage_messages=True, manage_channels=True)
    @commands.has_guild_permissions(manage_messages=True, manage_channels=True)
    @status.command(
        name="post",
        description="status updates for various things, post update. timestamps are in CEST",
    )
    @app_commands.describe(
        initial="first entry in the status log",
        title="title of this status log",
        channel="channel to post the message to",
        ping="role to ping on (every) update",
    )
    async def status_post(
        self,
        ctx: commands.Context,
        initial: str,
        title: str = "Downtime",
        channel=None,
        ping: discord.Role | None = None,
    ):
        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        if not channel:
            channel = ctx.channel
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")
        e = discord.Embed(
            title=title,
            description=f"-# `[{date} CEST • dynamic status updates by codygen]`\n"
            f"`[{time}]` {initial}",
            color=0x4775FF,
        ).set_footer(text=f"{channel.id}")
        content = ""
        if ping:
            content = ping.mention
        msg = await channel.send(content, embed=e)
        await ctx.reply(
            f"posted to {channel.mention}!\nlink: `{msg.jump_url}` ({msg.jump_url})",  # type: ignore
            ephemeral=True,
        )

    @app_commands.checks.has_permissions(manage_messages=True, manage_channels=True)
    @commands.has_guild_permissions(manage_messages=True, manage_channels=True)
    @status.command(name="add", description="add an event to a status.")
    @app_commands.describe(
        link="link to the original message",
        content="entry to be added to the message",
        ping="whether to ping the specified role again (defaults to true)",
    )
    async def status_add(
        self, ctx: commands.Context, link: str, content: str, ping: bool = True
    ):
        parsed = parse_msglink(link)
        if not parsed:
            await ctx.reply("invalid link", ephemeral=True)
            return
        self.bot: commands.Bot
        gid, cid, mid = parsed
        channel: discord.TextChannel = self.bot.get_channel(cid)  # type: ignore
        msg: discord.Message = await channel.fetch_message(mid)
        e = msg.embeds[0]
        if e.footer.text.startswith("00"):  # type:ignore
            await ctx.reply("already closed")
            return
        if not self.bot.user:
            return
        if msg.author.id != self.bot.user.id or not e.footer.text == str(channel.id):
            await ctx.reply("i can't edit that message", ephemeral=True)
            return

        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")

        pingc = msg.content

        if not e:
            await ctx.reply(
                "message may be invalid, please double check", ephemeral=True
            )
            return
        desc = e.description or ""

        odate_match = (
            re.search(r"\[(\d{2}/\d{2}/\d{2}) CEST", desc.splitlines()[0])
            if desc
            else None
        )
        desc += "\n"

        if not odate_match or odate_match.group(1) != date:
            desc += f"-# `[{date}]`"

        desc += f"`[{time}]` {content}"

        embed = discord.Embed(
            title=e.title, description=desc, color=e.color
        ).set_footer(text=f"{channel.id}")
        await msg.edit(embed=embed)

        if ping and pingc.strip():
            await channel.send(pingc, reference=msg)
        await ctx.reply("updated!", ephemeral=True)

    @app_commands.checks.has_permissions(manage_messages=True, manage_channels=True)
    @commands.has_guild_permissions(manage_messages=True, manage_channels=True)
    @status.command(name="close", description="resolve status event.")
    @app_commands.describe(
        link="link to the original message",
        color_override="whether to make the color go green (defaults to true)",
        ping="whether to ping the original role",
    )
    async def status_close(
        self,
        ctx: commands.Context,
        link: str,
        color_override: bool = True,
        ping: bool = True,
    ):
        parsed = parse_msglink(link)
        if not parsed:
            await ctx.reply("invalid link", ephemeral=True)
            return
        gid, cid, mid = parsed
        self.bot: commands.Bot
        channel = cast(discord.abc.MessageableChannel, self.bot.get_channel(cid))
        msg: discord.Message = await channel.fetch_message(mid)
        e = msg.embeds[0]
        if e.footer.text.startswith("00"):  # type: ignore
            await ctx.reply("already closed")
            return
        if msg.author.id != self.bot.user.id or not e.footer.text == str(channel.id):  # type: ignore
            await ctx.reply("i can't edit that message", ephemeral=True)
            return

        now_cest = datetime.now(ZoneInfo("Europe/Warsaw"))
        date = now_cest.strftime("%d/%m/%y")
        time = now_cest.strftime("%H:%M:%S")

        pingc = msg.content
        desc = e.description or ""

        odate_match = (
            re.search(r"\[(\d{2}/\d{2}/\d{2}) CEST", desc.splitlines()[0])
            if desc
            else None
        )
        desc += "\n"

        if not odate_match or odate_match.group(1) != date:
            desc += f"-# `[{date}]`"

        desc += f"`[{time} - resolved]`"

        embed = discord.Embed(
            title=e.title + " - resolved",  # type: ignore
            description=desc,
            color=e.color if not color_override else 0x17FF7F,
        ).set_footer(text=f"00{channel.id}")
        await msg.edit(embed=embed)

        if ping and pingc.strip():
            await channel.send(pingc, reference=msg)
        await ctx.reply("closed!", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.bot.user:
            return
        if message.author.bot:
            return
        if message.content.strip() == f"<@{self.bot.user.id}>":
            e = Message(
                message=f"# hey there! im codygen\n### try using </help:1338168344506925108>! the prefix for this server is: `{await get_prefix(self.bot, message)}`",
                accent_color=Color.accent,
            )
            await message.reply(view=e)

    # * maybe move this to a different cog?
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @utility.group(
        name="tag", description="commands related to server tags (primary guilds)"
    )
    async def tag_group(self, ctx: commands.Context): ...

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @tag_group.command(
        name="claim",
        description="grants the role for having the current server's tag",
    )
    async def claim_tag(self, ctx: commands.Context):
        db: aiosqlite.Connection = cast(Codygen, self.bot).db
        if not ctx.guild or not isinstance(ctx.author, discord.Member):
            return
        role = await (
            await db.execute(
                "SELECT role_id FROM primary_guild_roles WHERE guild_id=?",
                (ctx.guild.id,),
            )
        ).fetchone()
        if ctx.author.primary_guild.id != ctx.guild.id:
            if role:
                await ctx.author.remove_roles(
                    discord.Object(role[0]), reason="primary guild change"
                )
            await ctx.reply(
                view=Message(
                    "your server tag isn't from this server!",
                    accent_color=Color.negative,
                ),
                allowed_mentions=discord.AllowedMentions.none(),
            )

        if ctx.author.primary_guild.id == ctx.guild.id and ctx.author.primary_guild.tag:
            if role:
                if any(r.id == role for r in ctx.author.roles):
                    await ctx.reply(
                        view=Message("you already have this server's tag role!"),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                await ctx.author.add_roles(
                    discord.Object(role[0]), reason="primary guild claim"
                )
                await ctx.reply(
                    view=Message(
                        f"your server tag (`{ctx.author.primary_guild.tag}`) is from this server!\nthe <@&{role[0]}> role has been granted."
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                logger.debug(
                    f"adding role {role[0]} to {ctx.author.id} for primary guild {ctx.author.primary_guild.id}"
                )
            else:
                await ctx.reply(
                    view=Message(
                        f"your server tag (`{ctx.author.primary_guild.tag}`) is from this server, but there is no tag role. try contacting server administrators!",
                        accent_color=Color.negative,
                    ),
                    allowed_mentions=discord.AllowedMentions.none(),
                )

    # detect primary guild changes
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return
        if before.primary_guild.id != after.primary_guild.id:
            db: aiosqlite.Connection = cast(Codygen, self.bot).db
            # change previous guild
            oldrole = await (
                await db.execute(
                    "SELECT role_id FROM primary_guild_roles WHERE guild_id=?",
                    (before.guild.id,),
                )
            ).fetchone()
            if oldrole:
                await before.remove_roles(
                    discord.Object(oldrole[0]), reason="primary guild change"
                )
                logger.debug(
                    f"removing role {oldrole[0]} from {before.id} for primary guild change from {before.primary_guild.id}"
                )
            # change new guild
            role = await (
                await db.execute(
                    "SELECT role_id FROM primary_guild_roles WHERE guild_id=?",
                    (after.guild.id,),
                )
            ).fetchone()
            if role:
                await after.add_roles(
                    discord.Object(role[0]), reason="primary guild change"
                )
                logger.debug(
                    f"adding role {role[0]} to {after.id} for primary guild {after.primary_guild.id}"
                )


async def setup(bot):
    await bot.add_cog(utility(bot))
