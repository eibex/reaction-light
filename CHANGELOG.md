# Reaction Light - Changelog

### 2.5.0
- Fix `rl!new` showing unsuccessful reaction when the message creation was actually successful
- Add support for translations. To translate the bot's responses make a copy of [en.json](https://github.com/eibex/reaction-light/blob/master/files/i18n/en.json) and translate the associated strings. Consider sharing your translation as a pull request ([#74](https://github.com/eibex/reaction-light/issues/74) closed by [#77](https://github.com/eibex/reaction-light/pull/77) by [eibex](https://github.com/eibex), [Edwinexd](https://github.com/Edwinexd), and [d7415](https://github.com/d7415)).

### 2.4.3
- Fix deletion of wrong database entries under certain circumstances. Please check that all your messages are working before updating, and restore a backup if necessary ([#73](https://github.com/eibex/reaction-light/issues/73) closed by [#78](https://github.com/eibex/reaction-light/pull/78) by [Edwinexd](https://github.com/Edwinexd))


### 2.4.2
- Fix errors when trying to set a new server-specific system channel with `rl!systemchannel server #channel`

### 2.4.1
- Removed migration from CSV to SQLite ([#63](https://github.com/eibex/reaction-light/issues/63) closed by [#64](https://github.com/eibex/reaction-light/pull/64) by [eibex](https://github.com/eibex))
- Improved `rl!systemchannel` explanation when running the command with no arguments ([#65](https://github.com/eibex/reaction-light/issues/65) by [eibex](https://github.com/eibex))
- Fix f-string syntax errors on older Python versions ([#68](https://github.com/eibex/reaction-light/issues/68) closed by [#69](https://github.com/eibex/reaction-light/pull/69) by [Edwinexd](https://github.com/Edwinexd))
- Corrected dependencies ([#70](https://github.com/eibex/reaction-light/pull/70) by [minemalox](https://github.com/minemalox))
- Corrected Python minimum version to 3.6 ([#71](https://github.com/eibex/reaction-light/pull/71) by [Edwinexd](https://github.com/Edwinexd))

### 2.4.0
- Added support for mutually exclusive role/reactions: when creating a new message you can choose to limit users to select only one reaction (and role) at a time ([#44](https://github.com/eibex/reaction-light/issues/44) closed by [#60](https://github.com/eibex/reaction-light/pull/60) by [eibex](https://github.com/eibex) and [Edwinexd](https://github.com/Edwinexd))
- Show the latest version changes with the update notifications and `rl!version` command ([#60](https://github.com/eibex/reaction-light/pull/60) by [eibex](https://github.com/eibex))
- Fix missing error reporting when checking for notifications ([#60](https://github.com/eibex/reaction-light/pull/60) by [eibex](https://github.com/eibex))

### 2.3.0
- Adds the option to send a DM to the user when they add or remove a role from themselves ([#50](https://github.com/eibex/reaction-light/issues/50) closed by [#58](https://github.com/eibex/reaction-light/pull/58) by [eibex](https://github.com/eibex))
- Add the `rl!notify` command to toggle user notifications on add/remove for the current server (if you want to turn them on on multiple servers, use the command on each server)
- Merge `systemchannels` table into the `guild_settings` table

### 2.2.0
- Added support for custom messages & reworked creation process ([#56](https://github.com/eibex/reaction-light/issues/56) closed by [#57](https://github.com/eibex/reaction-light/pull/57) by [Edwinexd](https://github.com/Edwinexd))
- Reworked ReactionRole ID generation ([#30](https://github.com/eibex/reaction-light/issues/30) closed by [#57](https://github.com/eibex/reaction-light/pull/57) by [Edwinexd](https://github.com/Edwinexd))
- Removed the `rl!abort` command. ([#57](https://github.com/eibex/reaction-light/pull/57) by [Edwinexd](https://github.com/Edwinexd))

### 2.1.3
- Fix errors occuring during reaction-role message creation/editing ([#54](https://github.com/eibex/reaction-light/issues/54) closed by [#55](https://github.com/eibex/reaction-light/pull/55) by [Edwinexd](https://github.com/Edwinexd))

### 2.1.2
- Fix database errors resulting in guilds not being cleaned up

### 2.1.1
- Fix errors related to missing elements in the bot cache

### 2.1.0
- Fix guild clean-up ([#52](https://github.com/eibex/reaction-light/issues/52) closed by [#53](https://github.com/eibex/reaction-light/pull/53) by [Edwinexd](https://github.com/Edwinexd))
- Message clean-up reworked ([#53](https://github.com/eibex/reaction-light/pull/53) by [Edwinexd](https://github.com/Edwinexd))
- Admin system reworked ([#53](https://github.com/eibex/reaction-light/pull/53) by [Edwinexd](https://github.com/Edwinexd))
- Removed access to `kill`, `restart`, `update`, `color`, `activity` (and related) commands from non-bot owners ([#53](https://github.com/eibex/reaction-light/pull/53) by [Edwinexd](https://github.com/Edwinexd))

### 2.0.1
- Fix footers being deleted upon embed edit ([#49](https://github.com/eibex/reaction-light/pull/49) by [Edwinexd](https://github.com/Edwinexd))
- Remove start up messages informing that no migration was needed

### 2.0.0
- Added support for discord.py 1.5.0 and dropped support for any older version (the new Discord API is replacing the older one) ([#47](https://github.com/eibex/reaction-light/issues/47) closed by [#48](https://github.com/eibex/reaction-light/pull/48) by [eibex](https://github.com/eibex))
- **What you NEED to do**
  - Add the server members priviliged intent to your bot on the [Discord Developer Portal](https://discord.com/developers/applications)
  - You might have to re-clone the bot because of git history conflicts (copy the `config.ini` file and the `files` folder to the new installation and all your reaction-role messages will keep working as expected)

### 1.6.1
- Prevent adding an already existing reaction to new or existing reaction-role messages

### 1.6.0
- Add `rl!reaction` to add or remove reactions from existing reaction-role messages ([#1](https://github.com/eibex/reaction-light/issues/1) closed by [#43](https://github.com/eibex/reaction-light/pull/43) by [eibex](https://github.com/eibex))

### 1.5.4
- Merge `rl!rm-embed` into `rl!edit` (`rl!rm-embed` removed)

### 1.5.3
- Fix database errors when creating new reaction-role messages ([#41](https://github.com/eibex/reaction-light/issues/41) closed by [#42](https://github.com/eibex/reaction-light/pull/42) by [eibex](https://github.com/eibex))

### 1.5.2
- Fix migration for users directly migrating from 0.3.2 to 1.5.0+
- Fix database cleaning 
- Fix open database cursor and connection on schema updates

### 1.5.1
- Fix system channel fall back

### 1.5.0
- Add guild-only system channels to send error reports generated from messages of a certain guild in their own system channel ([#39](https://github.com/eibex/reaction-light/issues/39) closed by [#40](https://github.com/eibex/reaction-light/pull/40) by [eibex](https://github.com/eibex))
- Add fallback to the `config.ini` (aka main) system channel if a guild system channel was not set
- Modify `rl!systemchannel` to accept a new argument to define if the system channel being set is for a `server` or is the `main` one: `rl!systemchannel <main/server> #channelname`
- Modify database cleaning to include system channel entries of deleted guilds
- Add creation of database backups when `rl!update` is used
- Add automated database schema updates

### 1.4.0
- Add `rl!activity` command to add activities to show as bot status from within Discord.
- Add `rl!rm-activity` command to remove a given activity.
- Add `rl!activitylist` command to show all activities.
- Fix a crash (sorry!) ([#34](https://github.com/eibex/reaction-light/issues/34) closed by [#35](https://github.com/eibex/reaction-light/pull/35) by [eibex](https://github.com/eibex))
- Fix a wrong error description when failing to fetch admins

### 1.3.0
- Add `rl!adminlist` command to show the current bot admins registered in the database

### 1.2.1
- Fix saving of colour variables to the configuration file when updated via command

### 1.2.0
- Add configurable embed colours via `rl!colour` ([#32](https://github.com/eibex/reaction-light/pull/32) by [eibex](https://github.com/eibex))

### 1.1.2
- Automated database cleaning of deleted messages ([#26](https://github.com/eibex/reaction-light/pull/26) by [eibex](https://github.com/eibex))
- Better error reporting and catching ([#29](https://github.com/eibex/reaction-light/pull/29) by [eibex](https://github.com/eibex))

### 1.1.1
- Prevent SQL Injections ([#27](https://github.com/eibex/reaction-light/pull/27) by [arbaes](https://github.com/arbaes))
- Allow to abort setup via `rl!abort` ([#24](https://github.com/eibex/reaction-light/pull/24) by [eibex](https://github.com/eibex))

### 1.1.0
- Add `rl!admin` to allow members with a certain role to use the bot commands. Requires administrator permissions on the server ([#23](https://github.com/eibex/reaction-light/pull/23) by [eibex](https://github.com/eibex))
- Add `rl!rm-admin` to prevent members with a certain role from using the bot commands. Requires administrator permissions on the server ([#23](https://github.com/eibex/reaction-light/pull/23) by [eibex](https://github.com/eibex))
- Add migration script to transfer current admin roles from the config to the db ([#23](https://github.com/eibex/reaction-light/pull/23) by [eibex](https://github.com/eibex))

### 1.0.0
- Add `rl!rm-embed` to remove embeds from reaction-role messages, keeping the text-message body ([#21](https://github.com/eibex/reaction-light/pull/21) by [arbaes](https://github.com/arbaes))
- Improve `rl!edit` to add or edit a text-message body and/or embeds to reaction-role messages ([#21](https://github.com/eibex/reaction-light/pull/21) by [arbaes](https://github.com/arbaes))
- Improve `rl!new` and `rl!edit` by allowing to ignore text or embed fields ([#22](https://github.com/eibex/reaction-light/pull/22) by [arbaes](https://github.com/arbaes))
- Add SQLite database ([#20](https://github.com/eibex/reaction-light/pull/20) by [eibex](https://github.com/eibex))
- Add automatic migration to delete CSV files and transfer them to an SQLite database ([#20](https://github.com/eibex/reaction-light/pull/20) by [eibex](https://github.com/eibex))
- Remove `requests` dependency (rely on built-in `urllib` library instead)
- Minor improvements to `rl!help`

### 0.3.2
- Prevent update and restart commands when the bot is hosted on Windows to avoid errors
- Set all embed footers to show the configured bot name
- Improve `rl!help` to include all commands instead of just a few links to the README

### 0.3.1
- Fix "not admin" warning on embed edit ([#14](https://github.com/eibex/reaction-light/pull/14) by [arbaes](https://github.com/arbaes))
- Improve permission error handling ([#15](https://github.com/eibex/reaction-light/pull/15) by [arbaes](https://github.com/arbaes))
- Improve local version reading (read from file instead of hardcoded string) ([#16](https://github.com/eibex/reaction-light/pull/16) by [eibex](https://github.com/eibex))

### 0.3.0
- Add `rl!version` to show what version the bot is currently running

### 0.2.0
- Add `rl!restart` to restart the bot from within Discord ([#10](https://github.com/eibex/reaction-light/issues/10) closed by [#12](https://github.com/eibex/reaction-light/pull/12) by [eibex](https://github.com/eibex))
- Add `rl!update` to update the bot and restart it from within Discord (only works on `git` installations) ([#11](https://github.com/eibex/reaction-light/issues/11) closed by [#12](https://github.com/eibex/reaction-light/pull/12) by [eibex](https://github.com/eibex))

### 0.1.1
- Warns the user if no role mention is provided when creating combinations of reactions and roles
- Fix allowing users to create combinations with reactions from other servers that the bot cannot use ([#7](https://github.com/eibex/reaction-light/issues/7) closed by [#9](https://github.com/eibex/reaction-light/pull/9) by [eibex](https://github.com/eibex))
### 0.1.0
- Add Windows compatibility ([#4](https://github.com/eibex/reaction-light/issues/4) closed by [#8](https://github.com/eibex/reaction-light/pull/8) by [eibex](https://github.com/eibex))

### 0.0.7
- Add system channel updating via Discord (using the `rl!systemchannel` command)

### 0.0.6
- Allow editing embeds without relying on channel and message IDs ([#5](https://github.com/eibex/reaction-light/issues/5) closed by [#6](https://github.com/eibex/reaction-light/pull/6) by [eibex](https://github.com/eibex))

### 0.0.5
- Allow creating embeds without relying on channel IDs (partly fixes [#5](https://github.com/eibex/reaction-light/issues/5) by [eibex](https://github.com/eibex))
- Better handling of errors

### 0.0.4
- Fix file handling

### 0.0.3
- Add version checking

### 0.0.2
- Add guided setup

### 0.0.1
- Add embed creation process
- Add automatic role assignment and removal
