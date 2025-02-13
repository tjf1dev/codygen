from main import *
import json

class InitHomeView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, custom_id="init_button")
    async def init_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if the user has Administrator permissions
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="access denied",
                description="### you must have admin to run this, silly!",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return
        stage1 = discord.Embed(
            title="initialization in progress... hang on!",
            description="this message will update once its done :3",
            color=0xff0000
        )
        await interaction.response.send_message(embed=stage1, ephemeral=True)
        
        # check perms
        guild = interaction.guild
        bot_member = guild.me

        required_permissions = discord.Permissions(
            manage_roles=True,
            manage_channels=True,
            manage_guild=True,
            view_audit_log=True,
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            mention_everyone=True,
            use_external_emojis=True,
            add_reactions=True
        )

        if not bot_member.guild_permissions >= required_permissions:
            missing_perms = [perm for perm, value in required_permissions if not getattr(bot_member.guild_permissions, perm)]
            error_embed = discord.Embed(
                title="init failed: missing permissions",
                description=f"### missing the following permissions: `{', '.join(missing_perms)}`\nplease fix the permissions, and try again!",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        guild_config_path = f'data/guilds/{guild.id}.json'
        if os.path.exists(guild_config_path):
            configAlreadyMade = True
        else:
            with open('config.json', 'r') as f:
                template_config = json.load(f)['template']['guild']
                os.makedirs(os.path.dirname(guild_config_path), exist_ok=True)
                with open(guild_config_path, 'w') as f:
                    json.dump(template_config, f, indent=4)
                    configAlreadyMade = False

        stage2 = discord.Embed(
            title="initialization finished!",
            description="no errors found",
            color=0x00ff00
        )
        if not configAlreadyMade:
            stage2.add_field(
                name="tests passed",
                value="permissions\n> the bot has sufficient permissions to work!\nconfig\n> a [configuration file](https://github.com/tjf1dev/codygen/wiki/Config) has been created for your guild!"
            )
        else:
            stage2.add_field(
                name="tests passed",
                value="permissions\n> the bot has sufficient permissions to work!\nconfig\n> a configuration file already exists for your guild!"
            )
        await interaction.followup.send(embed=stage2, ephemeral=True)
class settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description="settings commands to manage your bot instance."

    @commands.hybrid_group(name="settings", description="settings commands to manage your bot instance.")
    async def settings(self,ctx):
        pass

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="config",description="change the configs for your guild. usage: settings config <key> <value>")
    async def config(self,ctx, key, value):
        set_value_from_guild_config(ctx.guild.id, key, value)
        e = discord.Embed(
            title="config changed successfully",
            color=0x00ff00
        ).add_field(
            name=f"{key}",
            value=f"```{value}```"
        )
        await ctx.reply(embed=e)

    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="viewconfig",description="view the configs for your guild.")
    async def viewconfig(self,ctx):
        e = discord.Embed(
            title=f"config for {ctx.guild.name}",
            color=0x00ff00
        )
        for key in get_guild_config(ctx.guild.id):
            e.add_field(
                name=f"{key}",
                value=f"```json\n{get_value_from_guild_config(ctx.guild.id, key)}```",inline=False
            )
        await ctx.reply(embed=e,ephemeral=True)
    @commands.has_guild_permissions(administrator=True)
    @settings.command(name="init", description="check if the bot has valid permissions and create a config.")
    async def init(self, ctx):
        if not ctx.interaction:
            await ctx.reply("## a prefixed command won't work for this.\n### please use the </settings init:1338195438494289964> command instead.", ephemeral=True)
            return
        e = discord.Embed(
            title=f"codygen - initialization",
            description=f"## hi! welcome to codygen :3\npress the button below to start the initialization :3"
        )
        await ctx.reply(embed=e, ephemeral=True, view=InitHomeView())
        

async def setup(bot):
    await bot.add_cog(settings(bot))