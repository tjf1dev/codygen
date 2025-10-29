from ext.utils import parse_flags
from discord.ext import commands
from ext.logger import logger


class testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = ""
        self.hidden = True

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.hybrid_group(name="test", description="")
    async def test(self, ctx: commands.Context):
        pass

    @test.command("flag")
    async def flag(self, ctx: commands.Context, *, flags: str):
        res = parse_flags(flags)
        await ctx.reply(str(res))


async def setup(bot):
    if bot.release:
        logger.debug("skipping testing cog - running on release target")
        return
    await bot.add_cog(testing(bot))
