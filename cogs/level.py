from main import *
from PIL import Image, ImageDraw, ImageFont, ImageOps


def xp_to_level(xp):
    level = 1  # Start at level 1
    xp_needed = 100  # XP needed for level 2
    increment = 50  # Each level requires 50 more XP than the last
    
    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed += increment  # Increase XP requirement for next level
    
    return level
class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Track and reward users for activity"
    @commands.Cog.listener("on_message")
    async def level_event(self, message):
        try:
            
            
            guild = message.guild
            if message.author.bot:
                return
            user = message.author

            # Load config
            per_message_default = get_config_defaults()["level"]["per_message"]
            guild_config = get_guild_config(guild.id)
            xp_per_message = guild_config["modules"]["level"]["per_message"] or per_message_default
            channel = await self.bot.fetch_channel(guild_config["modules"]["level"]["levelup"]["channel"])
            # Load guild data
            data_path = f"data/guilds/{guild.id}.json"
            try:
                with open(data_path, "r") as f:
                    data = json.load(f)
            except FileNotFoundError:
                print("Guild data file not found!")  # ✅ Check if data file exists
                embed = discord.Embed(
                    title="Moderation must run </settings init:1338195438494289964> before using this command.",
                    color=0xfd3553
                )
                embed.set_footer(text="Report this error to moderation.")
                await message.channel.send(embed=embed)
                return

            # Initialize level tracking if missing
            data.setdefault("stats", {}).setdefault("level", {}).setdefault("users", {}).setdefault(str(user.id), {"xp": 0})
            data["stats"]["level"]["users"][str(user.id)]["xp"] += int(xp_per_message)
            
            # Save the updated data
            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

            # Calculate Levels
            old_level = xp_to_level(data["stats"]["level"]["users"][str(user.id)]["xp"] - int(xp_per_message))
            new_level = xp_to_level(data["stats"]["level"]["users"][str(user.id)]["xp"])
            if new_level <= old_level:
                return
            
            # gen image
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

            img_path = f"data/guilds/{message.guild.id}_{message.author.id}_level.png"
            img.save(img_path)
            try:
                await channel.send(
                    content=f"## {user.mention} [{data['level']['users'][str(user.id)]['xp']} XP] {old_level} > {new_level}! 🎉",
                    file=discord.File(img_path)
                )
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path)
                    


            # Save the updated data
            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"❌ ERROR: {e}")
            traceback.print_exc()  # ✅ Print full error traceback


    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @verify()
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @app_commands.allowed_installs(guilds=True,users=False)
    @commands.hybrid_group(name="level", description="Track and reward users for activity")
    async def level(self, ctx):
        pass
    #* writing code can be painful sometimes
    @verify()
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="get", description="Check your current level.")
    async def level_get(self, ctx, user:discord.User=None):
        if user==None:
            user = ctx.author
        data_path = f"data/guilds/{ctx.guild.id}.json"
        try:
            with open(data_path, "r") as f:
                data = json.load(f)
            
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

            img_path = f"data/guilds/{ctx.guild.id}_{ctx.author.id}_level.png"
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
    @verify()
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="top", description="View the most active members of the server")
    async def leveltop(self, ctx):
        data_path = f"data/guilds/{ctx.guild.id}.json"
        try:
            with open(data_path,"r") as f:
                data = json.load(f)
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
                    d.text(((450-16), 16 + (i - 1) * 48), f"Level {level} • {xp} XP", font=font_light, fill=(255, 255, 255), anchor="rt")
                    d.text((56, 16 + (i - 1) * 48), str(i) + ". " + user.name, font=font, fill=(255, 255, 255), anchor="lt")
                    

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
    async def levelset(self,ctx,user:discord.User, xp:int):
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
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @level.command(name="refresh",description="synchronizes all levels and grants role rewards. administrator only")
    async def levelrefresh(self, ctx):
        start_time = time.time()
        if not ctx.author.guild_permissions.administrator:
            await ctx.reply("You do not have permission to use this command.")
            return
        total_users = len(ctx.guild.members)
        estimated_time = (total_users * 0.1) * 2
        await ctx.reply(f"levels/roles refresh started. the results will be sent soon. estimated time: {estimated_time:.1f} seconds.", ephemeral=False)

        data_path = f"data/guilds/{ctx.guild.id}.json"
        try:
            with open(data_path, "r") as f:
                data = json.load(f)
            
            users = data.get("stats",{}).get("level", {}).get("users", {})
            for user_id, user_data in users.items():
                guild = ctx.guild
                user = guild.get_member(int(user_id))
                xp = user_data.get("xp", 0)
                level = xp_to_level(xp)
                # Update user roles based on level
                guild = ctx.guild
                guild_config = get_guild_config(guild.id)

            with open(data_path, "w") as f:
                json.dump(data, f, indent=4)
            affected_users = []
            for user_id, user_data in users.items():
                user = guild.get_member(int(user_id))
                if user is None:
                    continue
                xp = user_data.get("xp", 0)
                level = xp_to_level(xp)
                # Update user roles based on level
                level_roles = guild_config["modules"]["level"]["rewards"]
                for role_level, role_id in level_roles.items():
                    role = guild.get_role(role_id)
                    if role is not None:
                        if level >= int(role_level):
                            if role not in user.roles:
                                await user.add_roles(role)
                                affected_users.append(f"{user.mention} ({level} • {xp}xp) - Added role <@&{role.id}>")
                        else:
                            if role in user.roles:
                                await user.remove_roles(role)
                                affected_users.append(f"{user.mention} ({level} • {xp}xp) - Removed role <@&{role.id}>")
                end_time = time.time()
                elapsed_time = end_time - start_time

                e = discord.Embed(
                    title="Leveling refresh complete",
                    description=f"## Users affected:\n" + "\n".join(affected_users) if affected_users else "No changes were made.",
                    color=0xffffff
                )
                time_difference = elapsed_time - estimated_time
                time_diff_sign = "+" if time_difference > 0 else "-"
                e.add_field(name="time elapsed", value=f"`{elapsed_time:.2f}s ({time_diff_sign}{abs(time_difference):.2f}s from estimate)`")
            await ctx.reply(embed=e)
            
        except FileNotFoundError:
            await ctx.reply("Guild config not found. Please report this to the administrators. (/settings init)")
async def setup(bot):
    await bot.add_cog(Level(bot))
