import configparser
from sys import platform, exit as shutdown
import os
from shutil import copy
from itertools import cycle
from urllib.request import urlopen
import csv
import discord
from discord.ext import commands, tasks
import rldb
import migration


# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

directory = os.path.dirname(os.path.realpath(__file__))

migrated = migration.migrate()
config_migrated = migration.migrateconfig()

with open(f"{directory}/.version") as f:
    __version__ = f.read().rstrip("\n").rstrip("\r")

folder = f"{directory}/files"
config = configparser.ConfigParser()
config.read(f"{directory}/config.ini")
TOKEN = str(config.get("server", "token"))
prefix = str(config.get("server", "prefix"))
botname = str(config.get("server", "name"))

Client = discord.Client()
bot = commands.Bot(command_prefix=prefix)
bot.remove_command("help")

# IDs
admins = rldb.get_admins()
system_channel = int(config.get("server", "system_channel"))
logo = str(config.get("server", "logo"))
activities = []

if not os.path.isfile(f"{folder}/activities.csv"):
    copy(
        f"{folder}/activities.csv.sample", f"{folder}/activities.csv",
    )

activities_file = f"{folder}/activities.csv"
with open(activities_file, "r") as f:
    reader = csv.reader(f, delimiter=",")
    for row in reader:
        activity = row[0]
        activities.append(activity)
activities = cycle(activities)

# Colour palette - changes 'embeds' sideline colour
botcolor = 0xFFFF00


def isadmin(ctx, msg=False):
    # Checks if command author has one of config.ini admin role IDs
    try:
        check = (
            [role.id for role in ctx.author.roles]
            if msg
            else [role.id for role in ctx.message.author.roles]
        )
        if [role for role in admins if role in check]:
            return True
        return False
    except AttributeError:
        # Error raised from 'fake' users, such as webhooks
        return False


def get_latest():
    data = urlopen(
        "https://raw.githubusercontent.com/eibex/reaction-light/master/.version"
    )
    for line in data:
        latest = line.decode()
        break
    return latest


def check_for_updates():
    # Get latest version from GitHub repo and checks it against the current one
    latest = get_latest()
    if latest > __version__:
        return latest
    return False


def restart():
    os.chdir(directory)
    python = "python" if platform == "win32" else "python3"
    cmd = os.popen(f"nohup {python} bot.py &")
    cmd.close()


@tasks.loop(seconds=30)
async def maintain_presence():
    # Loops through the activities specified in activities.csv
    activity = next(activities)
    await bot.change_presence(activity=discord.Game(name=activity))


@tasks.loop(seconds=86400)
async def updates():
    # Sends a reminder once a day if there are updates available
    new_version = check_for_updates()
    if system_channel and new_version:
        channel = bot.get_channel(system_channel)
        await channel.send(
            f"An update is available. Download Reaction Light v{new_version} at https://github.com/eibex/reaction-light "
            f"or simply use `{prefix}update` (only works with git installations).\n\n"
            "You can view what has changed here: <https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md>"
        )


@bot.event
async def on_ready():
    print("Reaction Light ready!")
    if migrated and system_channel:
        channel = bot.get_channel(system_channel)
        await channel.send(
            "Your CSV files have been deleted and migrated to an SQLite `reactionlight.db` file."
        )
    if config_migrated and system_channel:
        channel = bot.get_channel(system_channel)
        await channel.send(
            "Your `config.ini` has been edited and your admin IDs are now stored in the database.\n"
            f"You can add or remove them with `{prefix}admin` and `{prefix}rm-admin`."
        )
    maintain_presence.start()
    updates.start()


