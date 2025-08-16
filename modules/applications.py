import discord
from discord.ext import commands
from discord import app_commands
from main import Color, custom_api_request
from dateutil import parser


class applications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Manage server applications, if you have them enabled."

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="applications",
        description="Manage server applications, if you have them enabled.",
    )
    async def apps(self, ctx: commands.Context):
        pass

    @commands.has_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @apps.command(
        name="view-form",
        description="View the server's application form. This category is still in development",
    )
    async def view_form(self, ctx: commands.Context):
        raw = await custom_api_request(
            self.bot, f"/guilds/{ctx.guild.id}/member-verification", auth=True
        )
        req, json = raw[0], raw[1]
        if not req.ok:
            fail = discord.Embed(
                title="failed to fetch information.",
                description=f"code: {req.status_code}, [endpoint used]({req.url})",
                color=Color.negative,
            )
            await ctx.reply(embed=fail)
            return
        form = json
        dt = parser.isoparse(form["version"])
        udt = int(dt.timestamp())
        e1 = discord.Embed(title="about", color=0x00CCFF)
        e1.add_field(name="description", value=form["description"], inline=False)
        e1.add_field(
            name="last updated", value=f"<t:{udt}:R> (<t:{udt}:f>)", inline=False
        )
        e2 = discord.Embed(title="rules", color=0x00FFF7)
        for rule in form["form_fields"][0]["values"]:
            e2.add_field(name="", value=rule, inline=False)
        e3 = discord.Embed(title="questions", color=0x00FFA2)
        for q in form["form_fields"]:
            if q["field_type"] == "TERMS":
                pass
            else:
                if q["required"]:
                    name = f"{q['field_type']}, required"
                else:
                    name = f"{q['field_type']}"
                e3.add_field(name=name, value=q["label"], inline=False)
        await ctx.reply(embeds=[e1, e2, e3])


async def setup(bot):
    await bot.add_cog(applications(bot))
