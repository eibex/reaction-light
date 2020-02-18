# Reaction Light - Changelog
Since 0.1.0 this project will adhere to [semantic versioning](https://semver.org/).
### 0.2.0
- Add `rl!restart` to restart the bot from within Discord
- Add `rl!update` to update the bot and restart it from within Discord (only works on `git` installations)
### 0.1.1
- Warns the user if no role mention is provided when creating combinations of reactions and roles
- Fix allowing users to create combinations with reactions from other servers that the bot cannot use ([#7](https://github.com/eibex/reaction-light/issues/7) closed by [#9](https://github.com/eibex/reaction-light/pull/9))
### 0.1.0
- Add Windows compatibility ([#4](https://github.com/eibex/reaction-light/issues/4) closed by [#8](https://github.com/eibex/reaction-light/pull/8))

### 0.0.7
- Add system channel updating via Discord (using the `rl!systemchannel` command)

### 0.0.6
- Allow editing embeds without relying on channel and message IDs ([#5](https://github.com/eibex/reaction-light/issues/5) closed by [#6](https://github.com/eibex/reaction-light/pull/6))

### 0.0.5
- Allow creating embeds without relying on channel IDs (partly fixes [#5](https://github.com/eibex/reaction-light/issues/5))
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
