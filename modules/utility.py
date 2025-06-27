import re
import time
import psutil
import sys
import os
import aiohttp
import discord
import ext.errors
from discord.ext import commands
from discord import app_commands
from main import logger, Color, verify, get_global_config, version
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def parse_msglink(link: str):
    match = re.match(
        r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)",
        link,
    )
    if match:
        guild_id, channel_id, message_id = map(int, match.groups())
        return guild_id, channel_id, message_id
    return None


class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        options = []
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                if cog_name.lower() in ["jishaku"]:
                    pass
                else:
                    description = getattr(
                        cog, "description", "no description available."
                    )
                    options.append(
                        discord.SelectOption(
                            label=cog_name.lower(), description=description.lower()
                        )
                    )
        else:
            # add a fallback option if no cogs are loaded
            options.append(
                discord.SelectOption(
                    label="No Modules Loaded", description="Failed to load module list."
                )
            )
        super().__init__(
            placeholder="Select a cog", max_values=1, min_values=1, options=options
        )
    # hey, for self-hosted users: #! please don’t remove this command
    # i get it, you want your own bot, but at least give me some credit for this
    # if you really want your own bot, make one yourself
    # tip: codygen works under the MIT license. #* REMOVING CREDIT IS ILLEGAL.
    # you can do whatever you want with it, but #* if you redistribute this code without credit, you’re BREAKING THE LAW.
    # enjoy using codygen!
    @commands.command()
    async def whoami(self, ctx: commands.Context):
        await ctx.reply(
            embed=discord.Embed(
                title="",
                description="# codygen\n### made by [tjf1](https://tjf1dev/codygen)\nMIT licensed. you can do whatever, but don't remove credit if you're redistributing - it's required by the license, and somewhat illegal ;3\n-# for more information, read LICENSE, or the comment above this command ([cog utility.py, line 47](<https://github.com/tjf1dev/codygen/blob/main/cogs/utility.py#L47-L52>))",
                color=Color.negative,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"codygen - {self.values[0]}", color=Color.white)
        if self.values[0] == "No Modules Loaded":
            fail = discord.Embed(
                title="failed to load the list of modules",
                description="please report this issue.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
            return
        cog = self.bot.get_cog(self.values[0])

        if cog is None:
            fail = discord.Embed(
                title="failed to load :broken_heart:",
                description=f"module {self.values[0]} (cogs.{self.values[0]}) failed to load.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
            return
        elif len(cog.get_commands()) == 0:
            fail = discord.Embed(
                title="its quiet here...",
                description=f"cogs.{self.values[0]} doesnt have any commands.",
                color=Color.negative,
            )
            await interaction.response.edit_message(embed=fail)
        else:
            for command in cog.walk_commands():
                description = (
                    command.description
                    if command.description != ""
                    else "Figure it out yourself (no description provided)"
                )
                embed.add_field(
                    name=f"/{command.full_parent_name} {command.name}",
                    value=f"```{description}```",
                    inline=False,
                )
            await interaction.response.edit_message(
                embed=embed, view=HelpHomeView(self.bot)
            )


class HelpWiki(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Documentation",
            style=discord.ButtonStyle.link,
            url="https://github.com/tjf1dev/codygen/wiki",
        )


class HelpHomeView(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(HelpSelect(bot))
        self.add_item(HelpWiki())


class utility(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.description = "tools that can be helpful sometimes!"
    # deltarune,, nevr heard of this game smh
    # @tasks.loop(hours=24)
    # async def countdown_loop(self):
    #     target_date = datetime(datetime.now().year, 6, 4)
    #     channel = self.bot.get_channel(1374402713118572635)
    #     now = datetime.now()
    #     if now > target_date:
    #         await channel.send("deltarune tomorrow :3 (it's out)")
    #         self.countdown_loop.stop()
    #     else:
    #         days_left = (target_date - now).days
    #         if days_left == 1:
    #             await channel.send("deltarune tomorrow")
    #         else:
    #             await channel.send(f"{days_left} days until deltarune")

    # @countdown_loop.before_loop
    # async def before_countdown(self):
    #     await self.bot.wait_until_ready()
    #     now = datetime.now()
    #     next_midnight = datetime.combine(
    #         now.date() + timedelta(days=1), datetime.min.time()
    #     )
    #     seconds_until_midnight = (next_midnight - now).total_seconds()
    #     await asyncio.sleep(seconds_until_midnight)

    @commands.Cog.listener()
    async def on_ready(self):
        # if not self.countdown_loop.is_running():
        #     self.countdown_loop.start()
        logger.info(f"{self.__class__.__name__}: loaded.")

    @commands.hybrid_group(
        name="utility", description="tools that can be helpful sometimes!"
    )
    async def utility(self, ctx: commands.Context):
        await ctx.reply("utility")

    @utility.command(name="pfp", description="get someone's pfp")
    async def pfp(self, ctx: commands.Context, user: discord.User = None):
        if user is None:
            user = ctx.author
        avatar = user.avatar.url
        embed = discord.Embed(color=0x8FF0A4)
        embed.set_image(url=avatar)
        await ctx.reply(embed=embed)

    @commands.has_permissions(manage_messages=True)
    @utility.group(name="status", description="status updates for various things")
    async def status(self, ctx: commands.Context):
        pass

    @commands.has_permissions(manage_messages=True)
    @status.command(
        name="post",
        description="status updates for various things, post update. timestamps are in CEST",
    )
    async def status_post(
        self,
        ctx: commands.Context,
        initial: str,
        title: str = "Downtime",
        channel: discord.TextChannel = None,
        ping: discord.Role = None,
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
            f"posted to {channel.mention}!\nlink: `{msg.jump_url}` ({msg.jump_url})",
            ephemeral=True,
        )

    @commands.has_permissions(manage_messages=True)
    @status.command(name="add", description="add an event to a status.")
    async def status_add(
        self, ctx: commands.Context, link: str, content: str, ping: bool = False
    ):
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

    @commands.has_permissions(manage_messages=True)
    @status.command(name="close", description="resolve status event.")
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
            title=e.title + " - resolved",
            description=desc,
            color=e.color if not color_override else 0x17FF7F,
        ).set_footer(text=f"00{channel.id}")
        await msg.edit(embed=embed)

        if ping and pingc.strip():
            await channel.send(pingc, reference=msg)
        await ctx.reply("closed!", ephemeral=True)

    @verify()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="ping", description="shows how well is codygen doing!"
    )
    async def ping(self, ctx: commands.Context):
        client = self.bot
        e = discord.Embed(
            title=f"codygen v{version}",
            description="### hii :3 bot made by `tjf1`\nuse </help:1338168344506925108> for command list +more",
            color=Color.accent,
        )
        e.set_thumbnail(url=self.bot.user.avatar.url)
        e.add_field(
            name="ping", value=f"`{round(self.bot.latency * 1000)} ms`", inline=True
        )
        current_time = time.time()
        difference = int(round(current_time - self.bot.start_time))
        uptime = str(timedelta(seconds=difference))
        e.add_field(name="uptime", value=f"`{uptime}`", inline=True)
        process = psutil.Process(os.getpid())
        ram_usage = process.memory_info().rss / 1024**2
        total_memory = psutil.virtual_memory().total / 1024**2
        e.add_field(
            name="ram usage",
            value=f"`{ram_usage:.2f} MB / {total_memory:.2f} MB`",
            inline=True,
        )
        cpu_usage = psutil.cpu_percent(interval=1)
        e.add_field(name="cpu usage", value=f"`{cpu_usage}%`", inline=True)
        # nerdy ahh logic
        commands_list = [
            command.name
            for command in client.commands
            if not isinstance(command, commands.Group)
        ] + [
            command.name
            for command in client.tree.walk_commands()
            if not isinstance(command, commands.Group)
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
            inline=True,
        )
        e.add_field(
            name="servers",
            value=f"`codygen is in {len(client.guilds)} servers.`",
            inline=True,
        )
        e.add_field(
            name="users", value=f"`serving {len(client.users)} users.`", inline=True
        )
        e.add_field(
            name="system info",
            value=f"`running discord.py {discord.__version__} on python {sys.version.split()[0]}`",
            inline=True,
        )
        await ctx.reply(embed=e, ephemeral=False)

    @verify()
    @commands.hybrid_command(
        name="help", description="shows useful info about the bot."
    )
    async def help_command(self, ctx: commands.Context):
        embed = discord.Embed(
            title="",
            description="# codygen\ncode: <https://github.com/tjf1dev/codygen>\nuse the menu's below to search for commands and their usages.",  # i can change it now
            color=Color.purple,
        )
        await ctx.reply(embed=embed, view=HelpHomeView(self.bot), ephemeral=True)
    @verify()
    @commands.hybrid_command(
        name="add",
        description="shows useful info about the bot"
    )
    async def add(self, ctx: commands.Context):
        bid = os.getenv("APP_ID")
        guild = f"https://discord.com/oauth2/authorize?client_id={bid}&permissions=8&scope=applications.commands+bot"
        user = f"https://discord.com/oauth2/authorize?client_id={bid}&permissions=8&integration_type=1&scope=applications.commands"
        e = discord.Embed(
            description="# add codygen\n"
            f"## [server]({guild})\n"
            "use the link above to invite codygen to your server. this is the regular way of adding bots\n"
            f"## [user install]({user})\n"
            "use this link to install codygen to your user. you will be able to use it's commands anywhere\n\n"
            f"-# [about codygen](https://github.com/tjf1dev/codygen)",
            color=Color.accent,
        )
        await ctx.reply(embed=e, ephemeral=False)


    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @commands.hybrid_command(
        name="about",
        description="view detailed information about codygen, including contributors, etc.",
    )
    async def about(self, ctx: commands.Context):
        repo: str = get_global_config()["commands"].get("about", {"repo": ""})[
            "repo"
        ]
        if not len(repo.split("/")) == 2:
            raise ext.errors.MisconfigurationError(
                f"commands > about > repo: please make sure the value is in the format or AUTHOR/REPO, e.g tjf1dev/codygen, debug: {repo.split("/")}"
            )
        api_url = f"https://api.github.com/repos/{repo}/contributors"
        headers = {}
        token = os.getenv("GITHUB_PAT")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(api_url, headers=headers) as res:
                    if res.status != 200:
                        text = await res.text()
                        raise ext.errors.DefaultError(f"HTTP {res.status}: {text}")
                    data = await res.json()
            except aiohttp.ClientConnectionError as e:
                raise ext.errors.DefaultError(
                    f"connection closed while reading json: {e}"
                )
            except aiohttp.ContentTypeError:
                text = await res.text()
                raise ext.errors.DefaultError(f"response is not json: {text}")
            except Exception as e:
                raise ext.errors.DefaultError(f"unexpected error parsing json: {e}")

        contributors = ""
        for c in data:
            contributors += f"[`{c["login"]}`](<{c["html_url"]}>): {c["contributions"]} contributions\n"

        e = discord.Embed(
            description=f"""
            # codygen\n
            ### made by [`tjf1`](<https://github.com/tjf1dev>)\n
            ## contributors\n{contributors}
            ## support\n
            it takes a long time making a bot, any support would be appreciated! :3\n
            ### [`sponsor me on github <3`](<https://github.com/sponsors/tjf1dev>)\n\n
            thank you to **EVERYONE** (yes, you too) for making, contributing to, using codygen. without you, all of this wouldnt be possible </3
            """,
            color=Color.accent,
        )
        await ctx.reply(embed=e)

    # now some exclusives i need for my server
    # guild id will be hardcoded
    import re

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        if message.guild.id != 1333785291584180244:
            return

        if message.author.bot:
            return

        url_pattern = re.compile(
            r"https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\.(?:png|jpg|jpeg|gif|webp|bmp)"
        )
        urls = url_pattern.findall(message.content)

        if urls:
            perms = message.channel.permissions_for(message.author)
            return
            if not perms.embed_links:
                sticker = await message.guild.fetch_sticker(1370752176787558451)
                if sticker:
                    await message.reply(stickers=[sticker])
                    return
                else:
                    return
            else:
                return
        else:
            return


async def setup(bot):
    await bot.add_cog(utility(bot))
