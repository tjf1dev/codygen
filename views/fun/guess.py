from typing import Any, cast
import discord
from discord import ButtonStyle
from discord.ui import (
    LayoutView,
    Section,
    TextDisplay,
    Container,
    Modal,
    Button,
    Thumbnail,
    Label,
    ActionRow,
    TextInput,
)
from ext.colors import Color
import random


class GuessButton(Button):
    def __init__(
        self,
        *,
        user,
        style: discord.ButtonStyle = ButtonStyle.primary,
        label: str | None = "guess!",
    ):
        self.user = user
        super().__init__(style=style, label=label)

    async def callback(self, interaction: discord.Interaction) -> Any:
        await interaction.response.send_modal(GuessInputModal(correct=self.user))


class GuessInputModal(Modal):
    def __init__(self, correct) -> None:
        self.correct = correct
        super().__init__(title="guess user", timeout=30)

    guess = Label(text="who do you think this user is?", component=TextInput())

    async def on_submit(self, interaction: discord.Interaction):
        correct: discord.Member | discord.User = self.correct
        guess = cast(TextInput, self.guess.component).value
        is_correct = guess.lower() in [
            correct.name.lower(),
            correct.display_name.lower(),
        ]
        await interaction.response.send_message(
            view=LayoutView().add_item(
                Container(accent_color=Color.positive if is_correct else Color.negative)
                .add_item(
                    TextDisplay(
                        f"{interaction.user.mention} guessed that this was `{guess}`\n## {'in' if not is_correct else ''}correct!\nthe user was: {correct.mention}"
                    )
                )
                .add_item(ActionRow().add_item(GuessNewGameButton()))
            ),
            allowed_mentions=discord.AllowedMentions().none(),
        )


class GuessNewGameButton(Button):
    def __init__(
        self, *, style: ButtonStyle = ButtonStyle.secondary, label: str | None = "next"
    ):
        super().__init__(style=style, label=label)

    async def callback(self, interaction: discord.Interaction) -> Any:
        if not interaction.guild:
            return
        users = interaction.guild.members
        while True:
            user = random.choice(users)
            if not user.bot and user.avatar:
                break
        if interaction.message:
            await interaction.message.edit(view=GuessLayout(user=user))
        else:
            await interaction.response.send_message(view=GuessLayout(user=user))


class GuessLayout(LayoutView):
    def __init__(self, *, user: discord.User | discord.Member) -> None:
        self.user = user
        super().__init__(timeout=30)
        assert user.avatar is not None
        container = Container(accent_color=Color.accent_og)
        row = ActionRow().add_item(GuessButton(user=user))
        section = Section(accessory=Thumbnail(media=user.avatar.url)).add_item(
            TextDisplay("# guess the user!\nwho do you think this is?")
        )
        container.add_item(section)
        container.add_item(row)
        self.add_item(container)
