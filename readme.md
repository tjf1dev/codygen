# codygen

> [!TIP]
> Learn more about the bot in our [documentation](https://github.com/tjf1dev/codygen/wiki)

> [!TIP]
> [Invite codygen to your server](https://discord.com/oauth2/authorize?client_id=1337509693874245682&permissions=8&integration_type=0&scope=bot)

## about the app
> codygen is a small multipurpose Discord bot

> created and maintained by [tjf1dev](https://github.com/tjf1dev)

> in python ([discord.py](https://github.com/rapptz/discord.py)) <3
## support
support me! if you want to, become [tjf1dev's sponsor!](https://github.com/sponsors/tjf1dev)... or just press the sponsor button above :3
## contributions
> feel free to contribute to the bot
![contributors](https://readme-contribs.as93.net/contributors/tjf1dev/codygen)

# self-hosting
please make sure you have [Python](https://python.org) and [Git](https://git-scm.com) installed and in.
you may still run into some config issues, [report them](https://github.com/tjf1dev/codygen/issues)!!
1. clone this repo
```sh
git clone https://github.com/tjf1dev/codygen
```
2. install dependencies from requirements.txt:
```bash
pip install -r requirements.txt 
# --break-system-packages may be required to install dependencies
```
3. make a Discord app in the [Discord Developer Portal](https://discord.com/developers/applications)
> [!WARNING]
> make sure to enable all intents and user install, otherwise you may run into some issues
4. (optional, for last.fm integration) obtain an [API key](https://www.last.fm/api/authentication) from last.fm. you're also gonna need a callback url

after obtaining the API key and it's coresponding secret, go to the next step.

5. rename `.env.template` to `.env` and fill out it's values. do the same with `config.json`
> [!WARNING]
> if you skip step 5, the bot won't be able to start and/or have problems.
6. run `main.py`!
