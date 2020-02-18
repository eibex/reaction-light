# Reaction Light - Discord Role Bot
![Reaction Light 0.1.1](https://img.shields.io/badge/Reaction%20Light-0.1.1-yellow.svg)
![Python 3.5.3+](https://img.shields.io/badge/python-3.5.3+-blue.svg)
![discord.py rewrite](https://img.shields.io/badge/discord.py-1.2.5+-blue.svg)

![Reaction Light Embed Example](https://i.imgur.com/f4b9Qye.png)

Light yet powerful reaction role bot coded in discord.py (rewrite branch).

## Features
- Create multiple custom embedded messages with custom reactions and roles
- Automatically assign/remove roles to users when they select/deselect a certain reaction
- Use the same instance of the bot on multiple servers
- Easy installation, setup, and updating
- Optional update notifications and error reporting to your own Discord server
- No need to rely on developer mode and IDs

You can host the bot yourself by configuring the `config.ini` file.

## Contents
- [Reaction Light - Discord Role Bot](#reaction-light---discord-role-bot)
  - [Features](#features)
  - [Contents](#contents)
  - [Requirements](#requirements)
  - [Setup](#setup)
  - [Running the bot](#running-the-bot)
  - [Commands](#commands)
    - [Usage Example](#usage-example)
  - [Updating](#updating)
    - [Updating a git install](#updating-a-git-install)
    - [Updating a zip install](#updating-a-zip-install)
  - [FAQ](#faq)
  - [Help](#help)
  - [Contribute](#contribute)
  - [License](#license)

## Requirements
Discord.py requires Python 3.5.3 or higher. This bot requires discord.py 1.2.5 or greater as well as other dependencies.

You can get discord.py (and other dependencies) via PyPI:
```
python3 -m pip install -U discord.py requests 
```
or
```
pip install -U discord.py requests 
```

## Setup
- Clone the repository using `git clone https://github.com/eibex/reaction-light.git` (or download it as a `*.zip` file and extract it - it is recommended to use git instead of the zip archive)
- Run `setup.py` and follow the instructions or edit the `config.ini.sample` file manually (rename it to `config.ini` when done):
  - Insert the token of your bot (found at: https://discordapp.com/developers/applications/)
  - Choose a prefix of your liking (default is `rl!`)
  - Name is not currently used and can be left blank
  - URL of the footer logo
  - Set the admin role(s) by pasting their role IDs. In case you only have/need one admin role, fill the roles you do not need with `0`
- Edit the `activities.csv.sample` file (it will be automatically copied to `activities.csv` when the bot is launched):
  - In each row (line), add the activity the bot will display (`playing <activity>`). The bot will loop through them every 30 seconds.
  - If you want a static activity just add one line.
  - Do not use commas `,`.
- Invite the bot to your server(s) with enough permissions (Manage Roles, Manage Channels, Send Messages, Manage Messages, Add Reactions)
  - You can use this link (need to replace **CLIENT_ID** with your bot's ID, visibile under the general information tab): 
  - `https://discordapp.com/oauth2/authorize?&client_id=CLIENT_ID&scope=bot&permissions=268445776`
- On your Discord server, go to: `Server Settings > Roles` and move `Reaction Light` in a position that is above all roles that it needs to add/remove. The bot only has permission to manage the roles below its own role.

If you need help to setup the bot you can join [this Discord server](https://discord.gg/ZGTPh5b) to ask questions. Do not report bugs there, file an issue on GitHub instead.

## Running the bot
The bot can be run by using:
```
python3 bot.py
```

To run it as a background task (recommended unless debugging):
```
nohup python3 bot.py &
```

## Commands
All commands require an admin role set in `config.ini`. The bot will reply with missing permissions otherwise. In the following list the default prefix `rl!` is used, but it can be freely changed in the `config.ini` file.

- `rl!help` shows a set of commands to get started and provides a link to this README's setup walkthrough.
- `rl!new` starts the creation process for a new reaction role message. Check [below](#example) for an example.
- `rl!edit` edits an existing reaction role message or provides instructions on how to do so if no arguments are passed.
- `rl!kill` shuts down the bot. You will need to start it again manually (for now).
- `rl!systemchannel` updates the system channel where the bot sends errors and update notifications.

### Usage Example
In this example the prefix used is `rl!`. Once you initiate the process, be sure only to answer to the bots questions or the bot might record unwanted messages as instructions. You can still send messages to other channels, and others can send messages to the channel you initiated the process in.

Initiate the message creation process with `rl!new`.
```
User: rl!new
```

Next, you will be asked to mention the channel you want to send the message in.
```
Bot: Please mention the #channel where to send the auto-role message.
User: #get-roles
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

## Updating
You can view new features in the [changelog](https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md).

If you set a system channel in `config.ini`, your bot will check for new versions from this repository. If updates are available a message is sent briefly outlining the update process. This process varies depending on how you installed the bot.

### Updating a git install
If you downloaded the bot with git, updating is trivial:

- Navigate to the reaction-light directory
- Run `git pull origin master`
- Shutdown the bot by using the `rl!kill` command
- Start the bot again

### Updating a zip install
This is not the recommended way to manage the bot files, consider moving to git. You can copy your `files` folder and the `config.ini` file to maintain the bot functionality with older reaction-role messages. 

If you downloaded the bot as a zip archive:

- Download the new zip
- Extract it into the current reaction-light folder and replace old files with new ones if prompted to
- Shutdown the bot by using the `rl!kill` command
- Start the bot again


## FAQ
**When I click one of the reactions the bot does not give me a role!**

Ensure that you moved the `Reaction Light` role to a position that is hierarchically higher than the role you are trying to assign.

## Help
If you need help with the bot or need to report bugs, post an issue [here](https://github.com/eibex/reaction-light/issues).

## Contribute
If you would like to contribute to this project, fork it and then create a pull request. Please ensure that you have thoroughly tested all your changes. Black formatting is preferred. 

## License
[MIT](https://github.com/eibex/reaction-light/blob/master/LICENSE)
