from main import get_global_config
import discord
import requests
import aiosqlite
import hashlib
import random
from typing import cast
from views import GuessLayout
from discord.ext import commands
from ext.colors import Color
from ext.logger import logger
from discord import app_commands
from models import Cog


class fun(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "fun commands!"
        self.allowed_contexts = discord.app_commands.allowed_contexts(True, True, True)
        self.hidden = False

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.hybrid_group(
        name="fun",
        description="fun commands!",
        invoke_without_command=True,  # type: ignore
    )
    async def fun_group(self, ctx: commands.Context):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @fun_group.command(name="ship", description="ship two people")  # type: ignore
    @app_commands.describe(
        user1="users to ship", user2="users to ship (defaults to you)"
    )
    async def ship(
        self,
        ctx: commands.Context,
        user1: discord.User,
        user2: discord.User | discord.Member | None = None,
    ):
        if user2 is None:
            user2 = ctx.author

        # name1 = user1.name
        # name2 = user2.name
        def generate_number_from_strings(str1, str2):
            combined = str1 + str2
            hash_object = hashlib.sha256(combined.encode())
            hex_digest = hash_object.hexdigest()
            int_value = int(hex_digest, 16)
            number = (int_value % 100) + 1  # Maps to 1-100
            return number

        ship = str(generate_number_from_strings(user1.name, user2.name))
        exceptions = {
            (1201995223996321886, 1191871707577864203): 100,
            (978596696156147754, 1201995223996321886): 100,
            (1379503145658486994, 1337509693874245682): 100,
        }
        if user1 == user2:
            ship = 100
        value = (
            exceptions.get((user1.id, user2.id))
            or exceptions.get((user2.id, user1.id))
            or ship
        )
        embed = discord.Embed(
            title="ship",
            description=f"ship between {user1.mention} and {user2.mention} is {value}%",
            color=Color.accent_og,
        )
        await ctx.reply(embed=embed)

    # @verify()
    # @fun_group.command(name="awawawa", description="awawawawawawa")
    # async def awawawa(self, ctx: commands.Context):
    #     await ctx.reply(random.choice(words), ephemeral=True)

    # @verify()
    # @fun_group.command(
    #     name="randomword",
    #     description="get random word from the english dictionary and it's definition",
    # )
    # async def randomword(self, ctx: commands.Context):
    #     if ctx.interaction:
    #         await ctx.interaction.response.defer()
    #     with open("assets/randomword.txt", "r") as file:
    #         text = file.read()
    #         words = list(map(str, text.split()))
    #         word_found = False
    #         iteration = 0
    #         while not word_found:
    #             iteration += 1
    #             if iteration >= 5:
    #                 word_found = True
    #             word = random.choice(words)
    #             entry: list | dict = await request_with_json(
    #                 f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    #             )
    #             if isinstance(entry, dict):
    #                 if (
    #                     entry.get("title", None).strip().lower()
    #                     == "no definitions found"
    #                 ):
    #                     entry = None
    #             if entry:
    #                 word_found = True
    #                 meanings = entry[0].get("meanings", [{}])
    #                 first_meaning = meanings[0]
    #                 partOfSpeech = first_meaning.get("partOfSpeech", "unknown")
    #                 definitions = first_meaning.get("definitions", [{}])
    #                 first_definition = definitions[0].get("definition", "")
    #                 e = discord.Embed(
    #                     description=f"# {word}\n"
    #                     f"-# as {partOfSpeech}: \n"
    #                     f"**`{first_definition}`**\n-# for more definitions of this word, check </fun word:1367182065564520484>"
    #                 )
    #             if not entry:
    #                 e = discord.Embed(
    #                     description=f"# {word}\ncouldn't even find a definition for this one."
    #                 )
    #     await ctx.reply(embed=e)

    # @fun_group.command(name="word", description="get definition of an english word")
    # @app_commands.describe(word="the word to get a definition of")
    # async def word(self, ctx: commands.Context, *, word: str):
    #     entry: list | dict = await request_with_json(
    #         f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    #     )
    #     found = False
    #     embeds = []
    #     if isinstance(entry, dict):
    #         if entry.get("title", None).strip().lower() == "no definitions found":
    #             entry = None
    #     if entry:
    #         found = True
    #         meanings = entry[0].get("meanings", [{}])
    #         e1 = discord.Embed(
    #             description=f"# {word}\nfound {len(meanings)} meanings for this word."
    #         )
    #         if meanings == [{}]:
    #             found = False
    #         embeds.append(e1)
    #         for m in meanings:
    #             partOfSpeech = m.get("partOfSpeech", "unknown")
    #             definitions = m.get("definitions", [{}])
    #             desc = f"-# as {partOfSpeech}\n"
    #             for d in definitions:
    #                 definition = d.get("definition")
    #                 desc += f"**`{definition}`**\n\n"
    #             e = discord.Embed(description=desc)
    #             embeds.append(e)
    #     if not entry:
    #         e = discord.Embed(description="couldn't find a definition for this word.")
    #         embeds.append(e)
    #     await ctx.reply(embeds=embeds, ephemeral=False if found else True)

    @fun_group.command(name="wokemeter", description="see how WOKE someone is!")  # type: ignore
    @app_commands.describe(user="the user to check")
    async def wokemeter(
        self, ctx: commands.Context, user: discord.User | discord.Member | None = None
    ):
        if ctx.guild:
            con: aiosqlite.Connection = self.bot.db
            cur: aiosqlite.Cursor = await con.cursor()
            res = await cur.execute(
                "SELECT wokemeter_min, wokemeter_max FROM guild_commands WHERE guild_id=?",
                (ctx.guild.id,),
            )
            row = cast(tuple, await res.fetchone())
            if row:
                woke_min, woke_max = row[0], row[1]
            else:
                woke_min, woke_max = 0, 100

        else:
            woke_min, woke_max = 0, 100
        if user is None:
            user = ctx.author
        if user.bot:
            await ctx.reply("bots cant be woke :broken_heart:")
            return
        else:
            await ctx.reply(
                f"{user.mention} is **{random.randint(int(woke_min), int(woke_max))}%** woke"
            )
            return

    # @verify()
    # @fun_group.command(name="wokegame", description="Check is the game woke!")
    # async def wokegame(self, ctx: commands.Context, game: str):
    #     with open("assets/wokegames.csv", mode="r", encoding="utf-8") as wokelist:
    #         csvFile = csv.DictReader(wokelist)
    #         color = 0x0000
    #         game_lower = game.lower()
    #         for lines in csvFile:
    #             if game_lower in lines["name"].lower():
    #                 appID = lines["appid"]
    #                 name = lines["name"]
    #                 banner = lines["banner"]
    #                 wokeness = str(lines["woke"])
    #                 description = lines["description"]
    #                 if wokeness == "-1":
    #                     rate = "Very woke!"
    #                     color = Color.positive
    #                 elif wokeness == "0":
    #                     rate = "Slightly woke!"
    #                     color = Color.lyellow
    #                 elif wokeness == "1":
    #                     rate = "Not woke!"
    #                     color = Color.negative
    #                 else:
    #                     rate = "How the fuck did that happen"
    #                 embed = discord.Embed(
    #                     title=rate, description=description, color=color
    #                 )
    #                 embed.set_footer(text=f"{name}, {appID}")
    #                 embed.set_image(url=banner)
    #                 await ctx.send(embed=embed)
    #                 return
    #         fail = discord.Embed(title="cant find the game", color=Color.negative)
    #         await ctx.send(embed=fail)

    @app_commands.allowed_contexts(guilds=True, dms=False)
    @app_commands.allowed_installs(guilds=True, users=False)
    @fun_group.command(name="guess", description="Guess the user by pfp!")  # type: ignore
    async def guess(self, ctx: commands.Context):
        global guessUser
        global guessUserDisplay
        if not ctx.guild:
            return
        users = ctx.guild.members
        while True:
            user = random.choice(users)
            if not user.bot and user.avatar:
                break
        guessUser = user.name
        guessUserDisplay = user.display_name
        await ctx.reply(view=GuessLayout(user=user))

    # @verify()
    # @fun_group.command(name="guessrank", description="Check how many times have you guessed!")
    # async def guessrank(self,ctx: commands.Context):
    #     invoker = ctx.author
    #     invokerName = ctx.author.name
    #     randomColor = random.randrange(0, 2**24)
    #     randomHex = hex(randomColor)
    #     randomHexINT = int(randomHex,16)
    #     with open(f"data/guilds/{ctx.guild.id}.json", "r") as f:
    #         data = json.load(f)
    #         value = data["stats"]["guess"]["users"].get(invokerName, 0)
    #     if value == 1:
    #         raz = "time"
    #     else:
    #         raz = "times"
    #     embed = discord.Embed(color=randomHexINT)
    #     embed.add_field(name="User %s guessed %s %s!" % (invokerName, str(value), raz), value=" ", inline=True)
    #     embed.set_thumbnail(url=ctx.author.avatar.url)
    #     await ctx.send(embed=embed)
    # @verify()
    # @fun_group.command(name="guesstop", description="Guess the user by pfp!")
    # async def guesstop(self,ctx: commands.Context):
    #     with open(f"data/guilds/{ctx.guild.id}.json", "r") as f:
    #         data = json.load(f)
    #     topValues = data["stats"]["guess"]["users"]
    #     invoker = ctx.author
    #     invokerName = ctx.author.name
    #     with open(f"data/guilds/{ctx.guild.id}.json", "r") as f:
    #         data = json.load(f)
    #         value = data["stats"]["guess"]["users"].get(invokerName, 0)
    #     top = {k: v for k, v in sorted(topValues.items(), key=lambda item: item[1], reverse=True)}
    #     randomColor = random.randrange(0, 2**24)
    #     randomHex = hex(randomColor)
    #     randomHexINT = int(randomHex,16)
    #     embed = discord.Embed(color=randomHexINT)
    #     for x, (user, value) in enumerate(top.items(), start=1):
    #         if value == 1:
    #             raz = "time"
    #         else:
    #             raz = "times"
    #         embed.add_field(name=f"{x}. {user}", value=f"Guessed {value} {raz}.")
    #     await ctx.send(embed=embed)

    @fun_group.command(name="cat", description="get a random pic of a cat :3")  # type: ignore
    async def cat(self, ctx: commands.Context):
        url = get_global_config()["commands"]["cat"]["url"]
        req = requests.get(url)
        e = discord.Embed(title=":3", color=Color.white)
        e.set_image(url=req.json()[0]["url"])
        await ctx.reply(embed=e)


async def setup(bot):
    await bot.add_cog(fun(bot))
