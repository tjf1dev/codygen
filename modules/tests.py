from discord.ext import commands
from discord import Interaction
from main import version
import random
import aiosqlite
from db import get_database_latency

# from discord import app_commands
import discord


# from main import logger, Color, verify
class tests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = ""
        self.db: aiosqlite.Connection = bot.db

    class TestButton(discord.ui.Button):
        async def callback(self, interaction: Interaction):
            await interaction.response.send_message("test 1", ephemeral=True)

    class TestUserSelect(discord.ui.UserSelect):
        def __init__(self):
            super().__init__(placeholder="select a user to pick", max_values=1)

        async def callback(self, interaction: Interaction):
            await interaction.response.send_message(
                f"you selected {self.values[0]}!", ephemeral=True
            )

    class TestSelectActionRow(discord.ui.ActionRow):
        def __init__(self):
            super().__init__()
            self.add_item(tests.TestUserSelect())

    class TestActionRow(discord.ui.ActionRow):
        def __init__(self):
            super().__init__()
            self.add_item(tests.TestButton(label="test1"))

    class TestSection(discord.ui.Section):
        def __init__(self):

            accessory = discord.ui.Thumbnail(
                media="https://cdn.discordapp.com/avatars/1367173681155018916/a_2988d84484f9bd956ba2a89b34bda2cc.gif?size=1024"
            )
            super().__init__(accessory=accessory)
            self.add_item(
                discord.ui.TextDisplay(
                    f"## codygen {version} by tjf1\nthis message is a test of components v2 which will possibly be present in future beta versions of codygen"
                )
            )

    class TestLayout(discord.ui.LayoutView):
        def __init__(self):
            super().__init__()
            container = discord.ui.Container(accent_color=None)
            self.add_item(container)

            # test3 works
            container.add_item(tests.TestSection())
            container.add_item(
                discord.ui.TextDisplay(
                    "above this is a section so i can add an image alongside a message"
                )
            )
            container.add_item(discord.ui.Separator())
            container.add_item(
                discord.ui.TextDisplay(
                    "even more text here\nidk if theres a character limit here\nthere should be an action row above this message and below it should be the input"
                )
            )
            container.add_item(discord.ui.Separator())
            container.add_item(
                discord.ui.TextDisplay("nevermind i moved both of the action rows down")
            )
            container.add_item(tests.TestSelectActionRow())
            container.add_item(tests.TestActionRow())

    @commands.command(name="v2", description="preview of components v2")
    async def v2(self, ctx: commands.Context):
        await ctx.reply(view=self.TestLayout())

    @commands.command(name="levelup", description="test of the level up message")
    async def levelup(self, ctx: commands.Context):
        from ext.views import LevelupLayout

        old_xp = random.randint(0, 1000)
        xp = random.randint(old_xp, 1000)
        place_in_leaderboard = random.randint(0, 100)
        await ctx.reply(
            view=LevelupLayout(ctx.author, old_xp, xp, place_in_leaderboard)
        )
        await ctx.send(
            f"-# old_xp = {old_xp}, xp = {xp}, place in leaderboard = {place_in_leaderboard}"
        )

    @commands.is_owner()
    @commands.command(name="db", description="get database connection")
    async def db(self, ctx: commands.Context, *, sql: str = ""):
        cur = await self.db.cursor()
        tables = await cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t[0] for t in await tables.fetchall()]
        content = f"`{await get_database_latency(self.bot.db):.3f}ms, {len(table_names)} tables loaded`"
        msg = await ctx.reply(content)
        if sql != "":
            res = await cur.execute(sql)
            await msg.edit(content=f"{content}\n```\n{await res.fetchall()}```")


async def setup(bot):
    await bot.add_cog(tests(bot))
