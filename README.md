# Reaction Light - Discord Role Bot
![Python 3.5.3+](https://img.shields.io/badge/python-3.5.3+-blue.svg)
![discord.py rewrite](https://img.shields.io/badge/discord.py-rewrite-blue.svg)

![Reaction Light Embed Example](https://i.imgur.com/f4b9Qye.png)

Light yet powerful reaction role bot coded in discord.py (rewrite branch).
You can host the bot yourself by configuring the `config.ini` file or add the one hosted by myself.

You can request to use the bot hosted by myself by sending an email to hello@eibe.dev and explaining why you need the bot (and why you cannot host it yourself) along with how many server(s) and users the bot will need to serve more or less. I will reply within a few hours.

## Contents
- [Requirements](https://github.com/eibex/reaction-light#requirements)
- [Setup](https://github.com/eibex/reaction-light#setup)
- [Running the Bot](https://github.com/eibex/reaction-light#running-the-bot)
- [Commands](https://github.com/eibex/reaction-light#commands)
  - [Example](https://github.com/eibex/reaction-light#example)
- [Troubleshooting](https://github.com/eibex/reaction-light#troubleshooting)
- [Contribute](https://github.com/eibex/reaction-light#contribute)
  - [TO-DO List](https://github.com/eibex/reaction-light#to-do-list)
- [License](https://github.com/eibex/reaction-light#license)

## Requirements
Discord.py requires Python 3.5.3 or higher. This bot requires discord.py 1.2.5 or greater.
You can get discord.py via PyPI:
```
python3 -m pip install -U discord.py
```
## Setup
- Clone the repository using `git clone https://github.com/eibex/reaction-light.git` (or download it as a `*.zip` file)
- Run `setup.py` and follow the instructions or edit the `config.ini` file manually:
  - Insert the token of your bot (found at: https://discordapp.com/developers/applications/)
  - Choose a prefix of your liking (default is `rl!`)
  - Name is not currently used and can be left blank
  - URL of the footer logo
  - Set the admin role(s) by pasting their role IDs. In case you only have/need one admin role, fill the roles you do not need with `0`
- Edit the `activities.csv` file:
  - In each row (line), add the activity the bot will display (`playing <activity>`). The bot will loop through them every 30 seconds.
  - If you want a static activity just add one line.
  - Do not use commas `,`.
- Invite the bot to your server(s) with enough permissions (Manage Roles, Manage Channels, Send Messages, Manage Messages, Add Reactions)
- On your Discord server, go to: `Server Settings > Roles` and move `Reaction Light` in a position that is above all roles that it needs to add/remove. The bot only has permission to manage the roles below its own role.

## Running the bot
You can run the bot by using:
```
python3 bot.py
```
If you want to run it as a background task:
```
nohup python3 bot.py &
```
## Commands
Use `rl!help` to get started and follow the instructions. If the bot replies with an admin error, make sure you set the role id correctly in `config.ini`.

### Example
In this example the prefix used is `rl!`. Once you initiate the process, be sure only to answer to the bots questions or the bot might record unwanted messages as instructions. You can still send messages to other channels, and others can send messages to the channel you initiated the process in.

Initiate the message creation process with `rl!new`.
```
User: rl!new
```
Next, you will be asked to provide the ID of the channel you want to send the message in. You can find the ID by right clicking the channel and clicking on `Copy ID`. If you do not see a `Copy ID` option, go to `Discord Settings > Appearance` and, at the bottom of the page, turn `Developer Mode` ON.
```
Bot: Please paste the channel ID where to send the auto-role message.
User: 595907369242722304
```
Next, you will be asked to attach emojis to roles. Only use standard emojis or those that are hosted on your server (i.e. the Bot is not a Nitro user and cannot use emojis from other servers). Send a single message for each single combination and then type `done` when you have finished attaching emojis to their respective roles. Ensure that the roles are mentionable when you are doing this step. You can disable mentions after finishing this step.
```
Bot: Attach roles and emojis separated by a space (one combination per message).
When you are done type `done`. Example:
:smile: `@Role`
User: :rage: @AngryRole
User: :sob: @SadRole
User: :cry: @EvenSadderRole
User: :joy: @HappyRole
User: done
```
Next, you will be asked to customise the message that the bot is going to send with the roles attached to it. Enter a title and the content of your message by separating them with ` // ` (the space before and after `//` is important).
```
Bot: What would you like the message to say? Formatting is: `Title // Message_content`
User: Select your roles // Click on the buttons below to give yourself some roles!
```
Finally, the bot will send the message to the channel specified in the first step, and it will react with each reactions specified so that the buttons are ready to be used. The bot will remove any new reactions to the message to avoid clutter. For example, if you added an `:eggplant:` reaction to the message created in this example, the bot will remove it as it is not attached to any role.

#### Editing
To edit an old embed and preserve the emoji-role links, you can use the `edit` command. You will need the channel and message id where the embed is located. You can find these IDs by right clicking the respective channel and messages (with developer mode on in your Discord settings). For example:
```
rl!edit CHANNEL_ID // MESSAGE_ID // New Title // New Description
```

## Troubleshooting
**When I click one of the reactions the bot does not give me a role!**
Ensure that you moved the `Reaction Light` role to a position that is hierarchically higher than the role you are trying to assign.

Post bugs and issues [here](https://github.com/eibex/reaction-light/issues).

## Contribute
If you would like to contribute to this project, fork it and then create a pull request. Please ensure that you have thoroughly tested all your changes. PEP-8 styled code is not enforced but most welcome (human readability is required though).

### TO-DO List
- [x] Listen only to process initiator in the channel the command was used
- [x] Allow editing of previous embeds
- [ ] Use messages created by other users to manage roles and reactions
- [ ] Message setup abort feature
  - [ ] Delete entries to `*.csv` files when aborting
- [ ] Delete entries to `*.csv` files when deleting a reaction role message
- [ ] Your suggestions (open an issue [here](https://github.com/eibex/reaction-light/issues))

## License
[MIT](https://github.com/eibex/reaction-light/blob/master/LICENSE)
