import discord
from discord.ui import LayoutView, TextDisplay, Container, Section


class LevelupSection(Section):
    def __init__(
        self,
        user: discord.User | discord.Member,
        xp: int,
        place_in_leaderboard: int,
        highest_boost: int,
        old_level: int,
        new_level: int,
    ):
        super().__init__(accessory=discord.ui.Thumbnail(user.display_avatar.url))
        self.add_item(
            TextDisplay(
                f"{user.mention}\n"
                f"## level up! `{old_level}` > **`{new_level}`**\n"
                f"{f'-# {highest_boost}% boost\n' if highest_boost != 0 else ''}"
                f"-# {xp}xp • #{place_in_leaderboard}"
            )
        )


class LevelupLayout(LayoutView):
    def __init__(
        self,
        user: discord.User | discord.Member,
        xp: int,
        place_in_leaderboard: int,
        highest_boost: int,
        old_level: int,
        new_level: int,
    ):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(
            LevelupSection(
                user,
                xp,
                place_in_leaderboard,
                highest_boost,
                old_level,
                new_level,
            )
        )
