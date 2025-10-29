from discord.ext import commands
from discord import app_commands
from ext.ui_base import Message
import discord
from main import Color, get_prefix, logger
import aiosqlite
from typing import AsyncGenerator
import asyncio
from views import InitStartLayout
from PIL import Image
from io import BytesIO

# enabling this allows using a prefixed command for /settings init
no_app_force = False


def recursive_update(original: dict, template: dict) -> dict:
    """Recursively update a dictionary with missing keys from a template."""
    for key, value in template.items():
        if isinstance(value, dict):
            original[key] = recursive_update(original.get(key, {}), value)
        else:
            original.setdefault(key, value)
    return original


class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "settings to manage your bot instance."

    async def cog_load(self):
        logger.ok(f"loaded {self.__class__.__name__}")

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"{self.__class__.__name__}: loaded.")

    @app_commands.checks.has_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.hybrid_group(
        name="settings", description="settings to manage your bot instance."
    )
    async def settings(self, ctx: commands.Context):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(
        name="config", description="view the configuration for your server"
    )
    async def config(self, ctx: commands.Context):
        await ctx.reply(
            view=Message(
                "due to data system migration, server configurations are currently disabled."
            ),
            ephemeral=True,
        )

    async def setup_guild(
        self, guild: discord.Guild, gtype: int = 1
    ) -> AsyncGenerator[discord.ui.View | discord.ui.LayoutView, bool]:
        """
        Setup (initalize) a guild.
        Replaces on_guild_join and /settings init functions, and is shared between them.
        Returns embeds in realtime.
        Arguments:
            guild: `discord.Guild` object with the guild to setup.
            type: 1 = already existing guild, 2 = newly added guild
        """
        # gtype spoof for testing
        # gtype = 2
        logger.debug(f"now setting up {guild.id}...")
        message = ""
        if gtype == 2:
            message += (
                f"## welcome! codygen has been successfully added to {guild.name}.\n"
            )
        message += f"{'## ' if gtype != 2 else ''}codygen will now attempt to{' automatically' if gtype == 2 else None} initizalize in your server.\n"
        message += "> please wait, it can take a while.\n"
        message += "## support\n> join our [support server](https://discord.gg/WyxN6gsQRH).\n## issues and bugs\n> report all issues or bugs in the [issues tab](https://github.com/tjf1dev/codygen) of our github repository\n"

        if gtype == 2:
            message += "-# if something goes wrong: try running the </settings init:1340646304073650308> command in your guild.\n"
        message += "-# initializer v3"
        e = Message(
            message=message,
            accent_color=Color.purple,
        )
        yield e
        await asyncio.sleep(2)
        logger.debug("attempting to insert database values")
        db: aiosqlite.Connection = self.bot.db
        try:
            await db.execute("INSERT INTO guilds (guild_id) VALUES (?)", (guild.id,))
            logger.debug("made default guild data")
            config_already_made = False
        except Exception as e:
            logger.warning(
                f"failed when inserting guild data for {guild.id}; {type(e).__name__}: {e}"
            )
            config_already_made = True
        try:
            await db.execute("INSERT INTO modules (guild_id) VALUES (?)", (guild.id,))
            logger.debug("made default module data")
        except Exception as e:
            logger.warning(
                f"failed when inserting module data for {guild.id}; {type(e).__name__}: {e}"
            )
            pass
        await db.commit()
        bot_member = guild.me
        required_permissions = discord.Permissions(
            manage_roles=True,
            manage_channels=True,
            manage_guild=True,
            view_audit_log=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            kick_members=True,
            ban_members=True,
            create_instant_invite=True,
            change_nickname=True,
            manage_nicknames=True,
            send_messages_in_threads=True,
            create_public_threads=True,
            create_private_threads=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            mention_everyone=True,
            use_external_emojis=True,
            add_reactions=True,
        )
        if not bot_member.guild_permissions.is_superset(required_permissions):
            missing_perms = [
                perm
                for perm, value in required_permissions
                if not getattr(bot_member.guild_permissions, perm)
            ]
            permission_error = Message(
                message=f"# initialization failed: missing permissions\n### missing the following permissions: `{', '.join(missing_perms)}`\nplease fix the permissions and try again!",
                accent_color=Color.negative,
            )
            yield permission_error
            logger.debug("yielded permission_error")

        stage2 = Message(
            message=f"# initialization finished!\n> no errors found\npermissions\n> the bot has sufficient permissions to work!\nconfig\n> {'a configuration already exists and has been updated!' if config_already_made else 'a configuration has been created for your guild!'}",
            accent_color=Color.positive,
        )
        yield stage2
        logger.debug(f"...finished setting up {guild.id}")

    @app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(
        name="init",
        description="Check if the bot has valid permissions and create a config.",
    )
    async def init(self, ctx: commands.Context):
        # no_app_force = True
        if not ctx.interaction:
            if not no_app_force:
                await ctx.reply(
                    "## a prefixed command won't work for this.\n### please use the </settings init:1338195438494289964> command instead.",
                    ephemeral=True,
                )
                return

        async def prepare_header_image(path: str):
            with Image.open(path) as img:
                new_size = (round(img.width / 2), round(img.height / 2))
                img = img.resize(new_size)
                byte_io = BytesIO()
                img.save(byte_io, format="PNG")
                byte_io.seek(0)
                return discord.File(byte_io, filename="header.png")

        await ctx.reply(
            view=InitStartLayout(self),
            ephemeral=True,
            file=await prepare_header_image("assets/images/bannername.png"),
        )

    @commands.has_guild_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(prefix="The new prefix to set")
    @settings.command(
        name="prefix", description="view the current prefix and change it."
    )
    async def prefix(self, ctx: commands.Context, prefix: str | None = None):
        if not ctx.guild:
            return
        old = await get_prefix(self.bot, ctx.message)
        con: aiosqlite.Connection = self.bot.db
        cur: aiosqlite.Cursor = await con.cursor()
        e = Message(
            f"# prefix\nthe current prefix in this server is: `{old}`",
            accent_color=Color.white,
        )
        e2 = Message(
            f"# prefix\nprefix updated to: `{prefix}`",
            accent_color=Color.positive,
        )

        if not prefix:
            await ctx.reply(view=e, mention_author=False)
            return

        await cur.execute(
            "UPDATE guilds SET prefix = ? WHERE guild_id = ?", (prefix, ctx.guild.id)
        )
        if cur.rowcount == 0:
            return

        await con.commit()
        await ctx.reply(view=e2)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        owner = guild.owner
        if not owner:
            return
        try:
            gen = self.setup_guild(guild, gtype=2)
            async for view in gen:
                await owner.send(view=view)
        except Exception as e:
            logger.error(f"An error occurred while trying to setup {guild.name}: {e}")


async def setup(bot):
    await bot.add_cog(settings(bot))
