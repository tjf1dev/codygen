from main import *
import discord, random, json, csv
import os


class fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "fun commands!"

    @commands.hybrid_group(
        name="fun", description="fun commands!", invoke_without_command=True
    )
    async def fun_group(self, ctx: commands.Context):
        pass

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @verify()
    @fun_group.command(name="ship", description="SHIP TWO PEOPLE")
    async def ship(
        self,
        ctx: commands.Context,
        user1: discord.User = None,
        user2: discord.User = None,
    ):
        if user2 is None:
            user2 = ctx.author
        name1 = user1.name
        name2 = user2.name
        ship = str(random.randint(0, 100))
        exceptions_100 = [[1201995223996321886, 1191871707577864203]]

        def is_exception(id):
            for e in exceptions_100:
                if id in e:
                    return True

        if user1 == user2:
            ship = 100
        if is_exception(user1.id) and is_exception(user2.id):
            ship = 100
        embed = discord.Embed(
            title=f"ship",
            description=f"ship between {user1.mention} and {user2.mention} is {ship}%",
            color=Color.accent_og,
        )
        await ctx.reply(embed=embed)

    @verify()
    @fun_group.command(name="awawawa", description="awawawawawawa")
    async def awawawa(self, ctx: commands.Context):
        await ctx.reply(random.choice(words), ephemeral=True)

    @verify()
    @fun_group.command(
        name="randomword", description="get random word from english dictionary"
    )
    async def randomword(self, ctx: commands.Context):
        await ctx.interaction.response.defer()
        with open("assets/randomword.txt", "r") as file:
            text = file.read()
            words = list(map(str, text.split()))
            word_found = False
            iteration = 0
            while not word_found:
                iteration += 1
                if iteration >= 5:
                    word_found = True
                word = random.choice(words)
                req: aiohttp.ClientResponse = await request(
                    f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
                )
                entry: list | dict = await req.json()
                if isinstance(entry, dict):
                    if (
                        entry.get("title", None).strip().lower()
                        == "no definitions found"
                    ):
                        entry = None
                if entry:
                    word_found = True
                    meanings = entry[0].get("meanings", [{}])
                    first_meaning = meanings[0]
                    partOfSpeech = first_meaning.get("partOfSpeech", "unknown")
                    definitions = first_meaning.get("definitions", [{}])
                    first_definition = definitions[0].get("definition", "")
                    e = discord.Embed(
                        description=f"# {word}\n"
                        f"-# as {partOfSpeech}: \n"
                        f"**`{first_definition}`**\n-# for more definitions of this word, check </fun word:1367182065564520484>"
                    )
                if not entry:
                    e = discord.Embed(
                        description=f"# {word}\ncouldn't even find a definition for this one."
                    )
        await ctx.reply(embed=e)

    @fun_group.command(name="word", description="get definition of an english word")
    async def word(self, ctx: commands.Context, *, word: str):
        logger.debug(f"getting the word: {word}")
        entry: list | dict = await request(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        )
        found = False
        embeds = []
        if isinstance(entry, dict):
            if entry.get("title", None).strip().lower() == "no definitions found":
                entry = None
        if entry:
            found = True
            meanings = entry[0].get("meanings", [{}])
            logger.debug(f"entry: {entry}")
            e1 = discord.Embed(
                description=f"# {word}\nfound {len(meanings)} meanings for this word."
            )
            if meanings == [{}]:
                found = False
            embeds.append(e1)
            for m in meanings:
                partOfSpeech = m.get("partOfSpeech", "unknown")
                definitions = m.get("definitions", [{}])
                desc = f"-# as {partOfSpeech}\n"
                for d in definitions:
                    definition = d.get("definition")
                    desc += f"**`{definition}`**\n\n"
                e = discord.Embed(description=desc)
                embeds.append(e)
        if not entry:
            e = discord.Embed(description=f"couldn't find a definition for this word.")
            embeds.append(e)
        await ctx.reply(embeds=embeds, ephemeral=False if found else True)

    @verify()
    @fun_group.command(name="cute", description="cute command")
    async def cute(self, ctx: commands.Context, user: discord.User = None):
        if user:
            await ctx.reply(f"{user.mention} is cute and silly :3")
        else:
            await ctx.reply("you are cute and silly :3", ephemeral=True)

    @verify()
    @fun_group.command(name="wokemeter", description="see how WOKE someone is!")
    async def wokemeter(self, ctx: commands.Context, user: discord.User = None):
        woke = await get_guild_config(ctx.guild.id)["commands"]["wokemeter"]
        woke_min = woke["woke_min"]
        woke_max = woke["woke_max"]
        exceptions = woke["exceptions"]
        if user is None:
            user = ctx.author
        if str(user.id) in exceptions.keys():
            await ctx.reply(f"{user.mention} is **{exceptions[str(user.id)]}%** woke")
            return
        elif user.id == 1266572586528280668:
            await ctx.reply(f"{user.mention} is **wamz** woke")
            return
        if user.bot:
            await ctx.reply(f"bots cant be woke :broken_heart:")
            return
        else:
            await ctx.reply(
                f"{user.mention} is **{random.randint(int(woke_min), int(woke_max))}%** woke"
            )
            return

    @verify()
    @fun_group.command(name="wokegame", description="Check is the game woke!")
    async def wokegame(self, ctx: commands.Context, game: str):
        with open("assets/wokegames.csv", mode="r", encoding="utf-8") as wokelist:
            csvFile = csv.DictReader(wokelist)
            color = 0x0000
            game_lower = game.lower()
            for lines in csvFile:
                if game_lower in lines["name"].lower():
                    appID = lines["appid"]
                    name = lines["name"]
                    banner = lines["banner"]
                    wokeness = str(lines["woke"])
                    description = lines["description"]
                    if wokeness == "-1":
                        rate = "Very woke!"
                        color = Color.positive
                    elif wokeness == "0":
                        rate = "Slightly woke!"
                        color = Color.lyellow
                    elif wokeness == "1":
                        rate = "Not woke!"
                        color = Color.negative
                    else:
                        rate = "How the fuck did that happen"
                    embed = discord.Embed(
                        title=rate, description=description, color=color
                    )
                    embed.set_footer(text=f"{name}, {appID}")
                    embed.set_image(url=banner)
                    await ctx.send(embed=embed)
                    return
            fail = discord.Embed(title="cant find the game", color=Color.negative)
            await ctx.send(embed=fail)

    @verify()
    @fun_group.command(name="guess", description="Guess the user by pfp!")
    async def guess(self, ctx: commands.Context):
        global guessUser
        global guessUserDisplay
        users = ctx.guild.members
        while True:
            user = random.choice(users)
            if not user.bot and user.avatar:
                break
        guessUser = user.name
        guessUserDisplay = user.display_name
        pfp = user.avatar.url
        embed = discord.Embed(
            title=" ", description="Who is that?", color=Color.positive
        )
        embed.set_author(name="Which user is that??")
        embed.set_thumbnail(url=pfp)
        await ctx.send(
            embed=embed,
            view=guessButtons(
                guess_user=guessUser,
                guess_user_display=guessUserDisplay,
                interaction=ctx,
            ),
        )

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
    @verify()
    @fun_group.command(name="cat", description="get a random pic of a cat :3")
    async def cat(self, ctx: commands.Context):
        url = get_global_config()["commands"]["cat"]["url"]
        req = requests.get(url)
        e = discord.Embed(title=":3", color=Color.white)
        e.set_image(url=req.json()[0]["url"])
        await ctx.reply(embed=e)


