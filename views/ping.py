import discord
import time
import datetime
import psutil
import os
import sys
from ext.utils import parse_commands
from models import Codygen
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section


class PingSection(Section):
    def __init__(self, bot: Codygen):
        if not bot.user:
            return
        super().__init__(accessory=discord.ui.Thumbnail(bot.user.display_avatar.url))
        self.add_item(
            TextDisplay(
                f"## codygen {bot.version}\nmultipurpose discord by tjf1 and more"
            )
        )


class PingLayout(LayoutView):
    def __init__(self, bot: Codygen):
        super().__init__()
        commands_list = parse_commands(bot.full_commands)
        current_time = time.time()
        difference = int(round(current_time - bot.start_time))
        uptime = datetime.timedelta(seconds=difference)
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        process = psutil.Process(os.getpid())

        uptime = f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"
        uptime_alt = f"{days} day{'s' if days != 1 else ''}, {hours} hour{'s' if hours != 1 else ''}, {minutes} minute{'s' if minutes != 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"

        ram_usage = process.memory_info().rss / 1024**2
        total_memory = psutil.virtual_memory().total / 1024**2
        cpu_usage = psutil.cpu_percent(interval=1)

        container = Container()
        self.add_item(container)
        container.add_item(PingSection(bot))
        container.add_item(TextDisplay(f"### latency: `{round(bot.latency * 1000)}ms`"))
        container.add_item(Separator())
        container.add_item(TextDisplay(f"### uptime\n`{uptime_alt}`"))
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                f"### usage\n`RAM: {ram_usage:.0f} MB / {total_memory:.0f} MB CPU: {cpu_usage}%`"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                f"### stats\n`{len(commands_list)} commands`\n`{len(bot.guilds)} servers`\n`{len(bot.users)} users`"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                f"### runtime\n`running discord.py {discord.__version__} on python {sys.version.split()[0]}`"
            )
        )
