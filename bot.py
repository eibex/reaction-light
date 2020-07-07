"""
MIT License

Copyright (c) 2019-2020 eibex

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import configparser
from shutil import copy
from sys import platform, exit as shutdown

import discord
from discord.ext import commands, tasks

from core import database, migration, activity, github, schema


directory = os.path.dirname(os.path.realpath(__file__))

migrated = migration.migrate()
config_migrated = migration.migrateconfig()

with open(f"{directory}/.version") as f:
    __version__ = f.read().rstrip("\n").rstrip("\r")

folder = f"{directory}/files"
config = configparser.ConfigParser()
config.read(f"{directory}/config.ini")
logo = str(config.get("server", "logo"))
TOKEN = str(config.get("server", "token"))
botname = str(config.get("server", "name"))
prefix = str(config.get("server", "prefix"))
system_channel = int(config.get("server", "system_channel"))
botcolour = discord.Colour(int(config.get("server", "colour"), 16))

Client = discord.Client()
bot = commands.Bot(command_prefix=prefix)
bot.remove_command("help")

activities_file = f"{directory}/files/activities.csv"
activities = activity.Activities(activities_file)
db_file = f"{directory}/files/reactionlight.db"
db = database.Database(db_file)


def isadmin(user):
    # Checks if command author has an admin role that was added with rl!admin
    admins = db.get_admins()

    if isinstance(admins, Exception):
        return False

    try:
        user_roles = [role.id for role in user.roles]
        return [admin_role for admin_role in admins if admin_role in user_roles]

    except AttributeError:
        # Error raised from 'fake' users, such as webhooks
        return False


def restart():
    # Create a new python process of bot.py and stops the current one
    os.chdir(directory)
    python = "python" if platform == "win32" else "python3"
    cmd = os.popen(f"nohup {python} bot.py &")
    cmd.close()


def database_updates():
    handler = schema.SchemaHandler(db_file)
    if handler.version == 0:
        handler.update()
        messages = db.fetch_all_messages()
        for message in messages:
            channel_id = messages[message]
            channel = bot.get_channel(channel_id)
            db.add_guild(channel.id, channel.guild.id)


async def system_notification(guild_id, text):
    # Send a message to the system channel (if set)
    if guild_id:
        server_channel = db.fetch_systemchannel(guild_id)

        if isinstance(server_channel, Exception):
            await system_notification(
                None,
                "Database error when fetching guild system"
                f" channels:\n```\n{server_channel}\n```\n\n{text}",
            )
            return

        if server_channel:
            try:
                target_channel = bot.get_channel(server_channel[0][0])
                await target_channel.send(text)

            except discord.Forbidden:
                await system_notification(None, text)

        else:
            await system_notification(None, text)

    elif system_channel:
        try:
            target_channel = bot.get_channel(system_channel)
            await target_channel.send(text)

        except discord.NotFound:
            print("I cannot find the system channel.")

        except discord.Forbidden:
            print("I cannot send messages to the system channel.")

    else:
        print(text)


@tasks.loop(seconds=30)
async def maintain_presence():
    # Loops through the activities specified in activities.csv
    activity = activities.get()
    await bot.change_presence(activity=discord.Game(name=activity))


@tasks.loop(hours=24)
async def updates():
    # Sends a reminder once a day if there are updates available
    new_version = github.check_for_updates(__version__)
    if new_version:
        await system_notification(
            None,
            f"An update is available. Download Reaction Light v{new_version} at"
            f" https://github.com/eibex/reaction-light or simply use `{prefix}update`"
            " (only works with git installations).\n\nYou can view what has changed"
            " here: <https://github.com/eibex/reaction-light/blob/master/CHANGELOG.md>",
        )


@tasks.loop(hours=24)
async def cleandb():
    # Cleans the database by deleting rows of reaction role messages that don't exist anymore
    messages = db.fetch_all_messages()
    guilds = db.fetch_all_guilds()

    if isinstance(messages, Exception):
        await system_notification(
            None,
            "Database error when fetching messages during database"
            f" cleaning:\n```\n{messages}\n```",
        )
        return

    for message in messages:
        try:
            channel_id = messages[message]
            channel = bot.get_channel(channel_id)
            if channel is None:
                channel = await bot.fetch_channel(channel_id)

            await channel.fetch_message(message)

        except discord.NotFound as e:
            # If unknown channel or unknown message
            if e.code == 10003 or e.code == 10008:
                delete = db.delete(message)

                if isinstance(delete, Exception):
                    await system_notification(
                        channel.guild.id,
                        "Database error when deleting messages during database"
                        f" cleaning:\n```\n{delete}\n```",
                    )
                    return

                await system_notification(
                    channel.guild.id,
                    "I deleted the database entries of a message that was removed."
                    f"\n\nID: {message} in {channel.mention}",
                )

        except discord.Forbidden:
            await system_notification(
                channel.guild.id,
                "I do not have access to a message I have created anymore. "
                "I cannot manage the roles of users reacting to it."
                f"\n\nID: {message} in {channel.mention}",
            )

    if isinstance(guilds, Exception):
        await system_notification(
            None,
            "Database error when fetching guilds during database"
            f" cleaning:\n```\n{guilds}\n```",
        )
        return

    for guild_id in guilds:
        try:
            await bot.fetch_guild(guild_id)

        except discord.NotFound as e:
            # If unknown guild
            if e.code == 10004:
                delete = db.remove_systemchannel(guild_id)

                if isinstance(delete, Exception):
                    await system_notification(
                        None,
                        "Database error when deleting system channels during"
                        f" database cleaning:\n```\n{delete}\n```",
                    )
                    return

                delete = db.delete(message_id=None, guild_id=guild_id)

                if isinstance(delete, Exception):
                    await system_notification(
                        None,
                        "Database error when deleting messages during"
                        f" database cleaning:\n```\n{delete}\n```",
                    )
                    return

                await system_notification(
                    None,
                    "I deleted the database entries of a guild that was removed."
                    f"\n\nID: {guild_id}",
                )


@bot.event
async def on_ready():
    print("Reaction Light ready!")
    if migrated:
        await system_notification(
            None,
            "Your CSV files have been deleted and migrated to an SQLite"
            " `reactionlight.db` file.",
        )

    if config_migrated:
        await system_notification(
            None,
            "Your `config.ini` has been edited and your admin IDs are now stored in"
            f" the database.\nYou can add or remove them with `{prefix}admin` and"
            f" `{prefix}rm-admin`.",
        )

    database_updates()

    maintain_presence.start()
    cleandb.start()
    updates.start()


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if isadmin(message.author):
        user = str(message.author.id)
        channel = str(message.channel.id)
        step = db.step(user, channel)
        msg = message.content.split()

        # Checks if the setup process was started before.
        # If it was not, it ignores the message.
        if step is not None:
            if step == 0:
                db.step0(user, channel)

            elif step == 1:
                # The channel the message needs to be sent to is stored
                # Advances to step two
                if message.channel_mentions:
                    target_channel = message.channel_mentions[0].id

                else:
                    await message.channel.send("The channel you mentioned is invalid.")
                    return

                server = bot.get_guild(message.guild.id)
                bot_user = server.get_member(bot.user.id)
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

                db.step1(user, channel, target_channel)

                await message.channel.send(
                    "Attach roles and emojis separated by one space (one combination"
                    " per message). When you are done type `done`. Example:\n:smile:"
                    " `@Role`"
                )
            elif step == 2:
                if msg[0].lower() != "done":
                    # Stores reaction-role combinations until "done" is received
                    try:
                        reaction = msg[0]
                        role = message.role_mentions[0].id
                        await message.add_reaction(reaction)

                        db.step2(user, channel, role, reaction)

                    except IndexError:
                        await message.channel.send(
                            "Mention a role after the reaction. Example:\n:smile:"
                            " `@Role`"
                        )

                    except discord.HTTPException:
                        await message.channel.send(
                            "You can only use reactions uploaded to this server or"
                            " standard emojis."
                        )
                else:
                    # Advances to step three
                    db.step2(user, channel, done=True)

                    selector_embed = discord.Embed(
                        title="Embed_title",
                        description="Embed_content",
                        colour=botcolour,
                    )
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)

                    await message.channel.send(
                        "What would you like the message to say?\nFormatting is:"
                        " `Message // Embed_title // Embed_content`.\n\n`Embed_title`"
                        " and `Embed_content` are optional. You can type `none` in any"
                        " of the argument fields above (e.g. `Embed_title`) to make the"
                        " bot ignore it.\n\n\nMessage",
                        embed=selector_embed,
                    )

            elif step == 3:
                # Receives the title and description of the reaction-role message
                # If the formatting is not correct it reminds the user of it
                msg_values = message.content.split(" // ")
                selector_msg_body = (
                    msg_values[0] if msg_values[0].lower() != "none" else None
                )
                selector_embed = discord.Embed(colour=botcolour)
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
                        db.get_targetchannel(user, channel)
                    )
                    selector_msg = None
                    try:
                        selector_msg = await target_channel.send(
                            content=selector_msg_body, embed=selector_embed
                        )

                    except discord.Forbidden:
                        await message.channel.send(
                            "I don't have permission to send selector_msg messages to"
                            f" the channel {target_channel.mention}."
                        )

                    if isinstance(selector_msg, discord.Message):
                        combos = db.get_combos(user, channel)

                        end = db.end_creation(user, channel, selector_msg.id)
                        if isinstance(end, Exception):
                            await message.channel.send(
                                "I could not commit the changes to the database."
                            )
                            await system_notification(
                                message.channel.id, f"Database error:\n```\n{end}\n```",
                            )

                        for reaction in combos:
                            try:
                                await selector_msg.add_reaction(reaction)

                            except discord.Forbidden:
                                await message.channel.send(
                                    "I don't have permission to react to messages from"
                                    f" the channel {target_channel.mention}."
                                )

                else:
                    await message.channel.send(
                        "You can't use an empty message as a role-reaction message."
                    )


@bot.event
async def on_raw_reaction_add(payload):
    reaction = str(payload.emoji)
    msg_id = payload.message_id
    ch_id = payload.channel_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    exists = db.exists(msg_id)

    if isinstance(exists, Exception):
        await system_notification(
            guild_id,
            f"Database error after a user added a reaction:\n```\n{exists}\n```",
        )

    elif exists:
        # Checks that the message that was reacted to is a reaction-role message managed by the bot
        reactions = db.get_reactions(msg_id)

        if isinstance(reactions, Exception):
            await system_notification(
                guild_id,
                f"Database error when getting reactions:\n```\n{reactions}\n```",
            )
            return

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
                    await system_notification(
                        guild_id,
                        "Someone tried to add a role to themselves but I do not have"
                        " permissions to add it. Ensure that I have a role that is"
                        " hierarchically higher than the role I have to assign, and"
                        " that I have the `Manage Roles` permission.",
                    )


@bot.event
async def on_raw_reaction_remove(payload):
    reaction = str(payload.emoji)
    msg_id = payload.message_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    exists = db.exists(msg_id)

    if isinstance(exists, Exception):
        await system_notification(
            guild_id,
            f"Database error after a user removed a reaction:\n```\n{exists}\n```",
        )

    elif exists:
        # Checks that the message that was unreacted to is a reaction-role message managed by the bot
        reactions = db.get_reactions(msg_id)

        if isinstance(reactions, Exception):
            await system_notification(
                guild_id,
                f"Database error when getting reactions:\n```\n{reactions}\n```",
            )

        elif reaction in reactions:
            role_id = reactions[reaction]
            # Removes role if it has permissions, else 403 error is raised
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=role_id)
            try:
                await member.remove_roles(role)

            except discord.Forbidden:
                await system_notification(
                    guild_id,
                    "Someone tried to remove a role from themselves but I do not have"
                    " permissions to remove it. Ensure that I have a role that is"
                    " hierarchically higher than the role I have to remove, and that I"
                    " have the `Manage Roles` permission.",
                )


@bot.command(name="new")
async def new(ctx):
    if isadmin(ctx.message.author):
        # Starts setup process and the bot starts to listen to the user in that channel
        # For future prompts (see: "async def on_message(message)")
        started = db.start_creation(
            ctx.message.author.id, ctx.message.channel.id, ctx.message.guild.id
        )
        if started:
            await ctx.send("Mention the #channel where to send the auto-role message.")

        else:
            await ctx.send(
                "You are already creating a reaction-role message in this channel. "
                f"Use another channel or run `{prefix}abort` first."
            )

    else:
        await ctx.send(
            f"You do not have an admin role. You might want to use `{prefix}admin`"
            " first."
        )


@bot.command(name="abort")
async def abort(ctx):
    if isadmin(ctx.message.author):
        # Aborts setup process
        aborted = db.abort(ctx.message.author.id, ctx.message.channel.id)
        if aborted:
            await ctx.send("Reaction-role message creation aborted.")

        else:
            await ctx.send(
                "There are no reaction-role message creation processes started by you"
                " in this channel."
            )

    else:
        await ctx.send(f"You do not have an admin role.")


@bot.command(name="edit")
async def edit_selector(ctx):
    if isadmin(ctx.message.author):
        # Reminds user of formatting if it is wrong
        msg_values = ctx.message.content.split()
        if len(msg_values) < 2:
            await ctx.send(
                f"**Type** `{prefix}edit #channelname` to get started. Replace"
                " `#channelname` with the channel where the reaction-role message you"
                " wish to edit is located."
            )
            return

        elif len(msg_values) == 2:
            try:
                channel_id = ctx.message.channel_mentions[0].id

            except IndexError:
                await ctx.send("You need to mention a channel.")
                return

            all_messages = db.fetch_messages(channel_id)

            if isinstance(all_messages, Exception):
                await system_notification(
                    ctx.message.guild.id,
                    f"Database error when fetching messages:\n```\n{all_messages}\n```",
                )
                return

            channel = bot.get_channel(channel_id)
            if len(all_messages) == 1:
                await ctx.send(
                    "There is only one reaction-role message in this channel."
                    f" **Type**:\n```\n{prefix}edit #{channel.name} // 1 // New Message"
                    " // New Embed Title (Optional) // New Embed Description"
                    " (Optional)\n```\nto edit the reaction-role message. You can type"
                    " `none` in any of the argument fields above (e.g. `New Message`)"
                    " to make the bot ignore it."
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
                            "I do not have permissions to edit a reaction-role message"
                            f" that I previously created.\n\nID: {msg_id} in"
                            f" {channel.mention}"
                        )
                        continue
                    entry = (
                        f"`{counter}`"
                        f" {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
                    )
                    selector_msgs.append(entry)
                    counter += 1

                await ctx.send(
                    f"There are **{len(all_messages)}** reaction-role messages in this"
                    f" channel. **Type**:\n```\n{prefix}edit #{channel.name} //"
                    " MESSAGE_NUMBER // New Message // New Embed Title (Optional) //"
                    " New Embed Description (Optional)\n```\nto edit the desired one."
                    " You can type `none` in any of the argument fields above (e.g."
                    " `New Message`) to make the bot ignore it. The list of the"
                    " current reaction-role messages is:\n\n"
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
                all_messages = db.fetch_messages(channel_id)

                if isinstance(all_messages, Exception):
                    await system_notification(
                        ctx.message.guild.id,
                        "Database error when fetching"
                        f" messages:\n```\n{all_messages}\n```",
                    )
                    return

                counter = 1
                if all_messages:
                    message_to_edit_id = None
                    for msg_id in all_messages:
                        # Loop through all msg_ids and stops when the counter matches the user input
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
                        "Select a valid reaction-role message number (i.e. the number"
                        " to the left of the reaction-role message content in the list"
                        " above)."
                    )
                    return

                await old_msg.edit(suppress=False)
                selector_msg_new_body = (
                    msg_values[2] if msg_values[2].lower() != "none" else None
                )
                selector_embed = discord.Embed()

                if len(msg_values) > 3 and msg_values[3].lower() != "none":
                    selector_embed.title = msg_values[3]
                    selector_embed.colour = botcolour

                if len(msg_values) > 4 and msg_values[4].lower() != "none":
                    selector_embed.description = msg_values[4]
                    selector_embed.colour = botcolour

                try:
                    if selector_embed.title or selector_embed.description:
                        await old_msg.edit(
                            content=selector_msg_new_body, embed=selector_embed
                        )

                    else:
                        await old_msg.edit(content=selector_msg_new_body, embed=None)

                    await ctx.send("Message edited.")

                except discord.HTTPException as e:
                    if e.code == 50006:
                        await ctx.send(
                            "You can't use an empty message as role-reaction message."
                        )

                    else:
                        guild_id = ctx.message.guild.id
                        await system_notification(guild_id, str(e))

            except IndexError:
                await ctx.send("The channel you mentioned is invalid.")

            except discord.Forbidden:
                await ctx.send("I do not have permissions to edit the message.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="systemchannel")
async def set_systemchannel(ctx):
    if isadmin(ctx.message.author):
        global system_channel
        msg = ctx.message.content.split()
        mentioned_channels = ctx.message.channel_mentions
        if len(msg) < 3 or not mentioned_channels:
            await ctx.send(
                "Define if you are setting up a server or main system channel and"
                f" mention the target channel.\n```\n{prefix}systemchannel"
                " <main/server> #channelname\n```"
            )

        else:
            target_channel = mentioned_channels[0].id
            guild_id = ctx.message.guild.id

            server = bot.get_guild(guild_id)
            bot_user = server.get_member(bot.user.id)
            bot_permissions = bot.get_channel(system_channel).permissions_for(bot_user)
            writable = bot_permissions.read_messages
            readable = bot_permissions.view_channel
            if not writable or not readable:
                await ctx.send("I cannot read or send messages in that channel.")
                return

            if msg[1].lower() == "main":
                system_channel = target_channel
                config["server"]["system_channel"] = str(system_channel)
                with open(f"{directory}/config.ini", "w") as configfile:
                    config.write(configfile)

            elif msg[1].lower() == "server":
                add_channel = db.add_systemchannel(guild_id, target_channel)

                if isinstance(add_channel, Exception):
                    await system_notification(
                        guild_id,
                        "Database error when adding a new system"
                        f" channel:\n```\n{add_channel}\n```",
                    )

            else:
                await ctx.send(
                    "Define if you are setting up a server or main system channel and"
                    f" mention the target channel.\n```\n{prefix}systemchannel"
                    " <main/server> #channelname\n```"
                )

            await ctx.send("System channel updated.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="colour")
async def set_colour(ctx):
    if isadmin(ctx.message.author):
        msg = ctx.message.content.split()
        args = len(msg) - 1
        if args:
            global botcolour
            colour = msg[1]
            try:
                botcolour = discord.Colour(int(colour, 16))

                config["server"]["colour"] = colour
                with open(f"{directory}/config.ini", "w") as configfile:
                    config.write(configfile)

                example = discord.Embed(
                    title="Example embed",
                    description="This embed has a new colour!",
                    colour=botcolour,
                )
                await ctx.send("Colour changed.", embed=example)

            except ValueError:
                await ctx.send(
                    "Please provide a valid hexadecimal value. Example:"
                    f" `{prefix}colour 0xffff00`"
                )

        else:
            await ctx.send(
                f"Please provide a hexadecimal value. Example: `{prefix}colour"
                " 0xffff00`"
            )


@bot.command(name="help")
async def hlp(ctx):
    if isadmin(ctx.message.author):
        await ctx.send(
            "**Reaction Role Messages**\n"
            f"- `{prefix}new` starts the creation process for a new"
            " reaction role message.\n"
            f"- `{prefix}abort` aborts the creation process"
            " for a new reaction role message started by the command user in that"
            " channel.\n"
            f"- `{prefix}edit` edits an existing reaction-role message or"
            " provides instructions on how to do so if no arguments are passed.\n"
            f"- `{prefix}colour` changes the colour of the embeds of new and newly"
            " edited reaction role messages.\n"
            "**Activities**\n"
            f"- `{prefix}activity` adds an activity for the bot to loop through and"
            " show as status.\n"
            f"- `{prefix}rm-activity` removes an activity from the bot's list.\n"
            f"- `{prefix}activitylist` lists the current activities used by the"
            " bot as statuses.\n"
        )
        await ctx.send(
            "**Admins**\n"
            f"- `{prefix}admin` adds the mentioned role to the list of {botname}"
            " admins, allowing them to create and edit reaction-role messages."
            " You need to be a server administrator to use this command.\n"
            f"- `{prefix}rm-admin` removes the mentioned role from the list of"
            f" {botname} admins, preventing them from creating and editing"
            " reaction-role messages. You need to be a server administrator to"
            " use this command.\n"
            f"- `{prefix}adminlist` lists the current admins on the server the"
            " command was run in by mentioning them and the current admins from"
            " other servers by printing out the role IDs. You need to be a server"
            " administrator to use this command.\n"
            "**System**\n"
            f"- `{prefix}systemchannel` updates the main or server system channel"
            " where the bot sends errors and update notifications.\n"
            "**Bot Control**\n"
            f"- `{prefix}kill` shuts down the bot.\n"
            f"- `{prefix}restart` restarts the bot. Only works on installations"
            " running on GNU/Linux.\n"
            f"- `{prefix}update` updates the bot and restarts it. Only works on"
            " `git clone` installations running on GNU/Linux.\n"
            f"- `{prefix}version` reports the bot's current version and the latest"
            " available one from GitHub.\n\n"
            f"{botname} is running version {__version__} of Reaction Light. You can"
            " find more resources, submit feedback, and report bugs at: "
            "<https://github.com/eibex/reaction-light>"
        )

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="activity")
async def add_activity(ctx):
    if isadmin(ctx.message.author):
        activity = ctx.message.content[(len(prefix) + len("activity")) :].strip()
        if not activity:
            await ctx.send(
                "Please provide the activity you would like to"
                f" add.\n```\n{prefix}activity your activity text here\n```"
            )

        elif "," in activity:
            await ctx.send("Please do not use commas `,` in your activity.")

        else:
            activities.add(activity)
            await ctx.send(f"The activity `{activity}` was added succesfully.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="activitylist")
async def list_activities(ctx):
    if isadmin(ctx.message.author):
        if activities.activity_list:
            formatted_list = []
            for activity in activities.activity_list:
                formatted_list.append(f"`{activity}`")

            await ctx.send(
                "The current activities are:\n- " + "\n- ".join(formatted_list)
            )

        else:
            await ctx.send("There are no activities to show.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="rm-activity")
async def remove_activity(ctx):
    if isadmin(ctx.message.author):
        activity = ctx.message.content[(len(prefix) + len("rm-activity")) :].strip()
        if not activity:
            await ctx.send(
                "Please paste the activity you would like to"
                f" remove.\n```\n{prefix}rm-activity your activity text here\n```"
            )
            return

        removed = activities.remove(activity)
        if removed:
            await ctx.send(f"The activity `{activity}` was removed.")

        else:
            await ctx.send("The activity you mentioned does not exist.")

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="admin")
@commands.has_permissions(administrator=True)
async def add_admin(ctx):
    # Adds an admin role ID to the database
    try:
        role = ctx.message.role_mentions[0].id

    except IndexError:
        try:
            role = int(ctx.message.content.split()[1])

        except ValueError:
            await ctx.send("Please mention a valid @Role or role ID.")
            return

        except IndexError:
            await ctx.send("Please mention a @Role or role ID.")
            return

    add = db.add_admin(role)

    if isinstance(add, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when adding a new admin:\n```\n{add}\n```",
        )
        return

    await ctx.send("Added the role to my admin list.")


@bot.command(name="rm-admin")
@commands.has_permissions(administrator=True)
async def remove_admin(ctx):
    # Removes an admin role ID from the database
    try:
        role = ctx.message.role_mentions[0].id

    except IndexError:
        try:
            role = int(ctx.message.content.split()[1])

        except ValueError:
            await ctx.send("Please mention a valid @Role or role ID.")
            return

        except IndexError:
            await ctx.send("Please mention a @Role or role ID.")
            return

    remove = db.remove_admin(role)

    if isinstance(remove, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when removing an admin:\n```\n{remove}\n```",
        )
        return

    await ctx.send("Removed the role from my admin list.")


@bot.command(name="adminlist")
@commands.has_permissions(administrator=True)
async def list_admin(ctx):
    # Lists all admin IDs in the database, mentioning them if possible
    admin_ids = db.get_admins()

    if isinstance(admin_ids, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when fetching admins:\n```\n{admin_ids}\n```",
        )
        return

    server = bot.get_guild(ctx.message.guild.id)
    local_admins = []
    foreign_admins = []
    for admin_id in admin_ids:
        role = discord.utils.get(server.roles, id=admin_id)
        if role is not None:
            local_admins.append(role.mention)

        else:
            foreign_admins.append(f"`{admin_id}`")

    if local_admins and foreign_admins:
        await ctx.send(
            "The bot admins on this server are:\n- "
            + "\n- ".join(local_admins)
            + "\n\nThe bot admins from other servers are:\n- "
            + "\n- ".join(foreign_admins)
        )

    elif local_admins and not foreign_admins:
        await ctx.send(
            "The bot admins on this server are:\n- "
            + "\n- ".join(local_admins)
            + "\n\nThere are no bot admins from other servers."
        )

    elif not local_admins and foreign_admins:
        await ctx.send(
            "There are no bot admins on this server.\n\nThe bot admins from other"
            " servers are:\n- "
            + "\n- ".join(foreign_admins)
        )

    else:
        await ctx.send("There are no bot admins registered.")


@bot.command(name="version")
async def print_version(ctx):
    if isadmin(ctx.message.author):
        latest = github.get_latest()
        await ctx.send(
            f"I am currently running v{__version__}. The latest available version is"
            f" v{latest}."
        )
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="kill")
async def kill(ctx):
    if isadmin(ctx.message.author):
        await ctx.send("Shutting down...")
        shutdown()  # sys.exit()

    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="restart")
async def restart_cmd(ctx):
    if isadmin(ctx.message.author):
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
    if isadmin(ctx.message.author):
        if platform != "win32":
            await ctx.send("Attempting update...")
            os.chdir(directory)
            cmd = os.popen("git fetch")
            cmd.close()
            cmd = os.popen("git pull")
            cmd.close()
            await ctx.send("Creating database backup...")
            copy(db_file, f"{db_file}.bak")
            restart()
            await ctx.send("Restarting...")
            shutdown()  # sys.exit()

        else:
            await ctx.send("I cannot do this on Windows.")

    else:
        await ctx.send("You do not have an admin role.")


bot.run(TOKEN)
