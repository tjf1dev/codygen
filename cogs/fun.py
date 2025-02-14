from main import *
import discord, random, json, csv
import stats.stats

class fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description="fun commands!"

    @commands.hybrid_group(name="fun", description="fun commands!", invoke_without_command=True)
    async def fun_group(self, ctx):
        pass
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @verify()
    @fun_group.command(name="ship", description="SHIP TWO PEOPLE")
    async def ship(self, ctx, user1: discord.User = None, user2: discord.User = None):
        if user2 is None:
            user2 = ctx.author
        name1 = user1.name
        name2 = user2.name
        shipname = name1[:2] + name2[-2:]
        if user1.id in [978596696156147754, 1277351272147582990] and user2.id in [978596696156147754, 1277351272147582990]:
            embed=discord.Embed(
                title=f"ship",
                description=f"ship between {user1.mention} and {user2.mention} is ??? way too high idk",
                color=0xf53d82
            )
            embed.set_footer(
                text=f"name of this ship is {shipname}"
            )
            await ctx.reply(embed=embed)
        elif user1 == user2:
            embed=discord.Embed(
                title=f"ship",
                description=f"ship between {user1.mention} and {user2.mention} is ??? way too high idk",
                color=0xf53d82
                )
            embed.set_footer(text=f"name of this ship is {shipname}")
            await ctx.reply(embed=embed)
        else:
            embed=discord.Embed(
                title=f"ship",description=f"ship between {user1.mention} and {user2.mention} is {random.randint(0,100)}%",color=0xf53d82)
            await ctx.reply(embed=embed)
            

    @verify()
    @fun_group.command(name="awawawa", description="awawawawawawa")
    async def awawawa(self, ctx):
        await ctx.reply(random.choice(words), ephemeral=True)

    @verify()
    @fun_group.command(name="randomword", description="get random word from english dictionary")
    async def randomword(self, ctx):
        with open("assets/randomword.txt", "r") as file:
            text = file.read()
            words = list(map(str, text.split()))
            await ctx.reply(random.choice(words))

    @verify()
    @fun_group.command(name="cute", description="cute command")
    async def cute(self, ctx, user: discord.User = None):
        if user:
            await ctx.reply(f"{user.mention} is cute and silly :3")
        else:
            await ctx.reply("you are cute and silly :3", ephemeral=True)

    @verify()
    @fun_group.command(name="wokemeter", description="see how WOKE someone is!")
    async def wokemeter(self, ctx, user: discord.User = None):
        config = get_guild_config(ctx.guild.id)["commands"]["wokemeter"]
        woke_min = config["woke_min"]
        woke_max = config["woke_max"]
        woke_max = get_value_from_guild_config(ctx.guild.id, "woke_max")
        if user is None:
            user = ctx.author
        elif user.id == 1266572586528280668:
            await ctx.reply(f"{user.mention} is 101% woke")
        if user.bot:
            await ctx.reply(f"bots cant be woke :broken_heart:")
        else:
            await ctx.reply(f"{user.mention} is {random.randint(int(woke_min), int(woke_max))}% woke")

    # @verify()
    # @fun_group.command(name="whosthecutest", description="who is the cutest")
    # async def whosthecutest(self, ctx):
    #     await ctx.reply(r"<@978596696156147754>")
        
    @verify()
    @fun_group.command(name="wokegame", description="Check is the game woke!")
    async def wokegame(self,ctx, game:str):
        with open('assets/wokegames.csv', mode='r', encoding="utf-8") as wokelist:    
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
                        color = 0xea0006
                    elif wokeness == "0":
                        rate = "Slightly woke!"
                        color = 0xe4b805
                    elif wokeness == "1":
                        rate = "Not woke!"
                        color = 0x2fea00
                    else:
                        rate = "How the fuck did that happen"
                    
                    embed=discord.Embed(title=rate, description=description, color=color)
                    embed.set_footer(text=f"{name}, {appID}")
                    embed.set_image(url=banner)
                    await ctx.send(embed=embed)
                    return
            fail = discord.Embed(
                title="cant find the game",
                color=0xff0000
            )
            await ctx.send(embed=fail)

        # Zgaduj!
    @verify()
    @fun_group.command(name="guess", description="Guess the user by pfp!")
    async def guess(self, ctx):
        global guessUser
        global guessUserDisplay
        users = ctx.guild.members  # Lista wszystkich uczestników serwera
        
        try:
            async with asyncio.timeout(5):
                while True:
                    user = random.choice(users)
                    if not user.bot:
                        break
        except asyncio.TimeoutError:
            e = discord.Embed(
                title="sorry, we couldn't find a user to guess :broken_heart:",
                color=0xff0000
            )
        guessUser = user.name # Nazwa użytkownika
        guessUserDisplay = user.display_name # Nazwa wyświetlana
        pfp = user.avatar.url  # URL awataru, do zgadywanki.

        # Wiadomość!
        embed = discord.Embed(title=" ", description="Who is that?", color=0x8ff0a4)
        embed.set_author(name="Which user is that??")
        embed.set_image(url=pfp)
        await ctx.send(embed=embed, view=guessButtons(guess_user=guessUser, guess_user_display=guessUserDisplay))  # Send message to the channel
    
    
    @verify()
    @fun_group.command(name="guessrank", description="Check how many times have you guessed!")
    async def guessrank(self,ctx):
        invoker = ctx.author
        invokerName = ctx.author.name

        randomColor = random.randrange(0, 2**24)
        randomHex = hex(randomColor)
        randomHexINT = int(randomHex,16)

        value = stats.stats.getUserValue(invokerName)

        if value == 1:
            raz = "time"
        else:
            raz = "times"

        embed = discord.Embed(color=randomHexINT)
        embed.add_field(name="User %s guessed %s %s!" % (invokerName, str(value), raz), value=" ", inline=True)
        embed.set_image(url=ctx.author.avatar.url)  # Awatar Jupii
        await ctx.send(embed=embed)

    @verify()
    @fun_group.command(name="guesstop", description="Guess the user by pfp!")
    async def guesstop(self,ctx):
        topValues = stats.stats.getAllValues()
        top = {k: v for k, v in sorted(topValues.items(), key=lambda item: item[1], reverse=True)}

        randomColor = random.randrange(0, 2**24)
        randomHex = hex(randomColor)
        randomHexINT = int(randomHex,16)

        embed = discord.Embed(color=randomHexINT)
        for x, (user, value) in enumerate(top.items(), start=1):
            if value == 1:
                raz = "time"
            else:
                raz = "times"
            embed.add_field(name=f"{x}. {user}", value=f"Guessed {value} {raz}.")
        
        await ctx.send(embed=embed)

    @verify() 
    @fun_group.command(name="cat",description="get a random pic of a cat :3") 
    async def cat(self,ctx):
        url = get_global_config()["commands"]["cat"]["url"]
        req = requests.get(url)
        e = discord.Embed(
            title=":3",
            color=0xffffff
        )
        e.set_image(url=req.json()[0]["url"])
        await ctx.reply(embed=e)
                
