from main import *

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Get information about certain things"
    @commands.hybrid_group(name="info",description="get information about certain things")
    async def info(self,ctx: commands.Context):
        pass
    @info.command(name="user", description="view information about a user.")
    async def user(self, ctx: commands.Context, user: discord.Member | discord.User = None):
        if not user: 
            ref = ctx.message.reference
            if ref:
                user = ref.resolved.author
            else:
                user = ctx.author
        if user.avatar:
            avatar = f"[avatar]({user.avatar.url})"
        else:
            avatar = ""
        if user.banner:
            banner = f"[banner](<{user.banner.url}>)"
        else:
            banner = ""
        e = discord.Embed(
            description=f"# {user.mention}\n"
            f"display name: {user.display_name}\n"
            f"username: {user.name}\n"
            f"id: {user.id}\n"
            f"created: <t:{round(user.created_at.timestamp())}:R> (<t:{round(user.created_at.timestamp())}:D>)\n"
            f"{avatar}" + (" · " if user.banner else "") + f"{banner}\n"
            + (
                f"\nroles: {len(user.roles)}\njoined: <t:{round(user.joined_at.timestamp())}:R> (<t:{round(user.joined_at.timestamp())}:D>)"
                if isinstance(user, discord.Member)
                else ""
            )
        )

        e.set_thumbnail(url=user.avatar.url if user.avatar else None) 
        await ctx.reply(embed=e, mention_author=False)
        
    @app_commands.allowed_contexts(guilds=True,dms=False,private_channels=False)
    @info.command(name="guild", description="view information about this server.")
    async def guild(self, ctx: commands.Context):
        guild = ctx.guild
        roles = await guild.fetch_roles()
        members = guild.members
        channels = await guild.fetch_channels()
        bots = []
        users = []
        for m in members:
            if m.bot:
                bots.append(m)
            else:
                users.append(m)
        voice_channels = []
        text_channels = []
        other_channels = []
        for c in channels:
            if c.type == discord.ChannelType.voice:
                voice_channels.append(c)
            if c.type == discord.ChannelType.text:
                text_channels.append(c)
            else:
                if c.type != discord.ChannelType.category:
                    other_channels.append(c)

        
        e = discord.Embed(
            title=f"",
            description=f"# about {guild.name}\n"
                f"id: {guild.id}\n"
                f"owner: {guild.owner.mention}\n"
                f"roles: {len(roles)}\n"
                f"created: <t:{round(guild.created_at.timestamp())}:R> (<t:{round(guild.created_at.timestamp())}:D>)\n"
                f"[icon url](<{guild.icon.url}>)\n"
                f"## channels\n"
                f"total: {len(channels)}\n"
                f"text: {len(text_channels)}\n"
                f"voice: {len(voice_channels)}\n"
                f"other: {len(other_channels)}\n\n"
                f"## members\n"
                f"total: {len(members)}\n"
                f"bots: {len(bots)}\n"
                f"users: {len(users)}",
            color=Color.white
        )
        e.set_thumbnail(url=guild.icon.url)
        await ctx.reply(embed=e)
async def setup(bot):
    await bot.add_cog(Info(bot))