# Reaction Light - Discord Role Bot
[![Reaction Light 2.4.2](https://img.shields.io/badge/Reaction%20Light-2.4.2-yellow.svg)](https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](#)
[![discord.py 1.6.0+](https://img.shields.io/badge/discord.py-1.6.0+-blue.svg)](#)

![Reaction Light Embed Example](https://i.imgur.com/f4b9Qye.png)

Light yet powerful reaction role bot coded in discord.py.

## Key Features
- Create multiple custom embedded messages with custom reactions and roles
- Automatically assign/remove roles to users when they select/deselect a certain reaction
- Optionally limit users to select one reaction (and role) at a time
- Use the same instance of the bot on multiple servers
- Easy installation, setup, and updating
- Optional update notifications and error reporting to your own Discord server
- No need to rely on developer mode and IDs

You can host the bot yourself by configuring the `config.ini` file (manually or via `setup.py`).

## Contents
- [Requirements](#requirements)
- [Setup](#setup)
- [Running the bot](#running-the-bot)
- [Commands](#commands)
  - [Usage Example](#usage-example)
- [Updating](#updating)
  - [Update a git install with a command](#update-a-git-install-with-a-command)
  - [Manually updating a git install](#manually-updating-a-git-install)
  - [Manually updating a zip install](#manually-updating-a-zip-install)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Help](#help)
- [Contribute](#contribute)
- [License](#license)

## Requirements
This bot requires discord.py and Python 3.6+.

You can get discord.py (and other dependencies) via PyPI:
```
python3 -m pip install -U discord.py
```

## Setup
- Clone the repository using `git clone https://github.com/eibex/reaction-light.git` (or download it as a `*.zip` file and extract it - it is recommended to use git instead of the zip archive)
  - `git` comes pre-installed on most Linux-based operating systems. On Windows, if you are not familiar with git, you can use [GitHub Desktop](https://desktop.github.com/)
- Run `setup.py` and follow the instructions or create a `config.ini` file (example provided in `config.ini.sample`) and edit it manually:
  - Insert the token of your bot (found at: https://discord.com/developers/applications/)
    - Make sure you enabled the **server members intent** on your bot developer page
  - Choose a prefix of your liking (default: `rl!`)
  - Set a name to appear in embed footers (default: Reaction Light)
  - URL of the footer logo (default: same as picture above)
  - Hexadecimal value of embeds (default: 0xffff00 (yellow))
- **Optional**: Edit the `activities.csv` file (example provided in `activities.csv.sample`):
  - In each row (line), add the activity the bot will display (`playing <activity>`). The bot will loop through them every 30 seconds.
  - If you want a static activity just add one line.
  - Do not use commas `,`.
- Invite the bot to your server(s) with enough permissions (Manage Roles, Manage Channels, Send Messages, Manage Messages, Add Reactions)
  - You can use this link (need to replace **CLIENT_ID** with your bot's ID, visible under the general information tab): 
  - `https://discord.com/oauth2/authorize?&client_id=CLIENT_ID&scope=bot&permissions=8`
- On your Discord server, go to: `Server Settings > Roles` and move `Reaction Light` in a position that is above all roles that it needs to add/remove. The bot only has permission to manage the roles below its own role.
- Run `rl!admin @Role` to give users with that role permission to create reaction-role messages (even administrators need it). You need to be a server administrator to use this command.

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
All commands require an admin role which you can set by using `rl!admin` (requires administrator permissions on the server). The bot will reply with missing permissions otherwise. Executing a command without any argument will prompt the bot to provide you with instructions on how to use the command effectively. In the following list the default prefix `rl!` is used, but it can be freely changed in the `config.ini` file.

- `rl!help` shows this set of commands along with a link to the repository.
- `rl!new` starts the creation process for a new reaction role message. Check [below](#example) for an example.
- `rl!edit` edits the text and embed of an existing reaction role message.
- `rl!reaction` adds or removes a reaction from an existing reaction role message.
- `rl!notify` toggles sending messages to users when they get/lose a role (default off) for the current server (the command affects only the server it was used in).
- `rl!colour` changes the colour of the embeds of new and newly edited reaction role messages.
- `rl!activity` adds an activity for the bot to loop through and show as status.
- `rl!rm-activity` removes an activity from the bot's list.
- `rl!activitylist` lists the current activities used by the bot as statuses.
- `rl!admin` adds the mentioned role or role id to the admin list, allowing members with a certain role to use the bot commands. Requires administrator permissions on the server.
- `rl!rm-admin` removes the mentioned role or role id from the admin list, preventing members with a certain role from using the bot commands. Requires administrator permissions on the server.
- `rl!adminlist` lists the current admins on the server the command was run in by mentioning them and the current admins from other servers by printing out the role IDs. Requires administrator permissions on the server.
- `rl!kill` shuts down the bot.
- `rl!systemchannel` updates the main or server system channel where the bot sends errors and update notifications.
- `rl!restart` restarts the bot.
- `rl!update` updates the bot and restarts it. Only works on `git clone` installations. Check the [setup](#setup) section to learn how to install with git.
- `rl!version` reports the bot's current version and the latest available one from GitHub.

### Usage Example
In this example the prefix used is `rl!`. Once you initiate the process, be sure only to answer to the bots questions or the bot might record unwanted messages as instructions. You can still send messages to other channels, and others can send messages to the channel you initiated the process in.

Initiate the message creation process with `rl!new`.
```
User: rl!new
```

Next, you will be asked to attach emojis to roles. Only use standard emojis or those that are hosted on servers the bot has access to. Send a single message for each single combination and then type `done` when you have finished attaching emojis to their respective roles. Ensure that the roles are mentionable when you are doing this step. You can disable mentions after finishing this step.
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

Next, you will be asked if you want to allow users to select multiple reactions (and role) at a time or not. Then, you will be asked to either create a new message or use an existing one. Using an existing message will prevent you from using `rl!edit` if the target message wasn't created by the bot. If you choose to use an already existing message simply react to it with 🔧, the bot will remove the 🔧 reaction and add the ones you chose.

Otherwise, you will have to customise the message that the bot is going to send with the roles attached to it. Enter a title and the content of your message by separating them with ` // ` (the space before and after `//` is important).
```
Bot: What would you like the message to say? Formatting is: `Message // Embed_title // Embed_content`. `Embed_title` and `Embed_content` are optional. You can type `none` in any of the argument fields above (e.g. `Embed_title`) to make the bot ignore it.
User: none // Select your roles // Click on the buttons below to give yourself some roles!
```

Finally, the bot will send the message to the channel specified in the first step, and it will react with each reactions specified so that the buttons are ready to be used. The bot will remove any new reactions to the message to avoid clutter. For example, if you added an `:eggplant:` reaction to the message created in this example, the bot will remove it as it is not attached to any role.

## Updating
You can view new features in the [changelog](https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md).

If you set a system channel in `config.ini`, your bot will check for new versions from this repository. If updates are available a message is sent briefly outlining the update process. This process varies depending on how you installed the bot.

### Update a git install with a command
Type `rl!update` to update the bot and restart it.

### Manually updating a git install
- Navigate to the reaction-light directory
- Run `git pull origin master`
- Shutdown the bot by using the `rl!kill` command
- Start the bot again

### Manually updating a zip install
This is not the recommended way to manage the bot files, consider moving to git. You can copy your `files` folder and the `config.ini` file to maintain the bot functionality with older reaction-role messages. 

If you downloaded the bot as a zip archive:

- Download the new zip
- Extract it into the current reaction-light folder and replace old files with new ones if prompted to
- Shutdown the bot by using the `rl!kill` command
- Start the bot again

## Roadmap
Upcoming features can be found in the open issues and PRs tagged with **new feature**. They can be found [here](https://github.com/eibex/reaction-light/issues?q=is%3Aopen+label%3A%22new+feature%22).

Open a new issue if you would like to see a feature implemented, and/or open a pull request implementing it.

## FAQ
**When I click one of the reactions the bot does not give me a role!**

Ensure that you moved the `Reaction Light` role to a position that is hierarchically higher than the role you are trying to assign.

**The bot says I am not an admin, even though I own the server (or have admin rights for it)**

Run `rl!admin @Role` to give all users with that role permission to manage Reaction Light. This is done to have server staff use the bot without giving them unnecessary server rights. The only server admin (not bot admin) commands are `rl!admin` and `rl!rm-admin`.

## Help
If you need help with the bot or need to report bugs, post an issue [here](https://github.com/eibex/reaction-light/issues).

## Contribute
If you would like to contribute to this project, fork it and then create a pull request. Please ensure that you have thoroughly tested all your changes. Black formatting is preferred. 

## License
[MIT](https://github.com/eibex/reaction-light/blob/master/LICENSE)
