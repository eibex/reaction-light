import configparser
from sys import exit as shutdown
from os import path
from itertools import cycle
import csv
import discord
from discord.ext import commands, tasks
from requests import get as requests_get
import rlightfm


# Original Repository: https://github.com/eibex/reaction-light
__author__ = "eibex"
__version__ = "0.0.6"
__license__ = "MIT"

directory = path.dirname(path.realpath(__file__))
folder = "{}/files".format(directory)
config = configparser.ConfigParser()
config.read("{}/config.ini".format(directory))

TOKEN = str(config.get("server", "token"))

prefix = str(config.get("server", "prefix"))

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
activities_file = "{}/activities.csv".format(folder)
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
            "An update is available. Download Reaction Light v{} at https://github.com/eibex/reaction-light "
            "or simply use `git pull origin master` on your server".format(new_version)
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
                        await message.channel.send("I cannot read or send messages to that channel.")
                        return
                except IndexError:
                    await message.channel.send("The channel you mentioned is invalid.")
                    return
                rlightfm.step1(r_id, ch_id)
                await message.channel.send(
                    "Attach roles and emojis separated by a space (one combination per message). "
                    "When you are done type `done`. Example:\n:smile: `@Role`"
                )
            elif step == 2:
                if msg[0].lower() != "done":
                    # Stores reaction-role combinations until "done" is received
                    rlightfm.step2(r_id, str(message.role_mentions[0].id), msg[0])
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
                    em.set_footer(text="Reaction Light", icon_url=logo)
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
        await ctx.send(
            "Please mention the #channel where to send the auto-role message."
        )
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="edit")
async def edit_embed(ctx):
    if isadmin(ctx):
        # Reminds user of formatting if it is wrong
        msg = ctx.message.content.split()
        if len(msg) < 2:
            await ctx.send(
                "Type `{}edit #channelname` to get started. Replace `#channelname` "
                "with the channel where the reaction-role message "
                "you wish to edit is located.".format(prefix)
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
                    "`{}edit #channelname // 1 // New Title // New Description` "
                    "to edit the reaction-role message.".format(prefix)
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
                        ctx.send("I do not have permissions to edit a reaction-role message that I previously created.")
                        continue
                    entry = "{}. {}".format(counter, old_msg.embeds[0].title)
                    embeds.append(entry)
                    counter += 1
                await ctx.send(
                    "There are {} embeds in this channel. Type "
                    "`{}edit #channelname // EMBED_NUMBER // New Title // New Description` "
                    "to edit the desired reaction-role message. The list of embeds is:\n".format(len(r_ids), prefix)
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
                    await ctx.send("Select a valid embed number (i.e. the number to the left of the embed title in the list above).")
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


@bot.command(name="help")
async def hlp(ctx):
    if isadmin(ctx):
        await ctx.send(
            "Use `{}new` to start creating a reaction message.\n"
            "Visit <https://github.com/eibex/reaction-light/blob/master/README.md#example> "
            "for a setup walkthrough.".format(prefix)
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


bot.run(TOKEN)
