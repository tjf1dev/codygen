import discord
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section, ActionRow
from ext.colors import Color
from ext.utils import parse_commands
from ext.ui_base import Message
from models import Codygen
from ext.errors import CodygenError


class HelpSelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot: Codygen = bot
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
            await interaction.response.edit_message(view=HelpLayout(self.bot))
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
    def __init__(self, bot: Codygen):
        if not bot.user:
            raise CodygenError("bot/bot user not found")
        super().__init__(
            accessory=discord.ui.Thumbnail(media=bot.user.display_avatar.url)
        )
        self.add_item(
            TextDisplay(
                f"# codygen\na multipurpose bot by tjf1\n[`code`](<https://github.com/tjf1dev/codygen>) • [`add codygen`](<https://discord.com/oauth2/authorize?client_id={bot.user.id})"
            )
        )


class HelpListLayout(LayoutView):
    def __init__(self, header: str, content: str, bot: Codygen):
        super().__init__(timeout=None)
        container = Container(accent_color=Color.accent)
        self.add_item(container)
        container.add_item(TextDisplay(header))
        container.add_item(Separator())
        container.add_item(TextDisplay(content))
        container.add_item(HelpSelectActionRow(bot))
        container.add_item(HelpActionRow())


class HelpLayout(LayoutView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        container = Container(accent_color=Color.accent)
        self.add_item(container)
        container.add_item(HelpSection(bot))
        container.add_item(Separator())
        container.add_item(HelpSelectActionRow(bot))
        container.add_item(HelpActionRow())