@bot.event
async def on_message(message):
    if isadmin(message, msg=True):
        user = str(message.author.id)
        channel = str(message.channel.id)
        step = rldb.step(user, channel)
        msg = message.content.split()

        if step is not None:
            # Checks if the setup process was started before.
            # If it was not, it ignores the message.
            if step == 1:
                # The channel the message needs to be sent to is stored
                # Advances to step two
                try:
                    server = bot.get_guild(message.guild.id)
                    bot_user = server.get_member(bot.user.id)
                    target_channel = message.channel_mentions[0].id
                    bot_permissions = bot.get_channel(target_channel).permissions_for(
                        bot_user
                    )
                    writable = bot_permissions.read_messages
                    readable = bot_permissions.view_channel
                    if not writable or not readable:
                        await message.channel.send(
                            "I cannot read or send messages in that channel."
                        )
                        return
                except IndexError:
                    await message.channel.send("The channel you mentioned is invalid.")
                    return

                rldb.step1(user, channel, target_channel)
                await message.channel.send(
                    "Attach roles and emojis separated by one space (one combination per message). "
                    "When you are done type `done`. Example:\n:smile: `@Role`"
                )
            elif step == 2:
                if msg[0].lower() != "done":
                    # Stores reaction-role combinations until "done" is received
                    try:
                        reaction = msg[0]
                        role = message.role_mentions[0].id
                        await message.add_reaction(reaction)
                        rldb.step2(user, channel, role, reaction)
                    except IndexError:
                        await message.channel.send(
                            "Mention a role after the reaction. Example:\n:smile: `@Role`"
                        )
                    except discord.HTTPException:
                        await message.channel.send(
                            "You can only use reactions uploaded to this server or standard emojis."
                        )
                else:
                    # Advances to step three
                    rldb.step2(user, channel, done=True)

                    selector_embed = discord.Embed(
                        title="Embed_title",
                        description="Embed_content",
                        colour=botcolor,
                    )
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)
                    await message.channel.send(
                        "What would you like the message to say?"
                        "\nFormatting is: `Message // Embed_title // Embed_content`."
                        "\n\n`Embed_title` and `Embed_content` are optional. "
                        "You can type `none` in any of the argument fields above (e.g. `Embed_title`) to "
                        "make the bot ignore it."
                        "\n\n\nMessage",
                        embed=selector_embed,
                    )
            elif step == 3:
                # Receives the title and description of the reaction-role message
                # If the formatting is not correct it reminds the user of it
                msg_values = message.content.split(" // ")
                selector_msg_body = (
                    msg_values[0] if msg_values[0].lower() != "none" else None
                )
                selector_embed = discord.Embed(colour=botcolor)
                selector_embed.set_footer(text=f"{botname}", icon_url=logo)
                if len(msg_values) > 1:

                    if msg_values[1].lower() != "none":
                        selector_embed.title = msg_values[1]
                    if len(msg_values) > 2 and msg_values[2].lower() != "none":
                        selector_embed.description = msg_values[2]

                # Prevent sending an empty embed instead of removing it
                selector_embed = (
                    selector_embed
                    if selector_embed.title or selector_embed.description
                    else None
                )

                if selector_msg_body or selector_embed:
                    target_channel = bot.get_channel(
                        rldb.get_targetchannel(user, channel)
                    )
                    selector_msg = None
                    try:
                        selector_msg = await target_channel.send(
                            content=selector_msg_body, embed=selector_embed
                        )
                    except discord.Forbidden as ef:
                        await message.channel.send(
                            "I don't have permission to send selector_msg messages to the channel {0.mention}.".format(
                                target_channel
                            )
                        )
                    if isinstance(selector_msg, discord.Message):
                        combos = rldb.get_combos(user, channel)
                        rldb.end_creation(user, channel, selector_msg.id)
                        for reaction in combos:
                            try:
                                await selector_msg.add_reaction(reaction)
                            except discord.Forbidden:
                                await message.channel.send(
                                    "I don't have permission to react to messages from the channel {0.mention}.".format(
                                        target_channel
                                    )
                                )
                else:
                    await message.channel.send(
                        "You can't use an empty message as a role-reaction message."
                    )

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    reaction = str(payload.emoji)
    msg_id = payload.message_id
    ch_id = payload.channel_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    exists = rldb.exists(msg_id)
    if exists:
        # Checks that the message that was reacted to is a reaction-role message managed by the bot
        reactions = rldb.get_reactions(msg_id)
        ch = bot.get_channel(ch_id)
        msg = await ch.fetch_message(msg_id)
        user = bot.get_user(user_id)
        if reaction not in reactions:
            # Removes reactions added to the reaction-role message that are not connected to any role
            await msg.remove_reaction(reaction, user)
        else:
            # Gives role if it has permissions, else 403 error is raised
            role_id = reactions[reaction]
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=role_id)
            if user_id != bot.user.id:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    if system_channel:
                        channel = bot.get_channel(system_channel)
                        await channel.send(
                            "Someone tried to add a role to themselves but I do not have permissions to add it. "
                            "Ensure that I have a role that is hierarchically higher than the role I have to assign, "
                            "and that I have the `Manage Roles` permission."
                        )


