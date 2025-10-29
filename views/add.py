import discord
from discord.ui import LayoutView, TextDisplay, Container, Section, Button, Separator
from ext.colors import Color


class AddLayout(LayoutView):
    def __init__(self, bot):
        super().__init__()
        aid = bot.user.id
        guild = f"https://discord.com/oauth2/authorize?client_id={aid}&integration_type=0&scope=bot%20applications.commands&permissions=8"
        user = f"https://discord.com/oauth2/authorize?client_id={aid}&integration_type=1&scope=applications.commands"
        container = Container(accent_color=Color.accent)
        self.add_item(container)

        server_add_section = Section(
            accessory=Button(
                style=discord.ButtonStyle.blurple, label="Server install", url=guild
            )
        )
        server_add_section.add_item(
            TextDisplay(
                "invite codygen to your server\nyou will be able to use leveling, moderation, etc."
            )
        )

        user_add_section = Section(
            accessory=Button(
                style=discord.ButtonStyle.blurple, label="User install", url=user
            )
        )
        user_add_section.add_item(
            TextDisplay(
                "add codygen to your profile.\nyou will be able to use it's commands everywhere."
            )
        )

        container.add_item(TextDisplay("## add codygen"))
        if not bot.release:
            container.add_item(
                TextDisplay(
                    "> **warning!**\n> this version is not marked as a release target.\n> the installation links may not work"
                )
            )
        container.add_item(Separator())
        container.add_item(server_add_section)
        container.add_item(Separator())
        container.add_item(user_add_section)
