import discord
from models import Codygen


async def get_xp(user: discord.Member, bot: Codygen):
    query = await (
        await bot.db.execute(
            "SELECT xp FROM users WHERE guild_id=? AND user_id=?",
            (user.id, user.guild.id),
        )
    ).fetchone()
    if query:
        return query[0]