@bot.event
async def on_raw_reaction_remove(payload):
    reaction = str(payload.emoji)
    msg_id = payload.message_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    exists = rldb.exists(msg_id)
    if exists:
        # Checks that the message that was unreacted to is a reaction-role message managed by the bot
        reactions = rldb.get_reactions(msg_id)
        if reaction in reactions:
            role_id = reactions[reaction]
            # Removes role if it has permissions, else 403 error is raised
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=role_id)
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                if system_channel:
                    channel = bot.get_channel(system_channel)
                    await channel.send(
                        "Someone tried to remove a role from themselves but I do not have permissions to remove it. "
                        "Ensure that I have a role that is hierarchically higher than the role I have to remove, "
                        "and that I have the `Manage Roles` permission."
                    )


@bot.command(name="new")
async def new(ctx):
    if isadmin(ctx):
        # Starts setup process and the bot starts to listen to the user in that channel
        # For future prompts (see: "async def on_message(message)")
        rldb.start_creation(ctx.message.author.id, ctx.message.channel.id)
        await ctx.send("Mention the #channel where to send the auto-role message.")
    else:
        await ctx.send(f"You do not have an admin role. You might want to use `{prefix}admin` first.")


@bot.command(name="edit")
async def edit_selector(ctx):
    if isadmin(ctx):
        # Reminds user of formatting if it is wrong
        msg_values = ctx.message.content.split()
        if len(msg_values) < 2:
            await ctx.send(
                f"**Type** `{prefix}edit #channelname` to get started. Replace `#channelname` "
                "with the channel where the reaction-role message "
                "you wish to edit is located."
            )
            return
        elif len(msg_values) == 2:
            try:
                channel_id = ctx.message.channel_mentions[0].id
            except IndexError:
                await ctx.send("You need to mention a channel.")
                return

            all_messages = rldb.fetch_messages(channel_id)
            channel = bot.get_channel(channel_id)
            if len(all_messages) == 1:
                await ctx.send(
                    "There is only one reaction-role message in this channel. **Type**:"
                    f"\n```\n{prefix}edit #{channel.name} // 1 // New Message // New Embed Title (Optional) // New Embed Description (Optional)\n```"
                    "\nto edit the reaction-role message. You can type `none` in any of the argument fields above (e.g. `New Message`) to "
                    "make the bot ignore it."
                )
            elif len(all_messages) > 1:
                selector_msgs = []
                counter = 1
                for msg_id in all_messages:
                    try:
                        old_msg = await channel.fetch_message(int(msg_id))
                    except discord.NotFound:
                        # Skipping reaction-role messages that might have been deleted without updating CSVs
                        continue
                    except discord.Forbidden:
                        ctx.send(
                            "I do not have permissions to edit a reaction-role message that I previously created."
                        )
                        continue
                    entry = f"`{counter}` {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
                    selector_msgs.append(entry)
                    counter += 1

                await ctx.send(
                    f"There are **{len(all_messages)}** reaction-role messages in this channel. **Type**:"
                    f"\n```\n{prefix}edit #{channel.name} // MESSAGE_NUMBER // New Message // New Embed Title (Optional) // New Embed Description (Optional)\n```"
                    "\nto edit the desired one. You can type `none` in any of the argument fields above (e.g. `New Message`) to make the bot ignore it. "
                    "The list of the current reaction-role messages is:\n\n"
                    + "\n".join(selector_msgs)
                )
            else:
                await ctx.send("There are no reaction-role messages in that channel.")
        elif len(msg_values) > 2:
            try:
                # Tries to edit the reaction-role message
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                channel_id = ctx.message.channel_mentions[0].id
                channel = bot.get_channel(channel_id)
                msg_values = ctx.message.content.split(" // ")
                selector_msg_number = msg_values[1]
                all_messages = rldb.fetch_messages(channel_id)
                counter = 1

                # Loop through all msg_ids and stops when the counter matches the user input
                if all_messages:
                    message_to_edit_id = None
                    for msg_id in all_messages:
                        if str(counter) == selector_msg_number:
                            message_to_edit_id = msg_id
                            break
                        counter += 1
                else:
                    await ctx.send(
                        "You selected a reaction-role message that does not exist."
                    )
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))
                else:
                    await ctx.send(
                        "Select a valid reaction-role message number (i.e. the number to the left of the reaction-role message content in the list above)."
                    )
                    return

                await old_msg.edit(suppress=False)
                selector_msg_new_body = (
                    msg_values[2] if msg_values[2].lower() != "none" else None
                )
                selector_embed = discord.Embed()
                if len(msg_values) == 3 and old_msg.embeds:
                    selector_embed = old_msg.embeds[0]
                if len(msg_values) > 3 and msg_values[3].lower() != "none":
                    selector_embed.title = msg_values[3]
                    selector_embed.colour = botcolor
                    if old_msg.embeds and len(msg_values) == 4:
                        selector_embed.description = old_msg.embeds[0].description
                if len(msg_values) > 4 and msg_values[4].lower() != "none":
                    selector_embed.description = msg_values[4]
                    selector_embed.colour = botcolor

                # Prevent sending an empty embed instead of removing it
                selector_embed = (
                    selector_embed
                    if selector_embed.title or selector_embed.description
                    else None
                )

                if selector_msg_new_body or selector_embed:
                    await old_msg.edit(
                        content=selector_msg_new_body, embed=selector_embed
                    )
                    await ctx.send("Message edited.")
                else:
                    await ctx.send(
                        "You can't use an empty message as role-reaction message."
                    )

            except IndexError:
                await ctx.send("The channel you mentioned is invalid.")

            except discord.Forbidden:
                await ctx.send("I do not have permissions to edit the message.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="rm-embed")
async def remove_selector_embed(ctx):
    if isadmin(ctx):
        # Reminds user of formatting if it is wrong
        msg_values = ctx.message.content.split()
        if len(msg_values) < 2:
            await ctx.send(
                f"**Type** `{prefix}rm-embed #channelname` to get started. Replace `#channelname` "
                "with the channel where the reaction-role message "
                "you wish to remove its embed is located."
            )
            return
        elif len(msg_values) == 2:
            try:
                channel_id = ctx.message.channel_mentions[0].id
            except IndexError:
                await ctx.send("The channel you mentioned is invalid.")
                return

            channel = bot.get_channel(channel_id)
            all_messages = rldb.fetch_messages(channel_id)
            if len(all_messages) == 1:
                await ctx.send(
                    "There is only one reaction-role message in this channel. **Type**:"
                    f"\n```\n{prefix}rm-embed #{channel.name} // 1\n```"
                    "\nto remove the reaction-role message's embed."
                )
            elif len(all_messages) > 1:
                selector_msgs = []
                counter = 1
                for msg_id in all_messages:
                    try:
                        old_msg = await channel.fetch_message(int(msg_id))
                    except discord.NotFound:
                        # Skipping reaction-role messages that might have been deleted without updating the DB
                        continue
                    except discord.Forbidden:
                        ctx.send(
                            "I do not have permissions to edit a reaction-role message that I previously created."
                        )
                        continue
                    entry = f"`{counter}` {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
                    selector_msgs.append(entry)
                    counter += 1

                await ctx.send(
                    f"There are **{len(all_messages)}** reaction-role messages in this channel. **Type**:"
                    f"\n```\n{prefix}rm-embed #{channel.name} // MESSAGE_NUMBER\n```"
                    "\nto remove its embed. The list of the current reaction-role messages is:\n\n"
                    + "\n".join(selector_msgs)
                )
            else:
                await ctx.send("There are no reaction-role messages in that channel.")
        elif len(msg_values) > 2:
            try:
                # Tries to edit the reaction-role message
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                channel_id = ctx.message.channel_mentions[0].id
                channel = bot.get_channel(channel_id)
                msg_values = ctx.message.content.split(" // ")
                selector_msg_number = msg_values[1]
                all_messages = rldb.fetch_messages(channel_id)
                counter = 1

                # Loop through all msg_ids and stops when the counter matches the user input
                if all_messages:
                    message_to_edit_id = None
                    for msg_id in all_messages:
                        if str(counter) == selector_msg_number:
                            message_to_edit_id = msg_id
                            break
                        counter += 1
                else:
                    await ctx.send(
                        "You selected a reaction-role message that does not exist."
                    )
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))
                else:
                    await ctx.send(
                        "Select a valid reaction-role message number (i.e. the number to the left of the reaction-role message content in the list above)."
                    )
                    return

                try:
                    await old_msg.edit(embed=None)
                    await ctx.send("Embed Removed.")
                except discord.HTTPException as e:
                    if e.code == 50006:
                        await ctx.send(
                            "You can't remove an embed if its message is empty. Please edit the message first with: "
                            f"\n`{prefix}edit #{ctx.message.channel_mentions[0]} // {selector_msg_number} // New Message`"
                        )
                    else:
                        await ctx.send(str(e))

            except IndexError:
                await ctx.send("The channel you mentioned is invalid.")

            except discord.Forbidden:
                await ctx.send("I do not have permissions to edit the message.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="systemchannel")
async def set_systemchannel(ctx):
    if isadmin(ctx):
        global system_channel
        try:
            system_channel = ctx.message.channel_mentions[0].id

            server = bot.get_guild(ctx.message.guild.id)
            bot_user = server.get_member(bot.user.id)
            bot_permissions = bot.get_channel(system_channel).permissions_for(bot_user)
            writable = bot_permissions.read_messages
            readable = bot_permissions.view_channel
            if not writable or not readable:
                await ctx.send("I cannot read or send messages in that channel.")
                return

            config["server"]["system_channel"] = str(system_channel)

            with open("config.ini", "w") as f:
                config.write(f)

            await ctx.send("System channel updated.")

        except IndexError:
            await ctx.send(
                "Mention the channel you would like to receive notifications in.\n"
                f"`{prefix}systemchannel #channelname`"
            )


@bot.command(name="help")
async def hlp(ctx):
    if isadmin(ctx):
        await ctx.send(
            "Commands are:\n"
            f"- `{prefix}new` starts the creation process for a new reaction role message.\n"
            f"- `{prefix}edit` edits an existing reaction-role message or provides instructions on how to do so if no arguments are passed.\n"
            f"- `{prefix}rm-embed` suppresses the embed of an existing reaction-role message or provides instructions on how to do so if no arguments are passed.\n"
            f"- `{prefix}admin` adds the mentioned role to the list of {botname} admins, allowing them to create and edit reaction-role messages. You need to be a server administrator to use this command.\n"
            f"- `{prefix}rm-admin` removes the mentioned role from the list of {botname} admins, preventing them from creating and editing reaction-role messages. You need to be a server administrator to use this command.\n"
            f"- `{prefix}kill` shuts down the bot.\n"
            f"- `{prefix}systemchannel` updates the system channel where the bot sends errors and update notifications.\n"
            f"- `{prefix}restart` restarts the bot. Only works on installations running on GNU/Linux.\n"
            f"- `{prefix}update` updates the bot and restarts it. Only works on `git clone` installations running on GNU/Linux.\n"
            f"- `{prefix}version` reports the bot's current version and the latest available one from GitHub.\n\n"
            f"{botname} is running version {__version__} of Reaction Light. Find more resources at: <https://github.com/eibex/reaction-light>"
        )
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="admin")
@commands.has_permissions(administrator=True)
async def add_admin(ctx):
    try:
        role = ctx.message.role_mentions[0].id
    except IndexError:
        try:
            role = int(ctx.message.content.split()[1])
        except ValueError:
            ctx.send("Please mention a valid @Role or role ID.")
        except IndexError:
            ctx.send("Please mention a @Role or role ID.")
    rldb.add_admin(role)


