from discord.ui import LayoutView, Container, TextDisplay

# import discord


class Message(LayoutView):
    def __init__(self, message, **container_settings: dict):
        super().__init__()
        container = Container(**container_settings)
        self.add_item(container)
        container.add_item(TextDisplay(message))
