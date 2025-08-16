import discord
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section
from ext.utils import xp_to_level


class ChangelogLayout(LayoutView):
    def __init__(self, bot: discord.ext.commands.Bot, commits: list):
        super().__init__()
        # latest commit (big display)
        latest = commits[0]
        latest_sha = latest["sha"][:7]
        latest_url = latest["html_url"]
        latest_author = latest["author"]["login"]
        latest_author_url = latest["author"]["html_url"]
        latest_message = latest["commit"]["message"]
        container = Container()
        container.add_item(TextDisplay("## recent updates"))
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                f"-# [`{latest_sha}`](<{latest_url}>) • [`{latest_author}`](<{latest_author_url}>)\n```\n{latest_message}```"
            )
        )
        container.add_item(Separator())
        commit_text = ""
        for commit in commits[1:6]:  # all 5 latest ones except for the first latest
            commit_text += (
                f"-# [`{commit["sha"][:7]}`](<{commit["html_url"]}>)"
                " • "
                f"[`{commit["author"]["login"]}`](<{commit["author"]["html_url"]}>) "
                f"`{commit["commit"]["message"].split('\n')[0]}`\n"
            )
        container.add_item(TextDisplay(commit_text))
        self.add_item(container)


class AboutLayout(LayoutView):
    def __init__(self, bot: discord.ext.commands.Bot, contributors: str):
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
            TextDisplay(
                "## contributors\n"
                f"[`contribute to codygen`](<https://github.com/tjf1dev/codygen>)\n{contributors}"
            )
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


class LevelupSection(Section):
    def __init__(
        self,
        user: discord.User,
        old_xp: int,
        xp: int,
        place_in_leaderboard: int,
        highest_boost: int,
    ):
        super().__init__(accessory=discord.ui.Thumbnail(user.avatar.url))
        self.add_item(
            TextDisplay(
                f"{user.mention}\n"
                f"## level up! `{xp_to_level(float(old_xp))}` > **`{xp_to_level(float(xp))}`**\n"
                f"{f'-# {highest_boost}% boost\n' if highest_boost != 0 else ''}"
                f"-# {xp}xp • #{place_in_leaderboard}"
            )
        )


class LevelupLayout(LayoutView):
    def __init__(
        self,
        user: discord.User,
        old_xp: int,
        xp: int,
        place_in_leaderboard: int,
        highest_boost: int,
    ):

        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(
            LevelupSection(user, old_xp, xp, place_in_leaderboard, highest_boost)
        )
