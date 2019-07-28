# discord-bot

###Set up: <br />
follow the virtualenv instructions:
https://discordpy.readthedocs.io/en/rewrite/intro.html
For youtube client install <br />
pip install --upgrade google-api-python-client

The discord token is stored in config.py create this file and then add config='token_here'

####Config File:
A file named config.py needs to be place in the bot directory this provides all the
 necessary API keys and install locations
 
| Value                | Description                                       |
|----------------------|---------------------------------------------------|
| token                | Discord API login token                           |
| google_key           | Google API key to access the Youtube API          |
| REDDIT_CLIENT_SECRET | The Client secret for the Reddit API              |
| REDDIT_CLIENT_ID     | The Client ID for the Reddit API                  |
| FFMPEG_PATH          | The FFMPEG install path (usually /usr/bin/ffmpeg) |

### Commands
* Join (-join -summon)
    * Joins the voice channel
* Leave (-leave)
    * Leaves the voice channel
