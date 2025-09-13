import discord
from discord.ui import LayoutView, TextDisplay, Container, Separator, Section


class UserInfoSection(Section):
    def __init__(self, user: discord.Member | discord.User):
        super().__init__(accessory=discord.ui.Thumbnail(media=user.display_avatar.url))
        if user.display_avatar:
            avatar = f"[`avatar`]({user.display_avatar.url})"
        else:
            avatar = ""
        if user.banner:
            banner = f"[`banner`](<{user.banner.url}>)"
        else:
            banner = ""
        self.add_item(
            TextDisplay(
                f"[`profile`](<https://discord.com/users/{user.id}>) • {avatar}{' • ' if user.banner else ''}{banner}\n"
                f"{f'server display name: `{user.display_name}`\n' if user.global_name != user.display_name else ''}"
                f"display name: `{user.global_name}`\n"
                f"username: `{user.name}`\n"
                f"id: `{user.id}`\n"
                f"{f'roles: `{len(user.roles)}`\n' if isinstance(user, discord.Member) else ''}"
                f"{f'joined: <t:{round(user.joined_at.timestamp())}:R> (<t:{round(user.joined_at.timestamp())}:D>)\n' if isinstance(user, discord.Member) and user.joined_at else ''}"
                f"created: <t:{round(user.created_at.timestamp())}:R> (<t:{round(user.created_at.timestamp())}:D>)\n"
            )
        )


class UserInfoLayout(LayoutView):
    def __init__(self, user: discord.Member | discord.User):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay(f"# {user.mention}"))
        container.add_item(Separator())
        container.add_item(UserInfoSection(user))