# Guziki dla komendy zgaduj.
class guessButtons(discord.ui.View):
    def __init__(self, guess_user, guess_user_display, *, timeout=180): # Po trzech minutach od wysłania wiadomości guziki staną się nieaktywne.
        super().__init__(timeout=timeout)
        self.guess_user = guess_user
        self.guess_user_display = guess_user_display

    @discord.ui.button(label="Guess", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Questionnaire(self.guess_user, self.guess_user_display))
class Questionnaire(discord.ui.Modal, title='Guess the user!'):
    name = discord.ui.TextInput(label='Which user is that??')

    def __init__(self, guess_user, guess_user_display, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guess_user = guess_user
        self.guess_user_display = guess_user_display

    async def on_submit(self, interaction: discord.Interaction):
        guessOG = self.name
        guessLowercase = str(guessOG).lower()

        # zadziała np i THERI i theri i Theri i THeRi...
        guessUserDisplayLowercase = str(self.guess_user_display).lower()

        # Sprawdź czy użytkownik trafił albo na poprawną nazwę wyświetleniową albo na poprawną nazwę użytkownika.
        # Np: i "theri" i "theridev" zadziała.
        if guessLowercase == self.guess_user.lower() or guessLowercase == guessUserDisplayLowercase:
            embed = discord.Embed(color=0x8ff0a4)
            embed.add_field(name=f"{interaction.user.name} guessed it! This user is %s" % self.guess_user, value=" ", inline=True)
            stats.stats.add(interaction.user.name, 1)
            await interaction.response.send_message(embed=embed)
        else:
            # ups
            embed = discord.Embed(color=0xe01b24)
            embed.add_field(name=f"Wrong! This user is NOT {guessLowercase}", value=" ", inline=True)
            await interaction.response.send_message(embed=embed)



async def setup(bot):
    await bot.add_cog(fun(bot))