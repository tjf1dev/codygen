import discord
from discord.ui import LayoutView, TextDisplay, Section, Thumbnail, Container, Separator


class AboutLayout(LayoutView):
    def __init__(self, bot, contributors):
        super().__init__()
        container = Container()
        container.add_item(
            TextDisplay(
                "# codygen\n"
                "made by [`tjf1`](<https://github.com/tjf1dev>)"
                " • "
                f"[`add codygen`](<https://discord.com/oauth2/authorize?client_id={bot.user.id})"
                # * this link won't work on private clients
            )
        ).add_item(Separator()).add_item(
            TextDisplay("## contributors\n" f"{contributors}")
        ).add_item(
            Separator()
        ).add_item(
            TextDisplay(
                "## support\n"
                "[`sponsor me on github <3`](<https://github.com/sponsors/tjf1dev>)\n"
                "it takes a long time making a bot, any support would be appreciated! :3"
            )
        ).add_item(
            Separator()
        ).add_item(
            TextDisplay(
                "thank you to **EVERYONE** (yes, you too) for making, contributing to, using codygen. without you, all of this wouldnt be possible </3"
            )
        )
        self.add_item(container)
