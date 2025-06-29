import datetime


def iso_to_unix(iso_str: str) -> int:
    """
    Convert an ISO 8601 UTC timestamp string to a Unix timestamp.

    Args:
        iso_str (str): ISO timestamp, e.g. '2025-06-28T16:50:11Z'

    Returns:
        int: Unix timestamp (e.g. 1751129411)
    """
    if iso_str.endswith("Z"):
        iso_str = iso_str.replace("Z", "+00:00")

    dt = datetime.fromisoformat(iso_str)
    return int(dt.timestamp())


def _old_xp_to_level(xp):
    level = 1
    xp_needed = 100
    increment = 50

    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed += increment

    return level


def adjusted_xp_cost(level: int, base_xp: float = 50, exponent: float = 1.24) -> float:
    return base_xp * (level**exponent)


def level_to_xp(level: int, base_xp: float = 50, exponent: float = 1.24) -> float:
    total_xp = 0
    for lvl in range(1, level + 1):
        total_xp += adjusted_xp_cost(lvl, base_xp, exponent)
    return total_xp


def xp_to_level(xp: float, base_xp: float = 50, exponent: float = 1.24) -> int:
    level = 1
    while True:
        cost = adjusted_xp_cost(level, base_xp, exponent)
        if xp < cost:
            break
        xp -= cost
        level += 1
    return level
