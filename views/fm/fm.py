import discord
import asyncio
from typing import cast
from ext.emotes import get_emote_sync


class fmActionRow(discord.ui.ActionRow):
    def __init__(self, track_info: dict):
        super().__init__()
        self.voted_users = {}  # {user_id: "up" or "down"}

        downvote = get_emote_sync("downvote")
        upvote = get_emote_sync("upvote")
        self.downvote.emoji = str(downvote)
        self.upvote.emoji = str(upvote)

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        label="0",
    )
    async def downvote(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        user_id = interaction.user.id
        buttons = [cast(discord.ui.Button, b) for b in self.children]
        upvote_button = next(
            b for b in buttons if b.emoji and getattr(b.emoji, "name", None) == "upvote"
        )

        current_vote = self.voted_users.get(user_id)

        if current_vote == "down":
            self.voted_users.pop(user_id)
            old_label = button.label or "0"
            button.label = str(int(old_label) - 1)
        elif current_vote == "up":
            self.voted_users[user_id] = "down"
            old_label = button.label or "0"
            button.label = str(int(old_label) + 1)
            old_upvote_label = upvote_button.label or "0"
            upvote_button.label = str(int(old_upvote_label) - 1)
        else:
            self.voted_users[user_id] = "down"
            old_label = button.label or "0"
            button.label = str(int(old_label) + 1)

        await interaction.edit_original_response(view=self.view)

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        label="0",
    )
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        user_id = interaction.user.id

        buttons = [cast(discord.ui.Button, b) for b in self.children]
        downvote_button = next(
            b
            for b in buttons
            if b.emoji and getattr(b.emoji, "name", None) == "downvote"
        )
        current_vote = self.voted_users.get(user_id)

        if current_vote == "up":
            self.voted_users.pop(user_id)
            old_label = button.label or "0"
            button.label = str(int(old_label) - 1)
        elif current_vote == "down":
            self.voted_users[user_id] = "up"
            old_label = button.label or "0"
            button.label = str(int(old_label) + 1)
            old_down_label = downvote_button.label or "0"
            downvote_button.label = str(int(old_down_label) - 1)
        else:
            self.voted_users[user_id] = "up"
            old_label = button.label or "0"
            button.label = str(int(old_label) + 1)

        await interaction.edit_original_response(view=self.view)


class fmLayout(discord.ui.LayoutView):
    def __init__(self, track_info: dict, timeout=None):
        super().__init__()
        container = discord.ui.Container()
        container.add_item(fmSection(track_info))
        # if interaction.guild:
        container.add_item(fmActionRow(track_info))
        self.add_item(container)


class fmSection(discord.ui.Section):
    def __init__(self, track_info: dict):
        accessory = discord.ui.Thumbnail(media=track_info["image"])

        super().__init__(accessory=accessory)
        display_text = (
            f"## [{track_info['track']}]({track_info['url']})\n"
            f"{track_info['artist']} {'• ' if track_info.get('album', None) else ''}{track_info.get('album', '')}\n"
            f"{track_info['track_scrobble_count']} scrobbles, "
            f"{track_info['scrobble_count']} total"
        )

        self.add_item(discord.ui.TextDisplay(display_text))
