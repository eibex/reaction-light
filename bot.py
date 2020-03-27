import configparser
from sys import platform, exit as shutdown
import os
from itertools import cycle
import csv
import discord
from discord.ext import commands, tasks
from requests import get as requests_get
import rldb
import migration


# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

directory = os.path.dirname(os.path.realpath(__file__))

migrated = migration.migrate()

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
admin_a = int(config.get("server_role", "admin_a"))
admin_b = int(config.get("server_role", "admin_b"))
admin_c = int(config.get("server_role", "admin_c"))
system_channel = int(config.get("server", "system_channel"))
logo = str(config.get("server", "logo"))
activities = []
activities_file = f"{folder}/activities.csv"
with open(activities_file, "r") as f:
    reader = csv.reader(f, delimiter=",")
    for row in reader:
        activity = row[0]
        activities.append(activity)
activities = cycle(activities)

# Colour palette - changes embeds' sideline colour
botcolor = 0xFFFF00


def isadmin(ctx, msg=False):
    # Checks if command author has one of config.ini admin role IDs
    try:
        check = (
            [role.id for role in ctx.author.roles]
            if msg
            else [role.id for role in ctx.message.author.roles]
        )
        if admin_a in check or admin_b in check or admin_c in check:
            return True
        return False
    except AttributeError:
        # Error raised from 'fake' users, such as webhooks
        return False


def get_latest():
    latest = (
        requests_get(
            "https://raw.githubusercontent.com/eibex/reaction-light/master/.version"
        )
        .text.lower()
        .rstrip("\n")
    )
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
        await channel.send("Your CSV files have been deleted and migrated to an SQLite `reactionlight.db` file.")
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
                    bot_permissions = bot.get_channel(target_channel).permissions_for(bot_user)
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
                    # If "done" is received the combinations are written to CSV
                    # Advances to step three
                    rldb.step2(user, channel, done=True)

                    em = discord.Embed(
                        title="Title", description="Message_content", colour=botcolor
                    )
                    em.set_footer(text=f"{botname}", icon_url=logo)
                    await message.channel.send(
                        "What would you like the message to say? Formatting is: `Title // Message_content`",
                        embed=em,
                    )
            elif step == 3:
                # Receives the title and description of the embed
                # If the formatting is not correct it reminds the user of it
                msg = message.content.split(" // ")
                if len(msg) != 2:
                    await message.channel.send(
                        "Formatting is: `Title // Message_content`"
                    )
                else:
                    title = msg[0]
                    content = msg[1]
                    em = discord.Embed(
                        title=title, description=content, colour=botcolor
                    )
                    em.set_footer(text=f"{botname}", icon_url=logo)
                    target_channel = bot.get_channel(rldb.get_targetchannel(user, channel))

                    emb = None
                    try:
                        emb = await target_channel.send(embed=em)
                    except discord.Forbidden as ef:
                        await message.target_channel.send(
                            "I don't have permission to send embed messages to the channel {0.mention}.".format(target_channel)
                        )

                    if isinstance(emb, discord.Message):
                        combos = rldb.get_combos(user, channel)
                        rldb.end_creation(user, channel, emb.id)
                        for reaction in combos:
                            try:
                                await emb.add_reaction(reaction)
                            except discord.Forbidden:
                                await message.target_channel.send(
                                    "I don't have permission to react to messages in the channel {0.mention}.".format(
                                        target_channel
                                    )
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
        # Checks that the message that was reacted to is an embed managed by the bot
        reactions = rldb.get_reactions(msg_id)
        ch = bot.get_channel(ch_id)
        msg = await ch.fetch_message(msg_id)
        user = bot.get_user(user_id)
        if reaction not in reactions:
            # Removes reactions added to the embed that are not connected to any role
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
        # Checks that the message that was unreacted to is an embed managed by the bot
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
        await ctx.send("You do not have an admin role.")


@bot.command(name="edit")
async def edit_embed(ctx):
    if isadmin(ctx):
        # Reminds user of formatting if it is wrong
        msg = ctx.message.content.split()
        if len(msg) < 2:
            await ctx.send(
                f"Type `{prefix}edit #channelname` to get started. Replace `#channelname` "
                "with the channel where the reaction-role message "
                "you wish to edit is located."
            )
            return
        elif len(msg) == 2:
            try:
                channel_id = ctx.message.channel_mentions[0].id
            except IndexError:
                await ctx.send("You need to mention a channel.")
                return

            all_messages = rldb.fetch_messages(channel_id)
            channel = bot.get_channel(channel_id)
            if len(all_messages) == 1:
                await ctx.send(
                    "There is only one embed in this channel. Type\n"
                    f"```\n{prefix}edit #{channel.name} // 1 // New Title // New Description\n```\n"
                    "to edit the reaction-role message."
                )
            elif len(all_messages) > 1:
                embeds = []
                counter = 1
                for msg_id in all_messages:
                    try:
                        old_msg = await channel.fetch_message(int(msg_id))
                    except discord.NotFound:
                        # Skipping embeds that might have been deleted without updating CSVs
                        continue
                    except discord.Forbidden:
                        ctx.send(
                            "I do not have permissions to edit a reaction-role message that I previously created."
                        )
                        continue
                    entry = f"`{counter}` {old_msg.embeds[0].title}"
                    embeds.append(entry)
                    counter += 1

                await ctx.send(
                    f"There are {len(all_messages)} embeds in this channel. Type\n"
                    f"```\n{prefix}edit #{channel.name} // EMBED_NUMBER // New Title // New Description\n```\n"
                    "to edit the desired reaction-role message. The list of embeds is:\n"
                    + "\n".join(embeds)
                )
            else:
                await ctx.send("There are no reaction-role messages in that channel.")
        elif len(msg) > 2:
            try:
                # Tries to edit the embed
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                channel_id = ctx.message.channel_mentions[0].id
                channel = bot.get_channel(channel_id)
                msg = ctx.message.content.split(" // ")
                try:
                    embed_number = int(msg[1])
                except ValueError:
                    await ctx.send("You need to select an embed by typing its number in the list.")
                    return
                all_messages = rldb.fetch_messages(channel_id)
                try:
                    message_to_edit_id = all_messages[embed_number - 1]
                except IndexError:
                    await ctx.send("You selected an embed that does not exist.")
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))
                else:
                    await ctx.send(
                        "Select a valid embed number (i.e. the number to the left of the embed title in the list above)."
                    )
                    return

                title = msg[2]
                content = msg[3]
                em = discord.Embed(title=title, description=content, colour=botcolor)
                em.set_footer(text=f"{botname}", icon_url=logo)
                await old_msg.edit(embed=em)
                await ctx.send("Message edited.")

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
            f"- `{prefix}edit` edits an existing reaction role message or provides instructions on how to do so if no arguments are passed.\n"
            f"- `{prefix}kill` shuts down the bot.\n"
            f"- `{prefix}systemchannel` updates the system channel where the bot sends errors and update notifications.\n"
            f"- `{prefix}restart` restarts the bot. Only works on installations running on GNU/Linux.\n"
            f"- `{prefix}update` updates the bot and restarts it. Only works on `git clone` installations running on GNU/Linux.\n"
            f"- `{prefix}version` reports the bot's current version and the latest available one from GitHub.\n\n"
            f"{botname} is running version {__version__} of Reaction Light. Find more resources at: <https://github.com/eibex/reaction-light>"
        )
    else:
        await ctx.send("You do not have an admin role.")


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
