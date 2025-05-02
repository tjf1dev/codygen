from main import *
from PIL import Image, ImageDraw, ImageFont, ImageOps
import traceback
def split_embed_description(lines, max_length=4096):
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > max_length:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks
def _old_xp_to_level(xp):
    level = 1
    xp_needed = 100
    increment = 50
    
    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed += increment
    
    return level
def xp_to_level(xp):
    level = 1
    while xp >= 75 * (level ** 1.15):
        xp -= 75 * (level ** 1.15)
        level += 1
    return level
def boost_value(value, percentage):
    return value * (1 + percentage / 100)
class level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Track and reward users for activity"
    @commands.Cog.listener("on_message")
    async def level_event(self, message):
        guild = message.guild
        if message.author.bot:
            return
        logger.debug("test")
        user = message.author
        guild_config = await get_guild_config(guild.id)
        logger.debug("guild config gathered")
        per_message_default = get_config_defaults()["modules"]["level"]["per_message"]
        xp_per_message = guild_config.get("modules", {}).get("level", {}).get("per_message", per_message_default)
        channel_id = guild_config.get("modules", {}).get("level", {}).get("levelup", {}).get("channel")
        if not channel_id:
            return
        channel = await self.bot.fetch_channel(channel_id)
        
        users = guild_config.get("stats", {}).get("level", {}).get("users", {})
        user_xp = users.get(str(message.author.id), {}).get("xp", 0)
        boosts: dict = guild_config.get("modules", {}).get("level", {}).get("boost", {})
        logger.debug("all boosts gathered")
        global_boost: dict = boosts.get("global", {"percentage": 0, "expires": 0})
        if global_boost.get("expires") < time.time():
            global_boost_value = 0
        else:
            global_boost_value = global_boost.get("percentage")

        role_boosts: dict = boosts.get("role", {})
        user_boosts: dict = boosts.get("user", {})
        logger.debug("role and user boosts gathered")
        highest_boost = global_boost_value
        user_boost = user_boosts.get(str(user.id), {"expires": 0, "percentage": 0})
        if user_boost["expires"] > time.time():
            highest_boost = max(highest_boost, user_boost["percentage"])
        logger.debug("user boost gathered")
        for role in user.roles:
            role_boost = role_boosts.get(str(role.id), {"expires": 0, "percentage": 0})
            if role_boost["expires"] > time.time():
                highest_boost = max(highest_boost, role_boost["percentage"])
        logger.debug("role boost gathered")
        xp_with_boost = xp_per_message * (1 + highest_boost / 100)
        logger.debug(f"highest boost: {highest_boost}")
        await set_guild_config_key(guild.id, f"stats.level.users.{message.author.id}.xp", int(user_xp + xp_with_boost))

        old_level = xp_to_level(guild_config["stats"]["level"]["users"][str(message.author.id)]["xp"] - int(xp_with_boost))
        new_level = xp_to_level(guild_config["stats"]["level"]["users"][str(message.author.id)]["xp"])

        try:
            level_roles = guild_config["modules"]["level"]["rewards"]
            for role_level, role_id in level_roles.items():
                role = guild.get_role(role_id)
                if role is not None:
                    if new_level >= int(role_level):
                        if role not in user.roles:
                            await user.add_roles(role)
                    else:
                        if role in user.roles:
                            await user.remove_roles(role)
        except FileNotFoundError:
            pass

        if new_level <= old_level:
            return

        await channel.send(
            f"## {user.mention}\nyou are now level **{new_level}**!\nxp: **{user_xp}**"
            f"\nxp boost: **{highest_boost}%**!" if highest_boost != 0 else ""
        )




    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @app_commands.allowed_installs(guilds=True,users=False)
    @commands.hybrid_group(name="level", description="Track and reward users for activity")
    async def level(self, ctx: commands.Context):
        pass
    #* writing code can be painful sometimes
    # this hurts

    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="get", description="Check your current level.")
    async def level_get(self, ctx: commands.Context, user:discord.User=None):
        if user==None:
            user = ctx.author
        try:
            data = await get_guild_config(ctx.guild.id)
            users = data.get("stats",{}).get("level", {}).get("users", {})
            sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
            place_in_leaderboard = next(
                (i for i, (user_id, _) in enumerate(sorted_users, start=1) if user_id == str(user.id)), None
            )
            xp = users.get(str(user.id), {}).get("xp", 0)
            level = xp_to_level(xp)
            
            img = Image.new("RGB", (256, 256), color=(0, 0, 0))
            d = ImageDraw.Draw(img)
            
            font_bold = ImageFont.truetype("assets/ClashDisplay-Bold.ttf", 96)
            font = ImageFont.truetype("assets/ClashDisplay-Regular.ttf", 24)
            font_light = ImageFont.truetype("assets/ClashDisplay-Extralight.ttf", 22)

            avatar_asset = user.display_avatar.replace(size=32 )
            buffer = io.BytesIO(await avatar_asset.read())
            avatar = Image.open(buffer).convert("RGBA").resize((32, 32))

            mask = Image.new("L", (32, 32), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, 32, 32), fill=255)

            avatar = ImageOps.fit(avatar, (32, 32))
            avatar.putalpha(mask)

            img.paste(avatar, (16,16), avatar)
            d.text((56, (16+4)), user.name, font=font, fill=(255, 255, 255), anchor="lt")

            d.text((128, 128), str(level), font=font_bold, fill=(255, 255, 255), anchor="mm")
            d.text((128, 210), f"{xp}xp • #{place_in_leaderboard}", font=font_light, fill=(255, 255, 255), anchor="mm")
            if not os.path.exists("cache"):
                os.makedirs("cache",exist_ok=True)
            img_path = f"cache/{ctx.guild.id}_{ctx.author.id}_level.png"
            img.save(img_path)
            
            try:
                await ctx.reply(file=discord.File(img_path))
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path)

        except FileNotFoundError:
            await ctx.reply("guild config not found. please report this to the administrators. (/settings init)")
        except FileNotFoundError:
            await ctx.reply("guild config not found. please report this to the administrators. (/settings init)")

    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="top", description="View the most active members of the server")
    async def leveltop(self, ctx: commands.Context):
        try:
                data = await get_guild_config(ctx.guild.id)
                users = data.get("stats",{}).get("level", {}).get("users", {})
                sorted_users = sorted(users.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
                img = Image.new("RGB", (450, 512), color=(0, 0, 0))
                d = ImageDraw.Draw(img)

                font_bold = ImageFont.truetype("assets/ClashDisplay-Bold.ttf", 48)
                font = ImageFont.truetype("assets/ClashDisplay-Regular.ttf", 24)
                font_light = ImageFont.truetype("assets/ClashDisplay-Extralight.ttf", 22)

                valid_users = []
                count = 0
                for user_id, user_data in sorted_users:
                    user = ctx.guild.get_member(int(user_id))
                    if user is not None and count < 10:
                        valid_users.append((user_id, user_data))
                        count += 1

                for i, (user_id, user_data) in enumerate(valid_users[:10], start=1):
                    user = ctx.guild.get_member(int(user_id))
                    if user is None:
                        continue
                    xp = user_data.get("xp", 0)
                    level = xp_to_level(xp)
                    
                    avatar_asset = user.display_avatar.replace(size=32)
                    buffer = io.BytesIO(await avatar_asset.read())
                    avatar = Image.open(buffer).convert("RGBA").resize((32, 32))

                    mask = Image.new("L", (32, 32), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.ellipse((0, 0, 32, 32), fill=255)

                    avatar = ImageOps.fit(avatar, (32, 32))
                    avatar.putalpha(mask)

                    img.paste(avatar, (16, 16 + (i - 1) * 48), avatar)
                    d.text(((450-16), 16 + (i - 1) * 48), f"Level {level} • {xp}xp", font=font_light, fill=(255, 255, 255), anchor="rt")
                    if len(user.name) < 13:
                        d.text((56, 16 + (i - 1) * 48), str(i) + ". " + user.name, font=font, fill=(255, 255, 255), anchor="lt")
                    else:
                        d.text((56, 16 + (i - 1) * 48), str(i) + ". " + user.name[:12]+"...", font=font, fill=(255, 255, 255), anchor="lt")

                img_path = f"data/guilds/{ctx.guild.id}_level_top.png"
                img.save(img_path)

                try:
                    await ctx.reply(file=discord.File(img_path))
                finally:
                    if os.path.exists(img_path):
                        os.remove(img_path)
        except FileNotFoundError:
            await ctx.reply("guild config not found. please report this to the administrators. (/settings init)")
    @verify()
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="set", description="set a user's xp. requires administrator permissions")
    async def levelset(self,ctx: commands.Context,user:discord.User, xp:int):
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("You do not have permission to use this command.")
            return
        if user==None:
            user = ctx.author
        data_path = f"data/guilds/{ctx.guild.id}.json"
        try:
            with open(data_path, "r") as f:
                data = json.load(f)
                
                data.setdefault("stats", {}).setdefault("level", {}).setdefault("users", {}).setdefault(str(user.id), {"xp": 0})
                data["stats"]["level"]["users"][str(user.id)]["xp"] = xp

                with open(data_path, "w") as f:
                    json.dump(data, f, indent=4)

                await ctx.reply(f"set {user.name}'s XP to {xp}.",ephemeral=True)
        except FileNotFoundError:
            await ctx.reply("guild config not found. please report this to the administrators. (/settings init)")
    @verify()
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @level.command(name="refresh", description="synchronizes all levels and grants role rewards. administrator only")
    async def levelrefresh(self, ctx: commands.Context):
        start_time = time.time()
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("you do not have permission to use this command.")
            return

        total_users = len(ctx.guild.members)
        estimated_time = (total_users * 0.1) * 2
        await ctx.reply(f"levels/roles refresh started. the results will be sent soon. estimated time: {estimated_time:.1f} seconds.", ephemeral=False)

        data_path = f"data/guilds/{ctx.guild.id}.json"
        try:
            with open(data_path, "r") as f:
                data = json.load(f)

            users = data.get("stats", {}).get("level", {}).get("users", {})
            guild = ctx.guild
            guild_config = await get_guild_config(guild.id)
            affected_users = []

            for user_id, user_data in users.items():
                user = guild.get_member(int(user_id))
                if user is None:
                    continue
                xp = user_data.get("xp", 0)
                level = xp_to_level(xp)
                level_roles = guild_config["modules"]["level"]["rewards"]
                for role_level, role_id in level_roles.items():
                    role = guild.get_role(role_id)
                    if role:
                        if level >= int(role_level):
                            if role not in user.roles:
                                await user.add_roles(role)
                                affected_users.append(f"{user.mention} ({level} • {xp}xp) - added role <@&{role.id}>")
                        else:
                            if role in user.roles:
                                await user.remove_roles(role)
                                affected_users.append(f"{user.mention} ({level} • {xp}xp) - removed role <@&{role.id}>")

            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

            end_time = time.time()
            elapsed_time = end_time - start_time
            time_difference = elapsed_time - estimated_time
            time_diff_sign = "+" if time_difference > 0 else "-"

            if not affected_users:
                await ctx.reply("no changes were made.")
                return

            chunks = split_embed_description(affected_users)
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    description="## users affected:\n" + chunk,
                    color=Color.white
                )
                if i == len(chunks) - 1:
                    embed.title = "leveling refresh complete"
                    embed.add_field(
                        name="time elapsed",
                        value=f"`{elapsed_time:.2f}s ({time_diff_sign}{abs(time_difference):.2f}s from estimate)`"
                    )
                await ctx.send(embed=embed)

        except FileNotFoundError:
            await ctx.reply("guild config not found. please report this to the administrators. (/settings init)")
async def setup(bot):
    await bot.add_cog(level(bot))
