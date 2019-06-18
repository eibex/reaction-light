# Reaction Light - Discord Role Bot
![Reaction Light Embed Example](https://i.imgur.com/f4b9Qye.png)

Light yet powerful reaction role bot coded in discord.py (rewrite branch).
You can host the bost yourself by configurin the `config.ini` file or add the one hosted by myself.
You can request to use the bot hosted by myself by sending an email to: reactionlight@outlook.com

## Requirements
Discord.py requires Python 3.5.3 or higher.
You can get discord.py via PyPI:
```
python3 -m pip install -U discord.py
```
On Windows:
```
py -3 -m pip install -U discord.py
```
## Setup
- Edit the `config.ini` file:
- Insert the token of your bot (found at: https://discordapp.com/developers/applications/)
- Choose a prefix of your liking (default is `rl!`)
- Name is redundant in current version
- Choose a footer logo
- Set the admin(s) by pasting their role IDs. In case you only have/need one admin role, fill the roles you do not need with `0`
- Invite the bot to your server(s) with enough permissions (I use Manage Roles, Manage Channels, Send Messages, Manage Messages, Add Reactions)
- On your Discord server, go to: Server Settings > Roles and move `Reaction Light` in a position that is above all roles that it needs to add/remove. The bot only has permission to manage the roles below its own role.

## Running the bot
You can run the bot by using
```
python3 bot.py
```
Or
```
nohup python3 bot.py &
```
## Commands
Use `rl!help` to get started and follow the instructions. If the bot replies with an admin error, make sure you set the role id correctly in `config.ini`.

## License
- [GNU GPL v3.0](https://github.com/Alessandro-S19/reaction-light/blob/master/LICENSE)
