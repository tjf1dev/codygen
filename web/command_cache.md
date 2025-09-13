# Command caching

to make command data accessible by other programs,
codygen uses a **command cache**.  
it's a JSON file containing all command data

command cache files are made (by default)

- every day
- every time the command tree is synced

the files are accessible at `cache/commands.json` and `web/cache/commands.json`

> [!TIP]
> metadata about the last cache is stored in `.last_command_cache`

> [!TIP]
> check out the cache in action! the [commands page](/commands) depends on it
