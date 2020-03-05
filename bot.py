import configparser
from sys import platform, exit as shutdown
import os
from itertools import cycle
import csv
import discord
from discord.ext import commands, tasks
from requests import get as requests_get
import rlightfm


# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

__version__ = "0.2.0"

directory = os.path.dirname(os.path.realpath(__file__))
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


def check_for_updates():
    # Get latest version from GitHub repo and checks it against the current one
    latest = (
        requests_get(
            "https://raw.githubusercontent.com/eibex/reaction-light/master/.version"
        )
        .text.lower()
        .rstrip("\n")
    )
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
    maintain_presence.start()
    updates.start()


@bot.event
async def on_message(message):
    if isadmin(message, msg=True):
        user = str(message.author.id)
        channel = str(message.channel.id)
        wizard = rlightfm.get(user, channel)
        step = wizard[0]
        r_id = wizard[1]
        msg = message.content.split()

        if step is not None:  # Checks if the setup process was started before.
            if step == 1:  # If it was not, it ignores the message.
                # The channel the message needs to be sent to is stored
                # Advances to step two
                try:
                    server = bot.get_guild(message.guild.id)
                    bot_user = server.get_member(bot.user.id)
                    ch_id = message.channel_mentions[0].id
                    bot_permissions = bot.get_channel(ch_id).permissions_for(bot_user)
                    writable = bot_permissions.read_messages
                    readable = bot_permissions.view_channel
                    if not writable or not readable:
                        await message.channel.send(
                            "I cannot read or send messages to that channel."
                        )
                        return
                except IndexError:
                    await message.channel.send("The channel you mentioned is invalid.")
                    return

                rlightfm.step1(r_id, ch_id)
                await message.channel.send(
                    "Attach roles and emojis separated by one space (one combination per message). "
                    "When you are done type `done`. Example:\n:smile: `@Role`"
                )
            elif step == 2:
                if msg[0].lower() != "done":
                    # Stores reaction-role combinations until "done" is received
                    try:
                        await message.add_reaction(msg[0])
                        rlightfm.step2(r_id, str(message.role_mentions[0].id), msg[0])
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
                    rlightfm.step2(r_id, None, msg[0], done=True)

                    em = discord.Embed(
                        title="Title", description="Message_content", colour=botcolor
                    )
                    em.set_footer(text="Reaction Light", icon_url=logo)
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
                    em.set_footer(text=f"{botname} - github.com/eibex/reaction-light", icon_url=logo)
                    channel = bot.get_channel(int(rlightfm.getch(r_id)))
                    emb = await channel.send(embed=em)

                    combo = rlightfm.getcombo(r_id)
                    for i in range(len(combo)):
                        if i != 0:
                            # Skips first row as it does not contain reaction/role data
                            await emb.add_reaction(combo[i][0])
                    # Writes CSV name and embed ID to cache.csv and ends process
                    rlightfm.addids(emb.id, r_id)
                    rlightfm.end(r_id)

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    reaction = payload.emoji
    msg_id = payload.message_id
    ch_id = payload.channel_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    r = rlightfm.getids(str(msg_id))
    if r is not None:
        # Checks that the message that was reacted to is an embed managed by the bot
        reactions = rlightfm.getreactions(r)
        ch = bot.get_channel(ch_id)
        msg = await ch.fetch_message(msg_id)
        user = bot.get_user(user_id)
        if str(reaction) not in reactions:
            # Removes reactions added to the embed that are not connected to any role
            await msg.remove_reaction(reaction, user)
        else:
            # Gives role if it has permissions, else 403 error is raised
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=reactions[str(reaction)])
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
    reaction = payload.emoji
    msg_id = payload.message_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    r = rlightfm.getids(str(msg_id))
    if r is not None:
        # Checks that the message that was unreacted to is an embed managed by the bot
        reactions = rlightfm.getreactions(r)
        if str(reaction) in reactions:
            # Removes role if it has permissions, else 403 error is raised
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=reactions[str(reaction)])
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
        rlightfm.listen(ctx.message.author.id, ctx.message.channel.id)
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
                ch_id = ctx.message.channel_mentions[0].id
            except IndexError:
                await ctx.send("The channel you mentioned is invalid.")
                return

            ch = bot.get_channel(ch_id)
            r_ids = rlightfm.edit(ch_id)
            if len(r_ids) == 1:
                await ctx.send(
                    "There is only one embed in this channel. Type "
                    f"`{prefix}edit #channelname // 1 // New Title // New Description` "
                    "to edit the reaction-role message."
                )
            elif len(r_ids) > 1:
                embeds = []
                counter = 1
                for msg_id in r_ids:
                    try:
                        old_msg = await ch.fetch_message(int(msg_id))
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
                    f"There are {len(r_ids)} embeds in this channel. Type "
                    f"`{prefix}edit #channelname // EMBED_NUMBER // New Title // New Description` "
                    "to edit the desired reaction-role message. The list of embeds is:\n"
                    + "\n".join(embeds)
                )
            else:
                await ctx.send("There are no reaction-role messages in that channel.")
        elif len(msg) > 2:
            try:
                # Tries to edit the embed
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                ch_id = ctx.message.channel_mentions[0].id
                ch = bot.get_channel(ch_id)
                msg = ctx.message.content.split(" // ")
                embed_number = msg[1]
                r_ids = rlightfm.edit(ch_id)
                counter = 1

                # Loop through all msg_ids and stops when the counter matches the user input
                if r_ids:
                    to_edit_id = None
                    for msg_id in r_ids:
                        if str(counter) == embed_number:
                            to_edit_id = msg_id
                            break
                        counter += 1
                else:
                    await ctx.send("You selected an embed that does not exist.")
                    return

                if to_edit_id:
                    old_msg = await ch.fetch_message(int(to_edit_id))
                else:
                    await ctx.send(
                        "Select a valid embed number (i.e. the number to the left of the embed title in the list above)."
                    )
                    return

                title = msg[2]
                content = msg[3]
                em = discord.Embed(title=title, description=content, colour=botcolor)
                em.set_footer(text="Reaction Light", icon_url=logo)
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
                await ctx.send("I cannot read or send messages to that channel.")
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
            f"Use `{prefix}new` to start creating a reaction message.\n"
            "Visit <https://github.com/eibex/reaction-light#usage-example> "
            "for a setup walkthrough.\n\nYou can find a list of commands here: "
            "<https://github.com/eibex/reaction-light#commands>"
        )
    else:
        await ctx.send("You do not have an admin role.")


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
        restart()
        await ctx.send("Restarting...")
        shutdown()  # sys.exit()
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="update")
async def update(ctx):
    if isadmin(ctx):
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
        await ctx.send("You do not have an admin role.")


bot.run(TOKEN)
