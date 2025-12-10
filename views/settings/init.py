import discord
from discord.ui import LayoutView, TextDisplay, Container, ActionRow
from ext.colors import Color
from ext.logger import logger
import os
from discord.ui import MediaGallery, Button
from ext.utils import setup_guild

class InitStartButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        self.label = "Start"
        self.style = discord.ButtonStyle.primary
        self.custom_id = "init_button"

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return
        if not interaction.guild:
            return
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="access denied",
                description="### you need admin to run this!",
                color=Color.negative,
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        self.disabled = True
        self.style = discord.ButtonStyle.secondary
        self.label = "please wait..."
        await interaction.edit_original_response(view=InitStartLayout(self.cog))
        logger.debug(f"starting initialization for guild {interaction.guild.id}")

        gen = setup_guild(self.cog.bot, interaction.guild, gtype=1)
        async for view in gen:
            await interaction.followup.send(view=view, ephemeral=True)


class InitStartLayout(LayoutView):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        container = Container()
        self.add_item(container)
        logger.debug(os.getcwd())
        image = MediaGallery().add_item(media="attachment://header.png")
        docs_button = Button(
            style=discord.ButtonStyle.url,
            url="https://codygen.tjf1.dev",
            label="Website",
        )
        row = ActionRow().add_item(InitStartButton(self.cog)).add_item(docs_button)

        container.add_item(image)
        container.add_item(
            TextDisplay(
                "# codygen\npress the button below to start initalization.\nthis will create a configuration and check for permissions"
            )
        )
        container.add_item(row)
