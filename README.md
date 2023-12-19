# Reaction Light - Discord Role Bot
[![Reaction Light 3.4.3](https://img.shields.io/badge/Release-3.4.3-yellow.svg?logo=github&logoColor=ffffff&style=for-the-badge)](https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md)
[![Build Status](https://img.shields.io/github/actions/workflow/status/eibex/reaction-light/test.yml?logo=github&logoColor=ffffff&branch=master&style=for-the-badge)](#)
[![Reaction Light Discord Server](https://img.shields.io/discord/914952998109716531?color=5865f2&logo=discord&logoColor=ffffff&style=for-the-badge)](https://discord.gg/cqxZQkhhHm)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg?logo=python&logoColor=ffffff&style=for-the-badge)](#)
[![disnake 2.5.0+](https://img.shields.io/badge/disnake-2.5.0+-blue.svg?logo=pypi&logoColor=ffffff&style=for-the-badge)](#)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue.svg?logo=docker&logoColor=ffffff&style=for-the-badge)](https://github.com/eibex/reaction-light/pkgs/container/reaction-light)

[![Reaction Light Embed Example](https://i.imgur.com/f4b9Qye.png)](#)

Light yet powerful reaction role bot coded in Python.

## Key Features
- Create multiple custom embedded messages with custom reactions and roles, or use other messages and add reactionroles to them
- Automatically assign/remove roles to users when they select/deselect a certain reaction
- Optionally limit users to select one reaction (and role) at a time
- Use the same instance of the bot on multiple servers
- Easy installation, setup, and updating: no need to rely on developer mode and IDs
- Optional update notifications and error reporting to your own Discord server
- Multiple languages
- Slash command ready
- Docker support

You can host the bot yourself by configuring the `config.ini` file (manually or via `setup.py`).

## Contents
- [Installation, Updates & Commands](#installation-updates--commands)
- [Roadmap](#roadmap)
- [FAQ](#faq)
- [Help](#help)
- [Contribute](#contribute)
- [License](#license)

## Installation, Updates & Commands
You can find guides on installating, updating, and using the bot in the [wiki](https://github.com/eibex/reaction-light/wiki).

## Roadmap
Upcoming features can be found in the open issues and PRs tagged with **new feature** or **enhancement**. They can be found [here](https://github.com/eibex/reaction-light/issues?q=is%3Aopen).

Open a new issue if you would like to see a feature implemented, and/or open a pull request implementing it.

## FAQ
**When I click one of the reactions the bot does not give me a role!**

Ensure that you moved the `Reaction Light` role to a position that is hierarchically higher than the role you are trying to assign.

**The bot says I am not an admin, even though I own the server (or have admin rights for it)**

Run `/admin add @Role` to give all users with that role permission to manage Reaction Light. This is done to have server staff use the bot without giving them unnecessary server rights. The only server admin command is `/admin`.

**I have updated from v2 to v3 and I do not see any slash commands**

Ensure that you followed the update steps as outlined in the changelog for v3.0.0. If this still doesn't fix the issue, try to shutdown the bot and re-inviting it to your server with the link provided in this readme or in the changelog.

## Help
If you need help with the bot or need to report bugs, post an issue [here](https://github.com/eibex/reaction-light/issues).
You can also join our [Discord server](https://discord.gg/cqxZQkhhHm).

## Contribute
If you would like to contribute to this project, fork it and then create a pull request. Please ensure that you have thoroughly tested all your changes. We use Black formatting with a line length of 130, and spaces (no tabs).

```
black --line-length=130 .
```

Even if you are not a Python programmer, you can contribute to this project by reporting bugs, requesting new features, or translating the bot in your language. To translate the bot simply copy the [English file](https://github.com/eibex/reaction-light/blob/master/i18n/en-gb.json) and replace the text inside the second quotes of each line. Do not replace the text within `{}`. Click [here](https://github.com/eibex/reaction-light/blob/master/i18n/it-it.json) for an example.

## License
[MIT](https://github.com/eibex/reaction-light/blob/master/LICENSE)
