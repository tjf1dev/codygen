from typing import Any
from discord.ui import (
    LayoutView,
    Container,
    TextDisplay,
    ActionRow,
    ChannelSelect,
    Select,
    Button,
)
import json
import discord
from ext.ui_base import Message
from models import Codygen, Event
from typing import TYPE_CHECKING, cast
from ext.colors import Color

if TYPE_CHECKING:
    from modules.logging import logging


class LogChannelSelect(ChannelSelect):
    def __init__(self, bot):
        self.bot: Codygen = bot
        super().__init__(
            channel_types=[discord.ChannelType.text],
            placeholder="log channel",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> Any:
        await interaction.response.send_message(
            view=LoggingSetupStage2(self.bot, selected_channel=self.values[0]),
            ephemeral=True,
        )  # stage 2: log channel selected


class EventTypeSelect(Select):
    def __init__(self, events: list[Event]):
        options = []
        for event in events:
            options.append(
                discord.SelectOption(
                    label=event.name,
                    description=f"category: {event.category_name}, id: {event.id}",
                    value=event.id,
                )
            )
        super().__init__(
            placeholder="events to log",
            options=options,
            min_values=1,
            max_values=len(options),
        )

    async def callback(self, interaction: discord.Interaction) -> Any:
        await interaction.followup.send(
            view=Message(f"events selected:\n {'\n'.join([e for e in self.values])}"),
            ephemeral=True,
        )


class LoggingSetupLayout(LayoutView):
    def __init__(self, bot: Codygen):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(
            TextDisplay(
                "## logging setup\n"
                "welcome! codygen's logging can help you monitor a lot of different aspects of your server, such as:\n"
                "> - deleted/edited messages\n"
                "> - member joins\n"
                "> - channel creation/deletion\n"
                "> - and more!\n"
                "to proceed, you must first select a **log channel**. this will be the channel all logs go to.\n"
                "it is recommended that the channel is private. you can change where each log gets sent later."
            )
        )
        row = ActionRow()
        row.add_item(LogChannelSelect(bot))
        container.add_item(row)


class LoggingSetupConfirm(Button):
    def __init__(self, bot: Codygen, channel: discord.TextChannel, events: list[Event]):
        self.bot = bot
        self.channel = channel
        self.events = events
        super().__init__(style=discord.ButtonStyle.primary, label="Finish setup")

    async def callback(self, interaction: discord.Interaction) -> Any:
        await interaction.response.defer()
        db = self.bot.db
        data = {
            e.id: {"channel": self.channel.id, "meta": e.__dict__} for e in self.events
        }
        data_str = json.dumps(data)
        await db.execute(
            "UPDATE guilds SET logging_settings=? WHERE guild_id=?",
            (
                data_str,
                interaction.guild_id,
            ),
        )
        await db.commit()
        await interaction.followup.send(
            view=Message(
                "## setup finished! <3",
                accent_color=Color.positive,
            ),
            ephemeral=True,
        )


class LoggingSetupStage2(LayoutView):
    def __init__(self, bot: Codygen, selected_channel):
        super().__init__()
        container = Container()
        self.add_item(container)
        # container.add_item(
        #     TextDisplay(
        #         f"now, select which events will be sent to {selected_channel.mention}. you can also use the default values"
        #     )
        # )
        # row2 = ActionRow()
        logging_cog = bot.get_cog("logging")
        assert logging_cog is not None
        logging_cog = cast("logging", logging_cog)
        events = logging_cog.list_events()
        # row2.add_item(EventTypeSelect(events=list(events.values())))
        # container.add_item(row2)
        container.add_item(
            TextDisplay(
                f"- log channel: {selected_channel.mention}\n - events (you can change this later):\n{'\n'.join([f'> - {e.name}' for e in events.values()])}"
            )
        )
        container.add_item(
            ActionRow().add_item(
                LoggingSetupConfirm(bot, selected_channel, list(events.values()))
            )
        )


class LoggingSetupStartButton(Button):
    def __init__(self, bot, user: discord.User):
        self.bot = bot
        self.user = user
        super().__init__(label="Start")

    async def callback(self, interaction: discord.Interaction) -> Any:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                view=Message("## you cannot interact with this message!")
            )
            return
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            view=LoggingSetupLayout(self.bot), ephemeral=True
        )


class LoggingSetupStart(LayoutView):
    def __init__(self, bot: Codygen, user: discord.User):
        super().__init__()
        container = Container()
        container.add_item(
            TextDisplay("## press the button below to start the logging setup")
        )
        self.add_item(container)
        container.add_item(ActionRow().add_item(LoggingSetupStartButton(bot, user)))
