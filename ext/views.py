import discord
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section, ActionRow
from ext.utils import xp_to_level
import time
from ext.utils import timestamp
from ext.colors import Color
from ext.utils import parse_commands
from ext.ui_base import Message
from discord.ext import commands


class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        options = []

        all_custom_commands = parse_commands(bot.full_commands)
        custom_full_names = {cmd["full_name"] for cmd in all_custom_commands}
        options.append(
            discord.SelectOption(label="home", description="go back to the home page")
        )
        if bot.cogs:
            for cog_name, cog in bot.cogs.items():
                if cog_name.lower() in ["jishaku"]:
                    continue
                cog_commands = list(cog.walk_commands())

                def get_full_command_name(cmd):
                    return (
                        f"{cmd.full_parent_name} {cmd.name}"
                        if cmd.full_parent_name
                        else cmd.name
                    )

                has_custom_command = any(
                    get_full_command_name(cmd) in custom_full_names
                    for cmd in cog_commands
                )

                if has_custom_command:
                    description = getattr(
                        cog, "description", "no description available."
                    )
                    options.append(
                        discord.SelectOption(
                            label=cog_name.lower(), description=description.lower()
                        )
                    )
        else:
            options.append(
                discord.SelectOption(
                    label="No Modules Loaded", description="Failed to load module list."
                )
            )

        super().__init__(
            placeholder="Select a cog", max_values=1, min_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_cog_name = self.values[0]
        if selected_cog_name == "home":
            await interaction.response.edit_message(view=HelpHomeView(self.bot))
            return
        cog = self.bot.get_cog(selected_cog_name)

        if cog is None:
            fail = Message(
                f"## failed to load :broken_heart:\nmodule {selected_cog_name} failed to load.",
                accent_color=Color.negative,
            )
            await interaction.response.edit_message(view=fail)
            return

        def get_full_command_name(cmd):
            return (
                f"{cmd.full_parent_name} {cmd.name}"
                if cmd.full_parent_name
                else cmd.name
            )

        cog_commands = list(cog.walk_commands())
        command_lookup = {get_full_command_name(cmd): cmd for cmd in cog_commands}
        cog_command_names = set(command_lookup.keys())

        if not cog_command_names:
            fail = Message(
                f"## its quiet here...\nmodule {selected_cog_name} has no commands.",
                accent_color=Color.negative,
            )
            await interaction.response.edit_message(view=fail)
            return

        all_custom_commands = parse_commands(self.bot.full_commands)
        matching_commands = [
            cmd for cmd in all_custom_commands if cmd["full_name"] in cog_command_names
        ]

        if not matching_commands:
            fail = Message(
                f"## no commands found\nmodule {selected_cog_name} has no commands",
                accent_color=Color.negative,
            )
            await interaction.response.edit_message(view=fail)
            return

        header = f"## codygen: {cog.qualified_name}\n{cog.description}\n"
        content = ""
        for custom_cmd in matching_commands:
            cmd_name = custom_cmd["full_name"]
            dpy_cmd = command_lookup.get(cmd_name)

            description = (
                dpy_cmd.description
                if (dpy_cmd and dpy_cmd.description)
                else custom_cmd.get("description", "-")
            )

            content += f"> </{custom_cmd['full_name']}:{custom_cmd['id']}>\n> `{description}`\n\n"

        await interaction.response.edit_message(
            view=HelpListLayout(header, content, self.bot)
        )


class HelpSelectActionRow(ActionRow):
    def __init__(self, bot):
        super().__init__()
        self.add_item(HelpSelect(bot))


class HelpActionRow(ActionRow):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Documentation",
                style=discord.ButtonStyle.link,
                url="https://github.com/tjf1dev/codygen/wiki",
            )
        )
        self.add_item(
            discord.ui.Button(
                label="Dashboard",
                style=discord.ButtonStyle.url,
                url="https://codygen.tjf1.dev/dash",
                disabled=True,
            )
        )


