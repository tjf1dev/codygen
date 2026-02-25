from discord.ext import commands


class Module(commands.Cog):
    def __init__(self, hidden: bool, default: bool, **kwargs):
        super().__init__(**kwargs)
        self.hidden = hidden
        self.default = default
