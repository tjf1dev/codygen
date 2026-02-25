import logger
import json
from discord.ext import commands
from models import Module
import discord
from ext import errors
from enum import Enum


class ComponentType(Enum):
    TEXT = 0
    STRING_SELECT = 1


def layout_from_components(data: list) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView()
    container = discord.ui.Container()
    view.add_item(container)
    for component in data:
        type_value = component.get("type")
        if type_value is None:
            raise errors.FormDecodeError("no type provided")

        try:
            type = ComponentType(type_value)
        except ValueError:
            raise errors.FormDecodeError("invalid type")

        if type == ComponentType.TEXT:
            container.add_item(discord.ui.TextDisplay(component.get("content")))
        if type == ComponentType.STRING_SELECT:
            header = component.get("header")
            header_description = component.get("header_description")
            placeholder = component.get("placeholder")
            min_values = component.get("min_values")
            max_values = component.get("max_values")

            select_options = []
            options = component.get("options")
            for option in options:
                label_item = option.get("label")
                value = option.get("value")
                description = option.get("description")
                default = option.get("default", False)
                el = discord.SelectOption(
                    label=label_item,
                    value=value,
                    description=description,
                    default=default,
                )
                select_options.append(el)
            select = discord.ui.Select(
                placeholder=placeholder,
                min_values=min_values,
                max_values=max_values,
                options=options,
            )
            label = discord.ui.Label(
                text=header, description=header_description, component=select
            )
            container.add_item(label)

    return view


class forms(Module):
    def __init__(self, bot):
        self.bot = bot
        self.description = "flexible customizable forms system"
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    # TODO
    # build simple modal from JSON
    # channel to accept / deny forms
    # role requirements
    # role on resolved

    @commands.hybrid_group(name="forms", description="")
    async def forms(self, ctx: commands.Context):
        pass

    @forms.command()
    async def from_json(self, ctx: commands.Context, *, text: str):
        data = json.loads(text)
        view = layout_from_components(data.get("components", []))
        await ctx.reply(view=view)


async def setup(bot):
    if bot.release:
        return
    logger.debug("adding forms module - running a non release target")
    await bot.add_cog(forms(bot))
