import discord
from discord.ext import commands
from discord.ui import Button, ActionRow, LayoutView, Container
from ext.ui_base import Message
from typing import Sequence, Union
import logger

PageType = Union[Message, discord.ui.Item]


class Paginator:
    def __init__(self, pages: Sequence[PageType], user_id: int):
        self.pages = pages
        self.user_id = user_id
        self.current_page = 0

    @classmethod
    def from_ctx(cls, pages: Sequence[PageType], ctx: commands.Context):
        return cls(pages, ctx.author.id)

    @classmethod
    def from_id(cls, pages: Sequence[PageType], user_id: int):
        return cls(pages, user_id)

    def to_container(self, page: int = 0, buttons: bool = False) -> Container:
        """return a Container with the content for one page. optionally put the buttons in the container"""
        item = self.pages[page]
        logger.debug(type(item))
        if isinstance(item, Message):
            inner = item.children[0].children[0]  # type: ignore
        else:
            inner = item
        logger.debug(type(inner))
        container = Container(inner)
        if buttons:
            container.add_item(PaginatorButtons(self.user_id, self.pages, page))
        return container

    def content(self, page: int = 0):
        """return the Item of the provided page."""
        item = self.pages[page]

        if isinstance(item, Message):
            c = item.children[0]
        else:
            c = item
        return c

    def buttons(self, page: int = 0):
        return PaginatorButtons(self.user_id, self.pages, page)

    def to_layout(self, page: int = 0) -> LayoutView:
        """return a full layout including page container + paginator buttons."""
        layout = LayoutView()
        container = self.to_container(page, buttons=False)
        logger.debug(container)
        logger.debug(container.children[0])
        layout.add_item(container)
        layout.add_item(PaginatorButtons(self.user_id, self.pages, page))
        return layout


class PageButton(Button):
    def __init__(self, user_id: int, pages: Sequence[PageType], page: int):
        super().__init__(label=f"{page + 1}/{len(pages)}", disabled=True)


class ChangePageButton(Button):
    def __init__(
        self, user_id: int, pages: Sequence[PageType], page: int, forward: bool
    ):
        self.user_id = user_id
        self.pages = pages
        self.page = page
        self.forward = forward
        super().__init__(
            label=">" if forward else "<",
            disabled=(page == len(pages) - 1 if forward else page == 0),
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return

        self.page = self.page + 1 if self.forward else self.page - 1
        view = Paginator.from_id(self.pages, self.user_id).to_layout(self.page)
        logger.debug(type(view))
        await interaction.response.defer()
        await interaction.edit_original_response(view=view)


class PaginatorButtons(ActionRow):
    def __init__(self, user_id: int, pages: Sequence[PageType], page: int):
        super().__init__()
        self.add_item(ChangePageButton(user_id, pages, page, False))
        self.add_item(PageButton(user_id, pages, page))
        self.add_item(ChangePageButton(user_id, pages, page, True))

    def to_actionrow(self) -> ActionRow:
        return self
