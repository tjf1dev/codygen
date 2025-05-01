from main import *
import discord.ext.commands
class uotm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "user of the month - manage events"
    
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")
    @commands.hybrid_group(name="uotm",description="user of the month")
    async def uotm(self,ctx):
        pass
    @uotm.command(name="vote", description="vote for one of the uotm candidates")
    async def vote(self,ctx, user: discord.User):
        config = await get_guild_config(ctx.guild.id)
        if not config["modules"]["uotm"]["enabled"]:
            await ctx.send("This module is disabled.",ephemeral=True)
            return
        candidates = config["stats"]["uotm"]["candidates"]
        if ctx.author.id == user.id:
            await ctx.send("you can't vote for yourself!",ephemeral=True)
            return
        if user.bot:
            await ctx.send("you can't vote for a bot!",ephemeral=True)
            return
        if config["stats"]["uotm"]["users"].get(f"{ctx.author.id}",{"vote":None})["vote"] != None:
            await ctx.send("you have already voted!",ephemeral=True)
            return
        if candidates in [{},None]:
            e = discord.Embed(
                title=f"{user.name} is not a candidate!",
                description="use `/uotm view` to see the current candidates,\nyou can use use `/uotm apply` to apply for a candidate!\n## please make sure that this server has UOTM enabled!",
            )
            await ctx.send(embed=e,ephemeral=True)
        for c in candidates:
            if c["id"] == user.id:
                c["votes"] += 1
                await ctx.send(f"you have voted for {user.name}!",ephemeral=True)
        set_guild_config_key(ctx.guild.id, f"stats.uotm.candidates", candidates) 
        set_guild_config_key(ctx.guild.id, f"stats.uotm.users.{ctx.author.id}.vote", user.id)
        return
    @uotm.command(name="apply", description="apply for uotm")
    async def apply(self,ctx):
        config = await get_guild_config(ctx.guild.id)
        if not config["modules"]["uotm"]["enabled"]:
            await ctx.send("This module is disabled.",ephemeral=True)
            return
        candidates = config["stats"]["uotm"]["candidates"]
        if candidates in [{},None]:
            candidates = []
        for c in candidates:
            if c["id"] == ctx.author.id:
                await ctx.send("you are already a candidate!",ephemeral=True)
                return
        candidates.append({
            "id": ctx.author.id,
            "votes": 0,
        })
        set_guild_config_key(ctx.guild.id, "stats.uotm.candidates", candidates)
        await ctx.send("you are now candidate for user of the month!",ephemeral=True)
    @uotm.command(name="leave", description="remove yourself from uotm")
    async def leave(self,ctx):
        config = await get_guild_config(ctx.guild.id)
        if not config["modules"]["uotm"]["enabled"]:
            await ctx.send("This module is disabled.",ephemeral=True)
            return
        candidates = config["stats"]["uotm"]["candidates"]
        if candidates in [{},None]:
            await ctx.send("you are not a candidate!",ephemeral=True)
            return
        for c in candidates:
            if c["id"] == ctx.author.id:
                candidates.remove(c)
                set_guild_config_key(ctx.guild.id, "stats.uotm.candidates", candidates)
                await ctx.send("you are no longer a candidate for user of the month!",ephemeral=True)
                return
    @commands.has_permissions(administrator=True)
    @uotm.command(name="finish", description="wipe uotm votes and finish the current month")
    async def finish(self,ctx):
        config = await get_guild_config(ctx.guild.id)
        if not config["modules"]["uotm"]["enabled"]:
            await ctx.send("This module is disabled.",ephemeral=True)
            return
        
        e = discord.Embed(
            title="uotm - finished!",
            description="the current month has been finished!",
            color=0x0000ff
        )

        candidates = config["stats"]["uotm"]["candidates"]
        if candidates in [{},None]:
            await ctx.send("No candidates have been set yet.",ephemeral=True)
            return
        candidates = config["stats"]["uotm"]["candidates"]
        if not candidates:
            await ctx.send("No votes have been cast yet.")
            return
        vote_count = {}
        for c in candidates:
            vote_count[c["id"]] = {"votes":c["votes"]}
        # Calculate total votes
        total_votes = sum(candidate["votes"] for candidate in vote_count.values())

        # Sort candidates by votes (highest to lowest)
        sorted_candidates = sorted(
            vote_count.items(), key=lambda x: x[1]["votes"], reverse=True
        )

        top_3 = sorted_candidates[:3]  # Get the top 3 candidates

        results_embed = discord.Embed(
            title="winners",
            color=discord.Color.blurple()
        )

        for candidate_id, data in top_3:
            candidate = await self.bot.fetch_user(int(candidate_id))
            count = data["votes"]

            percentage = (count / total_votes * 100) if total_votes > 0 else 0  # Avoid division by zero

            results_embed.add_field(
                name=candidate.name,
                value=f"{count} votes ({percentage:.2f}%)",
                inline=False
            )
        set_guild_config_key(ctx.guild.id, "stats.uotm.candidates", {})
        set_guild_config_key(ctx.guild.id, "stats.uotm.users", {})
        await ctx.send(embeds=[e,results_embed],ephemeral=False)
    @uotm.command(name="view", description="view current uotm standings")
    async def view(self,ctx):
        # sourced from the og "tjf1" bot :3    
        vote_count = {}
        candidates = await get_guild_config(ctx.guild.id)["stats"]["uotm"]["candidates"]
        if candidates in [{},None]:
            await ctx.send("No candidates have been set yet.",ephemeral=True)
            return
        for c in candidates:
            vote_count[c["id"]] = c["votes"]

        total_votes = sum(vote_count.values())
        results_embed = discord.Embed(
            title=f"UOTM results",
            description="remember: you can use use `/uotm apply` to apply for a candidate!\ncurrent standings:",
            color=0x00ff00
        )

        sorted_candidates = sorted(
            vote_count.items(), key=lambda x: x[1], reverse=True
        )
        for candidate_id, count in sorted_candidates:
            candidate = await self.bot.fetch_user(int(candidate_id))
            
            if total_votes > 0:
                percentage = (count / total_votes) * 100
            else:
                percentage = 0  # Avoid division by zero
            
            results_embed.add_field(
                name=candidate.name,
                value=f"{count} votes ({percentage:.2f}%)",
                inline=False
            )

        await ctx.reply(embed=results_embed, ephemeral=True)

    
async def setup(bot):
    await bot.add_cog(uotm(bot))