from discord.ext import commands


class Cog(commands.Cog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    hidden: bool
