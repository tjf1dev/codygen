from discord.ui import LayoutView, TextDisplay, Container, Separator


class LevelRefreshSummaryLayout(LayoutView):
    def __init__(self, added_roles: dict, removed_roles: dict):
        super().__init__()
        container = Container()
        self.add_item(container)
        container.add_item(TextDisplay("# levels refreshed."))
        container.add_item(Separator())
        added_text = ""
        for user in added_roles.keys():
            for role in added_roles[user]:
                added_text += f"<@{user}>: + <@&{role}>\n"
        removed_text = ""
        for user in removed_roles.keys():
            for role in removed_roles[user]:
                removed_text += f"<@{user}>: - <@&{role}>\n"
        if not added_roles:
            added_text = ""
        if not removed_roles:
            removed_text = ""
        if not added_roles and not removed_roles:
            container.add_item(TextDisplay("## no changes have been made."))
        else:
            (
                container.add_item(TextDisplay("## added roles\n" + added_text))
                if added_roles
                else None
            )
            container.add_item(Separator())
            (
                container.add_item(TextDisplay("## removed roles\n" + removed_text))
                if removed_roles
                else None
            )