class guessNewGame(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="New Game", style=discord.ButtonStyle.green, custom_id="new_game"
    )
    async def new_game(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        global guessUser
        global guessUserDisplay
        users = interaction.guild.members
        while True:
            user = random.choice(users)
            if not user.bot and user.avatar:
                break
        guessUser = user.name
        guessUserDisplay = user.display_name
        pfp = user.avatar.url
        embed = discord.Embed(
            title=" ", description="Who is that?", color=Color.positive
        )
        embed.set_author(name="Which user is that??")
        embed.set_thumbnail(url=pfp)
        await interaction.response.send_message(
            embed=embed,
            view=guessButtons(
                guess_user=guessUser,
                guess_user_display=guessUserDisplay,
                interaction=interaction,
            ),
        )


class Questionnaire(discord.ui.Modal, title="Guess the user!"):
    name = discord.ui.TextInput(label="Which user is that??")

    def __init__(self, guess_user, guess_user_display, view, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guess_user = guess_user
        self.guess_user_display = guess_user_display
        self.view = view  # store the guessButtons view instance

    async def on_submit(self, interaction: discord.Interaction):
        # Get the user's guess from the text input's value
        guessOG = self.name.value
        guessLowercase = guessOG.lower()
        guessUserDisplayLowercase = str(self.guess_user_display).lower()
        if (
            guessLowercase == self.guess_user.lower()
            or guessLowercase == guessUserDisplayLowercase
        ):
            embed = discord.Embed(color=Color.positive)
            embed.add_field(name="Correct!", value=" ", inline=True)
            embed.set_author(
                name=interaction.user.name + f" tried: {guessOG}",
                icon_url=interaction.user.avatar.url,
            )
            # Stop the guessButtons view (cancelling its timeout)
            self.view.stop()
            # Send a new game message
            await interaction.response.send_message(embed=embed, view=guessNewGame())
        else:
            embed = discord.Embed(color=Color.negative)
            embed.add_field(name="Wrong!", value=" ", inline=True)
            embed.set_author(
                name=interaction.user.name + f" tried: {guessOG}",
                icon_url=interaction.user.avatar.url,
            )
            await interaction.response.send_message(embed=embed)


class guessButtons(discord.ui.View):
    def __init__(self, guess_user, guess_user_display, interaction, *, timeout=15):
        super().__init__(timeout=timeout)
        self.guess_user = guess_user
        self.guess_user_display = guess_user_display
        self.interaction = interaction  # Store the interaction for later use

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        e = discord.Embed(
            title="Time's up!",
            description=f"The user was... {self.guess_user}",
            color=Color.negative,
        )
        await self.interaction.message.edit(view=self)
        await self.interaction.followup.send(embed=e)

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.red)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Pass the current view (self) to the modal
        await interaction.response.send_modal(
            Questionnaire(self.guess_user, self.guess_user_display, view=self)
        )


async def setup(bot):
    await bot.add_cog(fun(bot))
