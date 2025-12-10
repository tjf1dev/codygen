from discord import Interaction, InteractionMessage
from discord.ui import (
    LayoutView,
    TextDisplay,
    Container,
    Modal,
    Label,
    TextInput,
    ActionRow,
    Button,
    ChannelSelect,
)
from typing import cast
from ext.ui_base import Message
from models import Codygen

# havent done modals for like 2 years im scared


class LevelSetupStartButton(Button):
    def __init__(self, bot: Codygen, user_id: int):
        self.bot = bot
        self.user_id = user_id
        super().__init__(label="Start")

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.send_modal(LevelSetupModal(self.bot, False))


class LevelSetupLayout(LayoutView):
    def __init__(self, bot: Codygen, user_id: int):
        self.bot = bot
        self.user_id = user_id
        super().__init__()
        cont = Container()
        self.add_item(cont)
        cont.add_item(
            TextDisplay(
                "## level setup\npress the button below to start setup\n-# tip: using the slash command skips directly to the setup"
            )
        )
        cont.add_item(
            ActionRow().add_item(LevelSetupStartButton(self.bot, self.user_id))
        )


class LevelSetupModal(Modal):
    def __init__(self, bot: Codygen, app_command: bool = True) -> None:
        self.bot = bot
        self.app_command = app_command
        super().__init__(title="codygen - leveling setup")
        self.add_item(
            TextDisplay(
                "## set up leveling\nto use leveling you must set **xp per message** and a **levelup channel** (optional)."
            )
        )
        self.add_item(
            Label(
                text="XP per message",
                id=0,
                description="the integer xp value each member will receive upon sending a message. input 0 to disable.",
                component=TextInput(placeholder="number", default="10"),
            )
        )
        self.add_item(
            Label(
                text="levelup channel",
                id=1,
                description="the channel level up messages will get sent to. optional",
                component=ChannelSelect(),
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        xp_label = cast(Label, self.find_item(0))
        xp_input = cast(TextInput, xp_label.component)
        channel_label = cast(Label, self.find_item(1))
        channel_input = cast(ChannelSelect, channel_label.component)
        response = Message(
            f"## level setup\n"
            f"{self.bot.emote('loading')} submitting values... please wait\n"
            f"xp per message: `{int(xp_input.value)}\n`"
            f"level up channel: {channel_input.values[0].mention}\n"
        )
        fail = False
        if not xp_input.value.isdigit():
            response = Message(
                "## failed!\n"
                f"`{xp_input.value}` is not a number.\n"
                f"please make sure that xp per message is a valid integer."
            )
            fail = True
        if not self.app_command:
            await interaction.response.defer()
            msg = await interaction.edit_original_response(view=response)
        else:
            msg = cast(
                InteractionMessage,
                (await interaction.response.send_message(view=response)).resource,
            )

        if fail:
            return
        db = self.bot.db

        level_per_message = int(xp_input.value) if xp_input.value else None
        levelup_channel = channel_input.values[0].id if channel_input.values else None

        if level_per_message is not None or levelup_channel is not None:
            sql_parts = []
            params = []

            if level_per_message is not None:
                sql_parts.append("level_per_message = ?")
                params.append(level_per_message)

            if levelup_channel is not None:
                sql_parts.append("levelup_channel = ?")
                params.append(levelup_channel)

            sql = f"UPDATE guilds SET {', '.join(sql_parts)} WHERE guild_id = ?"
            params.append(interaction.guild_id)

            await db.execute(sql, params)
            await db.commit()
        await msg.edit(
            view=Message(
                f"## {self.bot.emote('success')} level setup\n"
                f"xp per message: `{int(xp_input.value)}\n`"
                f"level up channel: {channel_input.values[0].mention}\n"
            )
        )
