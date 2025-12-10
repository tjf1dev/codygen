"""
this is the config made when first starting codygen
"""

DEFAULT_MODULE_STATE = True
DEFAULT_CONFIG = {
    "default_prefix": ">",
    "db_snapshot_interval_days": 7,
    "github": "tjf1dev/codygen",  # github repo in format of AUTHOR/REPO
    "admins": [],  # list of user ids
    "cogs": {"blacklist": []},
    "commands": {"cat": {"url": "https://api.thecatapi.com/v1/images/search"}},
}
