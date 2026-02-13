from discord.ext import commands
import logger
from models import Module, Codygen
from typing import cast


# todo
# tickets are gonna be divided into 'ticket modules'
# each one of them has settings (category, what roles can access tickets, etc.)
# i want to have most of this stuff manageable from the dashboard since i need to do that finally
class ticket(Module):
    def __init__(self, bot, **kwargs):
        super().__init__(hidden=False, default=False, **kwargs)
        self.bot = cast(Codygen, bot)
        self.description = ""
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.hybrid_group(name="ticket", description="")
    async def ticket(self, ctx: commands.Context):
        pass


async def setup(bot):
    await bot.add_cog(ticket(bot))