@bot.command(name="rm-admin")
@commands.has_permissions(administrator=True)
async def remove_admin(ctx):
    try:
        role = ctx.message.role_mentions[0].id
    except IndexError:
        try:
            role = int(ctx.message.content.split()[1])
        except ValueError:
            ctx.send("Please mention a valid @Role or role ID.")
        except IndexError:
            ctx.send("Please mention a @Role or role ID.")
    rldb.remove_admin(role)


@bot.command(name="version")
async def print_version(ctx):
    if isadmin(ctx):
        latest = get_latest()
        await ctx.send(
            f"I am currently running v{__version__}. The latest available version is v{latest}."
        )


@bot.command(name="kill")
async def kill(ctx):
    if isadmin(ctx):
        await ctx.send("Shutting down...")
        shutdown()  # sys.exit()
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="restart")
async def restart_cmd(ctx):
    if isadmin(ctx):
        if platform != "win32":
            restart()
            await ctx.send("Restarting...")
            shutdown()  # sys.exit()
        else:
            await ctx.send("I cannot do this on Windows.")
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="update")
async def update(ctx):
    if isadmin(ctx):
        if platform != "win32":
            await ctx.send("Attempting update...")
            os.chdir(directory)
            cmd = os.popen("git fetch")
            cmd.close()
            cmd = os.popen("git pull")
            cmd.close()
            restart()
            await ctx.send("Restarting...")
            shutdown()  # sys.exit()
        else:
            await ctx.send("I cannot do this on Windows.")
    else:
        await ctx.send("You do not have an admin role.")


bot.run(TOKEN)
