from discord.ui import LayoutView, TextDisplay, Container, Separator
from models import Codygen


class ChangelogLayout(LayoutView):
    def __init__(self, bot: Codygen, commits: list):
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
                f"-# [`{commit['sha'][:7]}`](<{commit['html_url']}>)"
                " • "
                f"[`{commit['author']['login']}`](<{commit['author']['html_url']}>) "
                f"`{commit['commit']['message'].split('\n')[0]}`\n"
            )
        container.add_item(TextDisplay(commit_text))
        self.add_item(container)