class HelpSection(Section):
    def __init__(self, bot: commands.Bot):
        super().__init__(accessory=discord.ui.Thumbnail(media=bot.user.avatar.url))
        self.add_item(
            TextDisplay(
                f"# codygen\na multipurpose bot by tjf1\n[`code`](<https://github.com/tjf1dev/codygen>) • [`add codygen`](<https://discord.com/oauth2/authorize?client_id={bot.user.id})"
            )
        )


class HelpListLayout(LayoutView):
    def __init__(self, header: str, content: str, bot: commands.Bot):
        super().__init__(timeout=None)
        container = Container(accent_color=Color.accent)
        self.add_item(container)
        container.add_item(TextDisplay(header))
        container.add_item(Separator())
        container.add_item(TextDisplay(content))
        container.add_item(HelpSelectActionRow(bot))
        container.add_item(HelpActionRow())


class HelpHomeView(LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        container = Container(accent_color=Color.accent)
        self.add_item(container)
        container.add_item(HelpSection(bot))
        container.add_item(Separator())
        container.add_item(HelpSelectActionRow(bot))
        container.add_item(HelpActionRow())


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


class LevelBoosts(LayoutView):
    def __init__(self, boosts: dict):
        super().__init__()
        empty_temp = {"percentage": 0, "expires": 0}
        container = Container()
        self.add_item(container)
        _global = boosts["global"]
        _role = boosts["role"]
        _user = boosts["user"]
        multiplier = boosts["multiplier"]
        if not multiplier:
            container.add_item(TextDisplay("> you don't have any boosts."))
            return
        inactive = 0
        container.add_item(TextDisplay("## active boosts"))
        container.add_item(Separator())
        content = ""

        if (
            _global is empty_temp
            or _global["percentage"] == 0
            or _global["expires"] < time.time()
            and _global["expires"] != -1
        ):
            inactive += 1
        else:
            container.add_item(
                TextDisplay(
                    f"> global: **{_global["percentage"]}%**\n> expires: **{timestamp(_global["expires"])}**"
                )
            )
        if (
            _user is empty_temp
            or _user["percentage"] == 0
            or _user["expires"] < time.time()
            and _user["expires"] != -1
        ):
            inactive += 1
        else:
            container.add_item(
                TextDisplay(
                    f"> user: **{_user["percentage"]}%**\n> expires: **{timestamp(_user["expires"])}**"
                )
            )
        if not _role:
            inactive += 1
        else:
            r_inactive = 0
            # > role: **{_global["percentage"]}%**\n> expires: **{timestamp(_global["expires"])}**
            for role_id in _role.keys():
                role = _role[role_id]
                if (
                    role["percentage"] == 0
                    or role["expires"] < time.time()
                    and role["expires"] != -1
                ):
                    r_inactive += 1
                    continue
                content += f"> role: <@&{role_id}>: **{role["percentage"]}%**\n> expires: **{timestamp(role["expires"])}**\n"
            if r_inactive == 0:
                inactive += 1
        if inactive == 4:
            container.add_item(TextDisplay("no boosts active."))
        else:
            if content:
                container.add_item(TextDisplay(f"{content}"))
            container.add_item(Separator())
            container.add_item(TextDisplay(f"### total: {multiplier}%"))
        # container.add_item(TextDisplay(f"```json\n_{boosts}```"))


class LevelRefreshSummary(LayoutView):
    def __init__(self, added_roles: dict, removed_roles: dict):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay("# levels refreshed."))
        container.add_item(Separator())
        added_text = ""
        for user in added_roles.keys():
            for role in added_roles[user]:
                added_text += f"<@{user}>: + <@&{role}>\n"
        removed_text = ""
        for user in removed_roles.keys():
            for role in removed_roles[user]:
                removed_text += f"<@{user}>: - <@&{role}>\n"
        if not added_roles:
            added_text = "no changes have been made."
        if not removed_roles:
            removed_roles = "no changes have been made."
        container.add_item(TextDisplay("## added roles\n" + added_text))
        container.add_item(Separator())
        container.add_item(TextDisplay("## removed roles\n" + removed_text))


