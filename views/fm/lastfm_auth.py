import discord
import os
from ext.logger import logger
from ext.utils import lfm_generate_full_state


class lastfmMessageWithLogin(discord.ui.LayoutView):
    def __init__(self, message, **container_options):
        super().__init__()
        container = discord.ui.Container(**container_options)
        self.add_item(container)
        container.add_item(discord.ui.TextDisplay(message))
        container.add_item(lastfmAuthPromptActionRow())


class lastfmAuthPromptActionRow(discord.ui.ActionRow):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Login", style=discord.ButtonStyle.secondary)
    async def auth_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            view = lastfmAuthFinal(interaction)
            await interaction.response.send_message(view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"{type(e)}: {e}")


class lastfmLoggedOutError(discord.ui.LayoutView):
    def __init__(self):
        super().__init__()

        container = discord.ui.Container()
        container.add_item(
            discord.ui.TextDisplay("## Not logged in!\nAuthorize with the button below")
        )
        container.add_item(lastfmAuthPromptActionRow())
        self.add_item(container)


class lastfmAuthFinalActionRow(discord.ui.ActionRow):
    def __init__(self, interaction: discord.Interaction):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                label="Authenticate",
                url=f"https://www.last.fm/api/auth?api_key={os.environ['LASTFM_API_KEY']}&cb={os.environ['LASTFM_CALLBACK_URL']}?state={lfm_generate_full_state(interaction.user.id)}",
            )
        )


class lastfmAuthFinal(discord.ui.LayoutView):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=None)
        container = discord.ui.Container()
        container.add_item(
            discord.ui.TextDisplay(
                f"## last.fm authentication\npress the button below to safely authenticate with last.fm as {interaction.user.name}"
            )
        )
        container.add_item(lastfmAuthFinalActionRow(interaction))
        self.add_item(container)
