import discord
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section


class ServerInfoSection(Section):
    def __init__(self, guild: discord.Guild, roles: int):
        super().__init__(
            accessory=discord.ui.Thumbnail(
                media=(
                    guild.icon.url
                    if guild.icon
                    else f"https://placehold.co/512x512?text={guild.name}&font=Montserrat"
                )
            )
        )

        text = f"## server\nid: `{guild.id}`\n"

        if guild.owner:
            text += f"owner: {guild.owner.mention}\n"

        text += f"roles: `{roles}`\n"

        if guild.icon:
            text += f"[`icon url`](<{guild.icon.url}>)\n"

        text += f"created: <t:{round(guild.created_at.timestamp())}:R> (<t:{round(guild.created_at.timestamp())}:D>)\n"

        self.add_item(TextDisplay(text))


class ServerInfoLayout(LayoutView):
    def __init__(
        self,
        guild: discord.Guild,
        roles: int,
        channels: int,
        text_channels: int,
        voice_channels: int,
        other_channels: int,
        members: int,
        bots: int,
        users: int,
    ):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay(f"# {guild.name}"))
        container.add_item(Separator())
        container.add_item(ServerInfoSection(guild, roles))
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "## channels\n"
                f"total: `{channels}`\n"
                f"text: `{text_channels}`\n"
                f"voice: `{voice_channels}`\n"
                f"other: `{other_channels}`\n\n"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                f"## members\ntotal: `{members}`\nbots: `{bots}`\nusers: `{users}`",
            )
        )
        # e = discord.Embed(
        #     description=f"# {guild.name}\n"
        #     f"id: {guild.id}\n"
        #     f"owner: {guild.owner.mention}\n"
        #     f"roles: {len(roles)}\n"
        #     f"created: <t:{round(guild.created_at.timestamp())}:R> (<t:{round(guild.created_at.timestamp())}:D>)\n"
        #     f"[icon url](<{guild.icon.url}>)\n"
        #     f"## channels\n"
        #     f"total: {len(channels)}\n"
        #     f"text: {len(text_channels)}\n"
        #     f"voice: {len(voice_channels)}\n"
        #     f"other: {len(other_channels)}\n\n"
        #     f"## members\n"
        #     f"total: {len(members)}\n"
        #     f"bots: {len(bots)}\n"
        #     f"users: {len(users)}",
        #     color=discord.Color.from_rgb(
        #         *await avg_color(guild.icon.url) if guild.icon else (0, 0, 0)
        #     ),
        # )
