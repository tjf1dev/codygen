# codygen

> [!TIP]
> Learn more about the bot in our [documentation](https://github.com/tjf1dev/codygen/wiki)

> [!TIP]
> [Invite codygen to your server](https://discord.com/oauth2/authorize?client_id=1337509693874245682)

## about the app
> codygen is a small multipurpose Discord bot made by [tjf1dev](https://github.com/tjf1dev)
> made in discord.py <3

## contributions
> feel free to contribute to the bot
![contributors](https://readme-contribs.as93.net/contributors/tjf1dev/codygen)

# self-hosting
1. Install dependencies seen in requirements.txt:
```bash
pip install -r requirements.txt (--break-system-packages) 
# --break-system-packages may be required to install dependencies
```
2. Make a Discord bot in the [Discord Developer Portal](https://discord.com/developers/applications):
It's steps are:
- Click on "New application" in the home page then set your application name and agree to the terms
- Go to Bot --> Reset Token then copy the token
- Make a invite for the bot (OAuth2 --> OAuth2 URL Generator)
Select the following after clicking `bot`:
- Administrator in GENERAL PERMISSIONS
You will see your invite link to the bot in GENERATED URL in this section, copy it and invite the bot.

(optional, to enable user installs and seamless guild installs) Enable also user installs by going to:
- Installation --> Installation Contexts (check both User and Guild Install)
- Also select in Install Link from the dropdown Discord provided link for installation and save your changes.
- For guild installs also go to Default Install Settings --> Guild Install then add the `bot` scope and then Administrator permissions and save your changes again.

3. (optional, for last.fm integration) Obtain a API key from last.fm

See the instructions [here](https://www.last.fm/api/authentication) to get a API key

After obtaining the API key and it's coresponding secret, go to the next step.

4. Make a .env file with the contents:
```
BOT_TOKEN=<bot_token> # insert here your token obtained for the bot
# below fields are only needed for last.fm integration
LASTFM_API_KEY=<lastfm_api_key> # paste the api key here for last.fm if you have it
LASTFM_SECRET=<lasfm_secret> # paste the secret here for last.fm if you have it
```
5. Make a config.json file that looks like this:

Below here is a minimal configuration needed to use the bot, configure it as you desire
```json
{
  "version": "0.18-alpha",

  "commands": {
    "awawawa": {
      "words": ["awawawa", "awa", "wawa"]
    }
  },

  "cogs": {
    "blacklist": []
  },

  "support": {
    "channel": 123456789012345678 /* replace this with the desired channel ID */
  },

  "template": {
    "guild": {
      "prefix": {
        "prefix": ">",
        "prefix_enabled": true
      },
      "settings": {
        "prefix": {"prefix_enabled": true}
        /* add any other guild‐defaults your commands expect */
      }
    }
  },

  "guilds": {
    /* once your bot joins a server,
       it will write out data/guilds/<guild_id>.json for you */
  }
}
```
Remove any comments that have the `/* example comment /` suffix on them, otherwaise you will see JSON errors during launching.
