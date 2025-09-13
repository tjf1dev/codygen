from discord.ui import LayoutView, TextDisplay, Container, Separator
import time
from ext.utils import timestamp


class LevelBoostsLayout(LayoutView):
    def __init__(self, boosts: dict):
        super().__init__()
        empty_temp = {"percentage": 0, "expires": 0}
        container = Container()
        self.add_item(container)
        _global = boosts["global"]
        _role = boosts["role"]
        _user = boosts["user"]
        multiplier = boosts["multiplier"]
        if not multiplier:
            container.add_item(TextDisplay("> you don't have any boosts."))
            return
        inactive = 0
        container.add_item(TextDisplay("## active boosts"))
        container.add_item(Separator())
        content = ""

        if (
            _global is empty_temp
            or _global["percentage"] == 0
            or _global["expires"] < time.time()
            and _global["expires"] != -1
        ):
            inactive += 1
        else:
            container.add_item(
                TextDisplay(
                    f"> global: **{_global['percentage']}%**\n> expires: **{timestamp(_global['expires'])}**"
                )
            )
        if (
            _user is empty_temp
            or _user["percentage"] == 0
            or _user["expires"] < time.time()
            and _user["expires"] != -1
        ):
            inactive += 1
        else:
            container.add_item(
                TextDisplay(
                    f"> user: **{_user['percentage']}%**\n> expires: **{timestamp(_user['expires'])}**"
                )
            )
        if not _role:
            inactive += 1
        else:
            r_inactive = 0
            # > role: **{_global["percentage"]}%**\n> expires: **{timestamp(_global["expires"])}**
            for role_id in _role.keys():
                role = _role[role_id]
                if (
                    role["percentage"] == 0
                    or role["expires"] < time.time()
                    and role["expires"] != -1
                ):
                    r_inactive += 1
                    continue
                content += f"> role: <@&{role_id}>: **{role['percentage']}%**\n> expires: **{timestamp(role['expires'])}**\n"
            if r_inactive == 0:
                inactive += 1
        if inactive == 4:
            container.add_item(TextDisplay("no boosts active."))
        else:
            if content:
                container.add_item(TextDisplay(f"{content}"))
            container.add_item(Separator())
            container.add_item(TextDisplay(f"### total: {multiplier}%"))
        # container.add_item(TextDisplay(f"```json\n_{boosts}```"))
