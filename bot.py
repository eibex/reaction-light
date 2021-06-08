"""
MIT License

Copyright (c) 2019-2021 eibex

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
import datetime
import configparser
import asyncio
from shutil import copy
from sys import platform, exit as shutdown

import discord
from discord.ext import commands, tasks

from core import database, activity, github, schema, i18n


directory = os.path.dirname(os.path.realpath(__file__))

with open(f"{directory}/.version") as f:
    __version__ = f.read().rstrip("\n").rstrip("\r")

folder = f"{directory}/files"
config = configparser.ConfigParser()
config.read(f"{directory}/config.ini")
logo = str(config.get("server", "logo"))
TOKEN = str(config.get("server", "token"))
botname = str(config.get("server", "name"))
prefix = str(config.get("server", "prefix"))
language = str(config.get("server", "language"))
botcolour = discord.Colour(int(config.get("server", "colour"), 16))
system_channel = (
    int(config.get("server", "system_channel"))
    if config.get("server", "system_channel")
    else None
)

response = i18n.Response(f"{folder}/i18n", language, prefix)

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.messages = True
intents.emojis = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

bot.remove_command("help")

activities_file = f"{directory}/files/activities.csv"
activities = activity.Activities(activities_file)
db_file = f"{directory}/files/reactionlight.db"
db = database.Database(db_file)


class Locks:
    def __init__(self):
        self.locks = {}
        self.main_lock = asyncio.Lock()

    async def get_lock(self, user_id):
        async with self.main_lock:
            if not user_id in self.locks:
                self.locks[user_id] = asyncio.Lock()

            return self.locks[user_id]


lock_manager = Locks()


def isadmin(member, guild_id):
    # Checks if command author has an admin role that was added with rl!admin
    admins = db.get_admins(guild_id)

    if isinstance(admins, Exception):
        print(f"Error when checking if the member is an admin:\n{admins}")
        return False

    try:
        member_roles = [role.id for role in member.roles]
        return [admin_role for admin_role in admins if admin_role in member_roles]

    except AttributeError:
        # Error raised from 'fake' users, such as webhooks
        return False


async def getchannel(channel_id):
    channel = bot.get_channel(channel_id)

    if not channel:
        channel = await bot.fetch_channel(channel_id)

    return channel


async def getguild(guild_id):
    guild = bot.get_guild(guild_id)

    if not guild:
        guild = await bot.fetch_guild(guild_id)

    return guild


async def getuser(user_id):
    user = bot.get_user(user_id)

    if not user:
        user = await bot.fetch_user(user_id)

    return user


def restart():
    # Create a new python process of bot.py and stops the current one
    os.chdir(directory)
    python = "python" if platform == "win32" else "python3"
    cmd = os.popen(f"nohup {python} bot.py &")
    cmd.close()


async def database_updates():
    handler = schema.SchemaHandler(db_file, bot)
    if handler.version == 0:
        handler.zero_to_one()
        messages = db.fetch_all_messages()
        for message in messages:
            channel_id = message[1]
            channel = await getchannel(channel_id)
            db.add_guild(channel.id, channel.guild.id)

    if handler.version == 1:
        handler.one_to_two()

    if handler.version == 2:
        handler.two_to_three()


async def system_notification(guild_id, text, embed=None):
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
            server_channel = server_channel[0][0]

        if server_channel:
            try:
                target_channel = await getchannel(server_channel)
                if embed:
                    await target_channel.send(text, embed=embed)
                else:
                    await target_channel.send(text)

            except discord.Forbidden:
                await system_notification(None, text)

        else:
            if embed:
                await system_notification(None, text, embed=embed)
            else:
                await system_notification(None, text)

    elif system_channel:
        try:
            target_channel = await getchannel(system_channel)
            if embed:
                await target_channel.send(text, embed=embed)
            else:
                await target_channel.send(text)

        except discord.NotFound:
            print("I cannot find the system channel.")

        except discord.Forbidden:
            print("I cannot send messages to the system channel.")

    else:
        print(text)


async def formatted_channel_list(channel):
    all_messages = db.fetch_messages(channel.id)
    if isinstance(all_messages, Exception):
        await system_notification(
            channel.guild.id,
            f"Database error when fetching messages:\n```\n{all_messages}\n```",
        )
        return

    formatted_list = []
    counter = 1
    for msg_id in all_messages:
        try:
            old_msg = await channel.fetch_message(int(msg_id))

        except discord.NotFound:
            # Skipping reaction-role messages that might have been deleted without updating CSVs
            continue

        except discord.Forbidden:
            await system_notification(
                channel.guild.id,
                "I do not have permissions to edit a reaction-role message"
                f" that I previously created.\n\nID: {msg_id} in"
                f" {channel.mention}",
            )
            continue

        entry = (
            f"`{counter}`"
            f" {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
        )
        formatted_list.append(entry)
        counter += 1

    return formatted_list


@tasks.loop(seconds=30)
async def maintain_presence():
    # Loops through the activities specified in activities.csv
    activity = activities.get()
    await bot.change_presence(activity=discord.Game(name=activity))


@tasks.loop(hours=24)
async def updates():
    # Sends a reminder once a day if there are updates available
    new_version = await github.check_for_updates(__version__)
    if new_version:
        changelog = await github.latest_changelog()
        em = discord.Embed(
            title=f"Reaction Light v{new_version} - Changes",
            description=changelog,
            colour=botcolour,
        )
        em.set_footer(text=f"{botname}", icon_url=logo)
        await system_notification(
            None,
            response.get("update-notification").format(new_version),
            embed=em,
        )


@tasks.loop(hours=24)
async def cleandb():
    # Cleans the database by deleting rows of reaction role messages that don't exist anymore
    messages = db.fetch_all_messages()
    guilds = db.fetch_all_guilds()
    # Get the cleanup queued guilds
    cleanup_guild_ids = db.fetch_cleanup_guilds(guild_ids_only=True)

    if isinstance(messages, Exception):
        await system_notification(
            None,
            response.get("db-error-fetching-cleaning").format(messages),
        )
        return

    for message in messages:
        try:
            channel_id = message[1]
            channel = await bot.fetch_channel(channel_id)

            await channel.fetch_message(message[0])

        except discord.NotFound as e:
            # If unknown channel or unknown message
            if e.code == 10003 or e.code == 10008:
                delete = db.delete(message[0], message[3])

                if isinstance(delete, Exception):
                    await system_notification(
                        channel.guild.id,
                        response.get("db-error-fetching-cleaning").format(delete),
                    )
                    return

                await system_notification(
                    channel.guild.id,
                    response.get("db-message-delete-success").format(message, channel.mention),
                )

        except discord.Forbidden:
            # If we can't fetch the channel due to the bot not being in the guild or permissions we usually cant mention it or get the guilds id using the channels object
            await system_notification(
                message[3],
                response.get("db-forbidden-message").format(message[0], message[1]),
            )

    if isinstance(guilds, Exception):
        await system_notification(
            None,
            response.get("db-error-fetching-cleaning-guild").format(guilds)
        )
        return

    for guild_id in guilds:
        try:
            await bot.fetch_guild(guild_id)
            if guild_id in cleanup_guild_ids:
                db.remove_cleanup_guild(guild_id)

        except discord.Forbidden:
            # If unknown guild
            if guild_id in cleanup_guild_ids:
                continue
            else:
                db.add_cleanup_guild(
                    guild_id, round(datetime.datetime.utcnow().timestamp())
                )

    cleanup_guilds = db.fetch_cleanup_guilds()

    if isinstance(cleanup_guilds, Exception):
        await system_notification(
            None,
            response.get("db-error-fetching-cleanup-guild").format(cleanup_guilds)
        )
        return

    current_timestamp = round(datetime.datetime.utcnow().timestamp())
    for guild in cleanup_guilds:
        if int(guild[1]) - current_timestamp <= -86400:
            # The guild has been invalid / unreachable for more than 24 hrs, try one more fetch then give up and purge the guilds database entries
            try:
                await bot.fetch_guild(guild[0])
                db.remove_cleanup_guild(guild[0])
                continue

            except discord.Forbidden:
                delete = db.remove_guild(guild[0])
                delete2 = db.remove_cleanup_guild(guild[0])
                if isinstance(delete, Exception):
                    await system_notification(
                        None,
                        response.get("db-error-deleting-cleaning-guild").format(delete),
                    )
                    return

                elif isinstance(delete2, Exception):
                    await system_notification(
                        None,
                        response.get("db-error-deleting-cleaning-guild").format(delete2),
                    )
                    return


@tasks.loop(hours=6)
async def check_cleanup_queued_guilds():
    cleanup_guild_ids = db.fetch_cleanup_guilds(guild_ids_only=True)
    for guild_id in cleanup_guild_ids:
        try:
            await bot.fetch_guild(guild_id)
            db.remove_cleanup_guild(guild_id)

        except discord.Forbidden:
            continue


@bot.event
async def on_ready():
    print("Reaction Light ready!")
    await database_updates()
    maintain_presence.start()
    cleandb.start()
    check_cleanup_queued_guilds.start()
    updates.start()


@bot.event
async def on_guild_remove(guild):
    db.remove_guild(guild.id)


@bot.event
async def on_message(message):
    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    reaction = str(payload.emoji)
    msg_id = payload.message_id
    ch_id = payload.channel_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    exists = db.exists(msg_id)

    async with (await lock_manager.get_lock(user_id)):
        if isinstance(exists, Exception):
            await system_notification(
                guild_id,
                response.get("db-error-reaction-add").format(exists)
            )

        elif exists:
            # Checks that the message that was reacted to is a reaction-role message managed by the bot
            reactions = db.get_reactions(msg_id)

            if isinstance(reactions, Exception):
                await system_notification(
                    guild_id,
                    response.get("db-error-reaction-get").format(reactions)
                )
                return

            ch = await getchannel(ch_id)
            msg = await ch.fetch_message(msg_id)
            user = await getuser(user_id)
            if reaction not in reactions:
                # Removes reactions added to the reaction-role message that are not connected to any role
                await msg.remove_reaction(reaction, user)

            else:
                # Gives role if it has permissions, else 403 error is raised
                role_id = reactions[reaction]
                server = await getguild(guild_id)
                member = server.get_member(user_id)
                role = discord.utils.get(server.roles, id=role_id)
                if user_id != bot.user.id:
                    unique = db.isunique(msg_id)
                    if unique:
                        for existing_reaction in msg.reactions:
                            if str(existing_reaction.emoji) == reaction:
                                continue
                            async for reaction_user in existing_reaction.users():
                                if reaction_user.id == user_id:
                                    await msg.remove_reaction(existing_reaction, user)
                                    # We can safely break since a user can only have one reaction at once
                                    break

                    try:
                        await member.add_roles(role)
                        notify = db.notify(guild_id)
                        if isinstance(notify, Exception):
                            await system_notification(
                                guild_id,
                                response.get("db-error-notification-check").format(notify)
                            )
                            return

                        if notify:
                            await user.send(
                                response.get("new-role-dm").format(role.name)
                            )

                    except discord.Forbidden:
                        await system_notification(
                            guild_id,
                            response.get("permission-error-add")
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
            response.get("db-error-reaction-remove").format(exists)
        )

    elif exists:
        # Checks that the message that was unreacted to is a reaction-role message managed by the bot
        reactions = db.get_reactions(msg_id)

        if isinstance(reactions, Exception):
            await system_notification(
                guild_id,
                response.get("db-error-reaction-get").format(reactions)
            )

        elif reaction in reactions:
            role_id = reactions[reaction]
            # Removes role if it has permissions, else 403 error is raised
            server = await getguild(guild_id)
            member = server.get_member(user_id)

            if not member:
                member = await server.fetch_member(user_id)

            role = discord.utils.get(server.roles, id=role_id)
            try:
                await member.remove_roles(role)
                notify = db.notify(guild_id)
                if isinstance(notify, Exception):
                    await system_notification(
                        guild_id,
                        response.get("db-error-notification-check").format(notify)
                    )
                    return

                if notify:
                    await member.send(
                        response.get("removed-role-dm").format(role.name)
                    )

            except discord.Forbidden:
                await system_notification(
                    guild_id,
                    response.get("permission-error-remove")
                )


@bot.command(name="new", aliases=["create"])
async def new(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        sent_initial_message = await ctx.send(
            response.get("new-reactionrole-init")
        )
        rl_object = {}
        cancelled = False

        def check(message):
            return message.author.id == ctx.message.author.id and message.content != ""

        if not cancelled:
            error_messages = []
            user_messages = []
            sent_reactions_message = await ctx.send(
                response.get("new-reactionrole-roles-emojis")
            )
            rl_object["reactions"] = {}
            try:
                while True:
                    reactions_message = await bot.wait_for(
                        "message", timeout=120, check=check
                    )
                    user_messages.append(reactions_message)
                    if reactions_message.content.lower() != "done":
                        reaction = (reactions_message.content.split())[0]
                        try:
                            role = reactions_message.role_mentions[0].id
                        except IndexError:
                            error_messages.append(
                                (
                                    await ctx.send(
                                        response.get("new-reactionrole-error")
                                    )
                                )
                            )
                            continue

                        if reaction in rl_object["reactions"]:
                            error_messages.append(
                                (
                                    await ctx.send(
                                        response.get("new-reactionrole-already-used")
                                    )
                                )
                            )
                            continue
                        else:
                            try:
                                await reactions_message.add_reaction(reaction)
                                rl_object["reactions"][reaction] = role
                            except discord.HTTPException:
                                error_messages.append(
                                    (
                                        await ctx.send(
                                            response.get("new-reactionrole-emoji-403")
                                        )
                                    )
                                )
                                continue
                    else:
                        break
            except asyncio.TimeoutError:
                await ctx.author.send(
                    response.get("new-reactionrole-timeout")
                )
                cancelled = True
            finally:
                await sent_reactions_message.delete()
                for message in error_messages + user_messages:
                    await message.delete()

        if not cancelled:
            sent_limited_message = await ctx.send(
                response.get("new-reactionrole-limit")
            )

            def reaction_check(payload):
                return (
                    payload.member.id == ctx.message.author.id
                    and payload.message_id == sent_limited_message.id
                    and (str(payload.emoji) == "🔒" or str(payload.emoji) == "♾️")
                )

            try:
                await sent_limited_message.add_reaction("🔒")
                await sent_limited_message.add_reaction("♾️")
                limited_message_response_payload = await bot.wait_for(
                    "raw_reaction_add", timeout=120, check=reaction_check
                )

                if str(limited_message_response_payload.emoji) == "🔒":
                    rl_object["limit_to_one"] = 1
                else:
                    rl_object["limit_to_one"] = 0
            except asyncio.TimeoutError:
                await ctx.author.send(
                    response.get("new-reactionrole-timeout")
                )
                cancelled = True
            finally:
                await sent_limited_message.delete()

        if not cancelled:
            sent_oldmessagequestion_message = await ctx.send(
                response.get("new-reactionrole-old-or-new").format(bot.user.mention)
            )

            def reaction_check2(payload):
                return (
                    payload.member.id == ctx.message.author.id
                    and payload.message_id == sent_oldmessagequestion_message.id
                    and (str(payload.emoji) == "🗨️" or str(payload.emoji) == "🤖")
                )

            try:
                await sent_oldmessagequestion_message.add_reaction("🗨️")
                await sent_oldmessagequestion_message.add_reaction("🤖")
                oldmessagequestion_response_payload = await bot.wait_for(
                    "raw_reaction_add", timeout=120, check=reaction_check2
                )

                if str(oldmessagequestion_response_payload.emoji) == "🗨️":
                    rl_object["old_message"] = True
                else:
                    rl_object["old_message"] = False
            except asyncio.TimeoutError:
                await ctx.author.send(
                    response.get("new-reactionrole-timeout")
                )
                cancelled = True
            finally:
                await sent_oldmessagequestion_message.delete()

        if not cancelled:
            error_messages = []
            user_messages = []
            if rl_object["old_message"]:
                sent_oldmessage_message = await ctx.send(
                    response.get("new-reactionrole-which-message").format(bot.user.mention)
                )

                def reaction_check3(payload):
                    return (
                        payload.member.id == ctx.message.author.id
                        and payload.guild_id == sent_oldmessage_message.guild.id
                        and str(payload.emoji) == "🔧"
                    )

                try:
                    while True:
                        oldmessage_response_payload = await bot.wait_for(
                            "raw_reaction_add", timeout=120, check=reaction_check3
                        )
                        try:
                            try:
                                channel = await getchannel(
                                    oldmessage_response_payload.channel_id
                                )
                            except discord.InvalidData:
                                channel = None
                            except discord.HTTPException:
                                channel = None

                            if channel is None:
                                raise discord.NotFound
                            try:
                                message = await channel.fetch_message(
                                    oldmessage_response_payload.message_id
                                )
                            except discord.HTTPException:
                                raise discord.NotFound
                            try:
                                await message.add_reaction("👌")
                                await message.remove_reaction("👌", message.guild.me)
                                await message.remove_reaction("🔧", ctx.author)
                            except discord.HTTPException:
                                raise discord.NotFound
                            if db.exists(message.id):
                                raise ValueError
                            rl_object["message"] = dict(
                                message_id=message.id,
                                channel_id=message.channel.id,
                                guild_id=message.guild.id,
                            )
                            final_message = message
                            break
                        except discord.NotFound:
                            error_messages.append(
                                (
                                    await ctx.send(
                                        response.get("new-reactionrole-permission-error").format(bot.user.mention)
                                    )
                                )
                            )
                        except ValueError:
                            error_messages.append(
                                (
                                    await ctx.send(
                                        response.get("new-reactionrole-already-exists")
                                    )
                                )
                            )
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        response.get("new-reactionrole-timeout")
                    )
                    cancelled = True
                finally:
                    await sent_oldmessage_message.delete()
                    for message in error_messages:
                        await message.delete()
            else:
                sent_channel_message = await ctx.send(
                    response.get("new-reactionrole-target-channel")
                )
                try:
                    while True:
                        channel_message = await bot.wait_for(
                            "message", timeout=120, check=check
                        )
                        if channel_message.channel_mentions:
                            rl_object[
                                "target_channel"
                            ] = channel_message.channel_mentions[0]
                            break
                        else:
                            error_messages.append(
                                (
                                    await message.channel.send(
                                        response.get("invalid-target-channel")
                                    )
                                )
                            )
                except asyncio.TimeoutError:
                    await ctx.author.send(
                        response.get("new-reactionrole-timeout")
                    )
                    cancelled = True
                finally:
                    await sent_channel_message.delete()
                    for message in error_messages:
                        await message.delete()

        if not cancelled and "target_channel" in rl_object:
            error_messages = []
            selector_embed = discord.Embed(
                title="Embed_title",
                description="Embed_content",
                colour=botcolour,
            )
            selector_embed.set_footer(text=f"{botname}", icon_url=logo)

            sent_message_message = await message.channel.send(
                response.get("new-reactionrole-message-contents"),
                embed=selector_embed,
            )
            try:
                while True:
                    message_message = await bot.wait_for(
                        "message", timeout=120, check=check
                    )
                    # I would usually end up deleting message_message in the end but users usually want to be able to access the
                    # format they once used incase they want to make any minor changes
                    msg_values = message_message.content.split(" // ")
                    # This whole system could also be re-done using wait_for to make the syntax easier for the user
                    # But it would be a breaking change that would be annoying for thoose who have saved their message commands
                    # for editing.
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
                        target_channel = rl_object["target_channel"]
                        sent_final_message = None
                        try:
                            sent_final_message = await target_channel.send(
                                content=selector_msg_body, embed=selector_embed
                            )
                            rl_object["message"] = dict(
                                message_id=sent_final_message.id,
                                channel_id=sent_final_message.channel.id,
                                guild_id=sent_final_message.guild.id,
                            )
                            final_message = sent_final_message
                            break
                        except discord.Forbidden:
                            error_messages.append(
                                (
                                    await message.channel.send(
                                        response.get("new-reactionrole-message-send-permission-error").format(target_channel.mention)
                                    )
                                )
                            )
            except asyncio.TimeoutError:
                await ctx.author.send(
                    response.get("new-reactionrole-timeout")
                )
                cancelled = True
            finally:
                await sent_message_message.delete()
                for message in error_messages:
                    await message.delete()

        if not cancelled:
            # Ait we are (almost) all done, now we just need to insert that into the database and add the reactions 💪
            try:
                r = db.add_reaction_role(rl_object)
            except database.DuplicateInstance:
                await ctx.send(
                    response.get("new-reactionrole-already-exists")
                )
                return

            if isinstance(r, Exception):
                await system_notification(
                    ctx.message.guild.id,
                    response.get("db-error-new-reactionrole").format(r)
                )
                return
            for reaction, _ in rl_object["reactions"].items():
                await final_message.add_reaction(reaction)
            await ctx.message.add_reaction("✅")
        await sent_initial_message.delete()

        if cancelled:
            await ctx.message.add_reaction("❌")
    else:
        await ctx.send(
            response.get("new-reactionrole-noadmin")
        )


@bot.command(name="edit")
async def edit_selector(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        # Reminds user of formatting if it is wrong
        msg_values = ctx.message.content.split()
        if len(msg_values) < 2:
            await ctx.send(
                response.get("edit-reactionrole-info")
            )
            return

        elif len(msg_values) == 2:
            try:
                channel_id = ctx.message.channel_mentions[0].id

            except IndexError:
                await ctx.send(response.get("edit-reactionrole-nochannel"))
                return

            channel = await getchannel(channel_id)
            all_messages = await formatted_channel_list(channel)
            if len(all_messages) == 1:
                await ctx.send(
                    response.get("edit-reactionrole-one").format(channel.name)
                )

            elif len(all_messages) > 1:
                await ctx.send(
                    response.get("edit-reactionrole-instructions").format(len(all_messages), channel.name) + "\n".join(all_messages)
                )

            else:
                await ctx.send(response.get("no-reactionrole-messages"))

        elif len(msg_values) > 2:
            try:
                # Tries to edit the reaction-role message
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                channel_id = ctx.message.channel_mentions[0].id
                channel = await getchannel(channel_id)
                msg_values = ctx.message.content.split(" // ")
                selector_msg_number = msg_values[1]
                all_messages = db.fetch_messages(channel_id)

                if isinstance(all_messages, Exception):
                    await system_notification(
                        ctx.message.guild.id,
                        response.get("db-error-fetching-messages").format(all_messages)
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
                         response.get("reactionrole-not-exists")
                    )
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))

                else:
                    await ctx.send(
                        response.get("select-valid-reactionrole")
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
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)

                if len(msg_values) > 4 and msg_values[4].lower() != "none":
                    selector_embed.description = msg_values[4]
                    selector_embed.colour = botcolour
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)

                try:
                    if selector_embed.title or selector_embed.description:
                        await old_msg.edit(
                            content=selector_msg_new_body, embed=selector_embed
                        )

                    else:
                        await old_msg.edit(content=selector_msg_new_body, embed=None)

                    await ctx.send(response.get("message-edited"))
                except discord.Forbidden:
                    await ctx.send(
                        response.get("other-author-error")
                    )
                    return
                except discord.HTTPException as e:
                    if e.code == 50006:
                        await ctx.send(
                            response.get("empty-message-error")
                        )

                    else:
                        guild_id = ctx.message.guild.id
                        await system_notification(guild_id, str(e))

            except IndexError:
                await ctx.send(response.get("invalid-target-channel"))

            except discord.Forbidden:
                await ctx.send(response.get("edit-permission-error"))

    else:
        await ctx.send(response.get("not-admin"))


@bot.command(name="reaction")
async def edit_reaction(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        msg_values = ctx.message.content.split()
        mentioned_roles = ctx.message.role_mentions
        mentioned_channels = ctx.message.channel_mentions
        if len(msg_values) < 4:
            if not mentioned_channels:
                await ctx.send(
                    response.get("reaction-edit-info")
                )
                return

            channel = ctx.message.channel_mentions[0]
            all_messages = await formatted_channel_list(channel)
            if len(all_messages) == 1:
                await ctx.send(
                    response.get("reaction-edit-one").format(channel.name)
                )
                return

            elif len(all_messages) > 1:
                await ctx.send(
                    response.get("reaction-edit-multi").format(len(all_messages), channel.name) + "\n".join(all_messages)
                )
                return

            else:
                await ctx.send(response.get("no-reactionrole-messages"))
                return

        action = msg_values[1].lower()
        channel = ctx.message.channel_mentions[0]
        message_number = msg_values[3]
        reaction = msg_values[4]
        if action == "add":
            if mentioned_roles:
                role = mentioned_roles[0]
            else:
                await ctx.send(response.get("no-role-mentioned"))
                return

        all_messages = db.fetch_messages(channel.id)
        if isinstance(all_messages, Exception):
            await system_notification(
                ctx.message.guild.id,
                f"Database error when fetching messages:\n```\n{all_messages}\n```",
            )
            return

        counter = 1
        if all_messages:
            message_to_edit_id = None
            for msg_id in all_messages:
                # Loop through all msg_ids and stops when the counter matches the user input
                if str(counter) == message_number:
                    message_to_edit_id = msg_id
                    break

                counter += 1

        else:
            await ctx.send("You selected a reaction-role message that does not exist.")
            return

        if message_to_edit_id:
            message_to_edit = await channel.fetch_message(int(message_to_edit_id))

        else:
            await ctx.send(
                "Select a valid reaction-role message number (i.e. the number"
                " to the left of the reaction-role message content in the list"
                " above)."
            )
            return

        if action == "add":
            try:
                # Check that the bot can actually use the emoji
                await message_to_edit.add_reaction(reaction)

            except discord.HTTPException:
                await ctx.send(
                    "You can only use reactions uploaded to servers the bot has access"
                    " to or standard emojis."
                )
                return

            react = db.add_reaction(message_to_edit.id, role.id, reaction)
            if isinstance(react, Exception):
                await system_notification(
                    ctx.message.guild.id,
                    "Database error when adding a reaction to a message in"
                    f" {message_to_edit.channel.mention}:\n```\n{react}\n```",
                )
                return

            if not react:
                await ctx.send(
                    "That message already has a reaction-role combination with"
                    " that reaction."
                )
                return

            await ctx.send("Reaction added.")

        elif action == "remove":
            try:
                await message_to_edit.clear_reaction(reaction)

            except discord.HTTPException:
                await ctx.send("Invalid reaction.")
                return

            react = db.remove_reaction(message_to_edit.id, reaction)
            if isinstance(react, Exception):
                await system_notification(
                    ctx.message.guild.id,
                    "Database error when adding a reaction to a message in"
                    f" {message_to_edit.channel.mention}:\n```\n{react}\n```",
                )
                return

            await ctx.send("Reaction removed.")

    else:
        await ctx.send(response.get("not-admin"))


@bot.command(name="systemchannel")
async def set_systemchannel(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        global system_channel
        msg = ctx.message.content.split()
        mentioned_channels = ctx.message.channel_mentions
        channel_type = None if len(msg) < 2 else msg[1].lower()
        if (
            len(msg) < 3
            or not mentioned_channels
            or channel_type not in ["main", "server"]
        ):
            server_channel = db.fetch_systemchannel(ctx.guild.id)
            if isinstance(server_channel, Exception):
                await system_notification(
                    None,
                    "Database error when fetching guild system"
                    f" channels:\n```\n{server_channel}\n```",
                )
                return

            if server_channel:
                server_channel = server_channel[0][0]

            main_text = (await getchannel(system_channel)).mention if system_channel else 'none'
            server_text = (await getchannel(server_channel)).mention if server_channel else 'none'
            await ctx.send(
                "Define if you are setting up a server or main system channel and"
                f" mention the target channel.\n```\n{prefix}systemchannel"
                " <main/server> #channelname\n```\nThe server system channel"
                " reports errors and notifications related to this server only,"
                " while the main system channel is used as a fall-back and for"
                " bot-wide errors and notifications.\n\nThe current channels are:\n"
                f"**Main:** {main_text}\n"
                f"**Server:** {server_text}"
            )
            return

        target_channel = mentioned_channels[0].id
        guild_id = ctx.message.guild.id

        server = await getguild(guild_id)
        bot_user = server.get_member(bot.user.id)
        bot_permissions = (await getchannel(target_channel)).permissions_for(bot_user)
        writable = bot_permissions.read_messages
        readable = bot_permissions.view_channel
        if not writable or not readable:
            await ctx.send("I cannot read or send messages in that channel.")
            return

        if channel_type == "main":
            system_channel = target_channel
            config["server"]["system_channel"] = str(system_channel)
            with open(f"{directory}/config.ini", "w") as configfile:
                config.write(configfile)

        elif channel_type == "server":
            add_channel = db.add_systemchannel(guild_id, target_channel)

            if isinstance(add_channel, Exception):
                await system_notification(
                    guild_id,
                    "Database error when adding a new system"
                    f" channel:\n```\n{add_channel}\n```",
                )
                return

        await ctx.send("System channel updated.")

    else:
        await ctx.send(response.get("not-admin"))


@bot.command(name="notify")
async def toggle_notify(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        notify = db.toggle_notify(ctx.guild.id)
        if notify:
            await ctx.send(
                "Notifications have been set to **ON** for this server.\n"
                "Use this command again to turn them off."
            )
        else:
            await ctx.send(
                "Notifications have been set to **OFF** for this server.\n"
                "Use this command again to turn them on."
            )


@commands.is_owner()
@bot.command(name="colour")
async def set_colour(ctx):
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
            f"Please provide a hexadecimal value. Example: `{prefix}colour" " 0xffff00`"
        )


@commands.is_owner()
@bot.command(name="activity")
async def add_activity(ctx):
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


@commands.is_owner()
@bot.command(name="activitylist")
async def list_activities(ctx):
    if activities.activity_list:
        formatted_list = []
        for activity in activities.activity_list:
            formatted_list.append(f"`{activity}`")

        await ctx.send("The current activities are:\n- " + "\n- ".join(formatted_list))

    else:
        await ctx.send("There are no activities to show.")


@commands.is_owner()
@bot.command(name="rm-activity")
async def remove_activity(ctx):
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


@bot.command(name="help")
async def hlp(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        await ctx.send(
            "**Reaction Role Messages**\n"
            f"- `{prefix}new` starts the creation process for a new"
            " reaction role message.\n"
            f"- `{prefix}edit` edits the text and embed of an existing reaction"
            " role message.\n"
            f"- `{prefix}reaction` adds or removes a reaction from an existing"
            " reaction role message.\n"
            f"- `{prefix}notify` toggles sending messages to users when they get/lose"
            " a role (default off) for the current server (the command affects only"
            " the server it was used in).\n"
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
        await ctx.send(response.get("not-admin"))


@bot.command(pass_context=True, name="admin")
@commands.has_permissions(administrator=True)
async def add_admin(ctx, role: discord.Role):
    # Adds an admin role ID to the database
    add = db.add_admin(role.id, ctx.guild.id)

    if isinstance(add, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when adding a new admin:\n```\n{add}\n```",
        )
        return

    await ctx.send("Added the role to my admin list.")


@add_admin.error
async def add_admin_error(ctx, error):
    if isinstance(error, commands.RoleNotFound):
        await ctx.send("Please mention a valid @Role or role ID.")


@bot.command(name="rm-admin")
@commands.has_permissions(administrator=True)
async def remove_admin(ctx, role: discord.Role):
    # Removes an admin role ID from the database
    remove = db.remove_admin(role.id, ctx.guild.id)

    if isinstance(remove, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when removing an admin:\n```\n{remove}\n```",
        )
        return

    await ctx.send("Removed the role from my admin list.")


@remove_admin.error
async def remove_admin_error(ctx, error):
    if isinstance(error, commands.RoleNotFound):
        await ctx.send("Please mention a valid @Role or role ID.")


@bot.command(name="adminlist")
@commands.has_permissions(administrator=True)
async def list_admin(ctx):
    # Lists all admin IDs in the database, mentioning them if possible
    admin_ids = db.get_admins(ctx.guild.id)

    if isinstance(admin_ids, Exception):
        await system_notification(
            ctx.message.guild.id,
            f"Database error when fetching admins:\n```\n{admin_ids}\n```",
        )
        return

    adminrole_objects = []
    for admin_id in admin_ids:
        adminrole_objects.append(
            discord.utils.get(ctx.guild.roles, id=admin_id).mention
        )

    if adminrole_objects:
        await ctx.send(
            "The bot admins on this server are:\n- " + "\n- ".join(adminrole_objects)
        )
    else:
        await ctx.send("There are no bot admins registered in this server.")


@bot.command(name="version")
async def print_version(ctx):
    if isadmin(ctx.message.author, ctx.guild.id):
        latest = await github.get_latest()
        changelog = await github.latest_changelog()
        em = discord.Embed(
            title=f"Reaction Light v{latest} - Changes",
            description=changelog,
            colour=botcolour,
        )
        em.set_footer(text=f"{botname}", icon_url=logo)
        await ctx.send(
            f"I am currently running Reaction Light **v{__version__}**. The latest"
            f" available version is **v{latest}**.",
            embed=em,
        )

    else:
        await ctx.send(response.get("not-admin"))


@commands.is_owner()
@bot.command(name="kill")
async def kill(ctx):
    await ctx.send("Shutting down...")
    shutdown()  # sys.exit()


@commands.is_owner()
@bot.command(name="restart")
async def restart_cmd(ctx):
    if platform != "win32":
        restart()
        await ctx.send("Restarting...")
        shutdown()  # sys.exit()

    else:
        await ctx.send("I cannot do this on Windows.")


@commands.is_owner()
@bot.command(name="update")
async def update(ctx):
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


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("Only the bot owner may execute this command.")


try:
    bot.run(TOKEN)

except discord.PrivilegedIntentsRequired:
    print(
        "[Login Failure] You need to enable the server members intent on the Discord Developers Portal."
    )

except discord.errors.LoginFailure:
    print("[Login Failure] The token inserted in config.ini is invalid.")
