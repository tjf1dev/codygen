from ext.utils import parse_flags
from discord.ext import commands
from ext.logger import logger
from ext.ui_base import Message
from ext.utils import setup_guild
from ext.pagination import Paginator
from discord.ui import TextDisplay
from ext.emotes import get_emotes_async, get_emotes_from_assets


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

    @test.command("guildsetup")
    async def guildsetup(self, ctx: commands.Context):
        guild = ctx.guild
        if not guild:
            return
        try:
            gen = setup_guild(self.bot, guild, gtype=1)
            is_first_message = True
            async for view in gen:
                await ctx.reply(view=view) if is_first_message else await ctx.send(
                    view=view
                )
                is_first_message = False
        except Exception as e:
            logger.error(f"An error occurred while trying to setup {guild.name}: {e}")

    @test.command("paginator")
    async def paginator(self, ctx: commands.Context):
        p1 = Message("page 1")
        p2 = Message("page 2")
        p3 = Message("# page 3")
        p4 = TextDisplay("page 4")
        await ctx.reply(view=Paginator([p1, p2, p3, p4], ctx))

    @test.command("emote")
    async def emote(self, ctx: commands.Context, emote: str | None = None):
        if emote:
            await ctx.message.add_reaction(ctx.bot.emote(emote).PartialEmoji())
            return
        emotes = await get_emotes_async()
        required_emotes = get_emotes_from_assets()
        content = (
            f"## this bot has {len(emotes)} emote{'s' if len(emotes) != 1 else ''}:\n"
        )
        for em in emotes:
            content += f"{'-# ' if em.name not in required_emotes else ''}{em.name} (`{em.id}`) - {em}\n"
        await ctx.reply(view=Message(content))


async def setup(bot):
    if bot.release:
        logger.debug("skipping testing cog - running on release target")
        return
    await bot.add_cog(testing(bot))
