import discord
from discord.ext import commands
from discord.ui import Button, ActionRow, LayoutView
from ext.ui_base import Message


def createLayoutFromMessageOrContainer(page: int, user_id: int, pages):
    item = pages[page]
    if isinstance(item, Message):
        item = item.children[0]  # container of the message LayoutView
    view = LayoutView()
    view.add_item(item)

    view.add_item(PaginatorButtons(user_id, pages, page))

    return view


class PageButton(Button):
    def __init__(self, user_id: int, pages: list[discord.ui.Item], page: int):
        super().__init__(label=f"{page + 1}/{len(pages)}", disabled=True)


class ChangePageButton(Button):
    def __init__(
        self, user_id: int, pages: list[discord.ui.Item], page: int, forward: bool
    ):
        self.pages = pages
        self.user_id = user_id
        self.page = page
        self.forward = forward
        super().__init__(
            label=">" if forward else "<",
            disabled=page == len(pages) - 1 if forward else page == 0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        self.page = self.page + 1 if self.forward else self.page - 1
        await interaction.response.defer()
        await interaction.edit_original_response(
            view=createLayoutFromMessageOrContainer(self.page, self.user_id, self.pages)
        )


class PaginatorButtons(ActionRow):
    def __init__(self, user_id: int, pages: list[discord.ui.Item], page: int) -> None:
        super().__init__()

        self.add_item(ChangePageButton(user_id, pages, page, False))
        self.add_item(PageButton(user_id, pages, page))
        self.add_item(ChangePageButton(user_id, pages, page, True))


def Paginator(
    pages: list[Message | discord.ui.Item], ctx: commands.Context
) -> LayoutView:
    user_id = ctx.author.id
    return createLayoutFromMessageOrContainer(0, user_id, pages)
