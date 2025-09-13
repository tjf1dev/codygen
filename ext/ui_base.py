from typing import Any
from discord.ui import LayoutView, Container, TextDisplay

# from discord import Colour


class Message(LayoutView):
    def __init__(self, message: str, **container_settings: Any):
        super().__init__()
        container = Container(**container_settings)
        self.add_item(container)
        container.add_item(TextDisplay(message))
