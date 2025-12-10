import aiosqlite
import discord
import json
from typing import Any
from discord.ui import (
    LayoutView,
    TextDisplay,
    Container,
    Separator,
    Select,
    ActionRow,
    Button,
)
from models import Codygen
from ext.colors import Color


class ModulesConfirmButton(Button):
    def __init__(
        self,
        bot: Codygen,
        selected_modules: list,
        module_settings: dict,
        change_text: str,
        user_id: int,
    ):
        self.bot = bot
        self.user_id = user_id
        self.selected_modules = selected_modules
        self.module_settings = module_settings
        self.change_text = change_text
        super().__init__(label="Apply", style=discord.ButtonStyle.primary)

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        con: aiosqlite.Connection = self.bot.db
        for module, state in self.module_settings.items():
            new_state = module in self.selected_modules
            if state != new_state:
                self.module_settings[module] = new_state
        settings_str = json.dumps(self.module_settings, indent=4)
        await con.execute(
            "UPDATE guilds SET module_settings=? WHERE guild_id=?",
            (settings_str, interaction.guild_id),
        )
        await con.commit()
        await interaction.edit_original_response(view=ModulesSuccess(self.change_text))


class ModulesSuccess(LayoutView):
    def __init__(self, change_text: str) -> None:
        super().__init__()
        cont = Container(accent_color=Color.positive)
        cont.add_item(
            TextDisplay(f"## changes applied successfully.\n```{change_text}```")
        )
        self.add_item(cont)


class ModulesConfirmBackButton(Button):
    def __init__(self, bot, module_settings, user_id: int):
        self.user_id = user_id
        self.bot = bot
        self.module_settings = module_settings
        super().__init__(label="Back")

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        await interaction.edit_original_response(
            view=SettingsModulesLayout(self.bot, self.module_settings, self.user_id)
        )


class ModulesConfirm(LayoutView):
    def __init__(
        self, bot: Codygen, selected_modules: list, module_settings: dict, user_id: int
    ) -> None:
        super().__init__()
        cont = Container()
        row = ActionRow()
        change_text = ""
        for module, state in module_settings.items():
            new_state = module in selected_modules
            if state != new_state:
                change_text += "+ " if new_state else "- "
                change_text += f"{module}\n"
        row.add_item(
            ModulesConfirmButton(
                bot, selected_modules, module_settings, change_text, user_id
            )
        )
        row.add_item(ModulesConfirmBackButton(bot, module_settings, user_id))

        cont.add_item(
            TextDisplay(
                f"## are you sure?\nthis will change the following modules:\n```{change_text}```\nafter applying, the changes will take effect immediatly, making affected modules (in)accessible"
            )
        )
        cont.add_item(row)
        self.add_item(cont)


class ModuleSelect(Select):
    def __init__(self, bot: Codygen, module_settings: dict, user_id: int):
        self.bot = bot
        self.module_settings = module_settings
        self.user_id = user_id

        super().__init__(min_values=0, max_values=len(module_settings))
        for name, state in module_settings.items():
            self.add_option(label=name, default=state)

    async def callback(self, interaction) -> Any:
        if interaction.user.id != self.user_id:
            return
        await interaction.response.defer()
        await interaction.edit_original_response(
            view=ModulesConfirm(
                self.bot, self.values, self.module_settings, self.user_id
            )
        )


class SettingsModulesLayout(LayoutView):
    def __init__(self, bot: Codygen, module_settings: dict, user_id: int):
        super().__init__()
        cont = Container()
        row = ActionRow()
        row.add_item(ModuleSelect(bot, module_settings, user_id))

        cont.add_item(TextDisplay("## module setup"))
        cont.add_item(Separator())
        cont.add_item(
            TextDisplay("select modules that will be allowed in this server.")
        )
        cont.add_item(row)
        self.add_item(cont)