class UserInfoSection(Section):
    def __init__(self, user: discord.Member | discord.User):
        super().__init__(accessory=discord.ui.Thumbnail(media=user.avatar.url))
        if user.display_avatar:
            avatar = f"[`avatar`]({user.display_avatar.url})"
        else:
            avatar = ""
        if user.banner:
            banner = f"[`banner`](<{user.banner.url}>)"
        else:
            banner = ""
        self.add_item(
            TextDisplay(
                f"[`profile`](<https://discord.com/users/{user.id}>) • {avatar}{" • " if user.banner else ""}{banner}\n"
                f"{f"server display name: `{user.display_name}`\n" if user.global_name != user.display_name else ""}"
                f"display name: `{user.global_name}`\n"
                f"username: `{user.name}`\n"
                f"id: `{user.id}`\n"
                f"{f"roles: `{len(user.roles)}`\n" if isinstance(user, discord.Member) else ""}"
                f"{f"joined: <t:{round(user.joined_at.timestamp())}:R> (<t:{round(user.joined_at.timestamp())}:D>)\n" if isinstance(user, discord.Member) else ""}"
                f"created: <t:{round(user.created_at.timestamp())}:R> (<t:{round(user.created_at.timestamp())}:D>)\n"
            )
        )


class UserInfo(LayoutView):
    def __init__(self, user: discord.Member | discord.User):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay(f"# {user.mention}"))
        container.add_item(Separator())
        container.add_item(UserInfoSection(user))


class ServerInfoSection(Section):
    def __init__(self, guild: discord.Guild, roles: int):
        super().__init__(accessory=discord.ui.Thumbnail(media=guild.icon.url))
        self.add_item(
            TextDisplay(
                f"## server\n"
                f"id: `{guild.id}`\n"
                f"owner: {guild.owner.mention}\n"
                f"roles: `{len(roles)}`\n"
                f"[`icon url`](<{guild.icon.url}>)\n"
                f"created: <t:{round(guild.created_at.timestamp())}:R> (<t:{round(guild.created_at.timestamp())}:D>)\n"
            )
        )


class ServerInfo(LayoutView):
    def __init__(
        self,
        guild: discord.Guild,
        roles: int,
        channels: int,
        text_channels: int,
        voice_channels: int,
        other_channels: int,
        members: int,
        bots: int,
        users: int,
    ):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay(f"# {guild.name}"))
        container.add_item(Separator())
        container.add_item(ServerInfoSection(guild, roles))
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "## channels\n"
                f"total: `{len(channels)}`\n"
                f"text: `{len(text_channels)}`\n"
                f"voice: `{len(voice_channels)}`\n"
                f"other: `{len(other_channels)}`\n\n"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "## members\n"
                f"total: `{len(members)}`\n"
                f"bots: `{len(bots)}`\n"
                f"users: `{len(users)}`",
            )
        )
        # e = discord.Embed(
        #     description=f"# {guild.name}\n"
        #     f"id: {guild.id}\n"
        #     f"owner: {guild.owner.mention}\n"
        #     f"roles: {len(roles)}\n"
        #     f"created: <t:{round(guild.created_at.timestamp())}:R> (<t:{round(guild.created_at.timestamp())}:D>)\n"
        #     f"[icon url](<{guild.icon.url}>)\n"
        #     f"## channels\n"
        #     f"total: {len(channels)}\n"
        #     f"text: {len(text_channels)}\n"
        #     f"voice: {len(voice_channels)}\n"
        #     f"other: {len(other_channels)}\n\n"
        #     f"## members\n"
        #     f"total: {len(members)}\n"
        #     f"bots: {len(bots)}\n"
        #     f"users: {len(users)}",
        #     color=discord.Color.from_rgb(
        #         *await avg_color(guild.icon.url) if guild.icon else (0, 0, 0)
        #     ),
        # )
