"""
MIT License

Copyright (c) 2019-present eibex

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
import traceback
import configparser
import asyncio
from shutil import copy
from sys import platform

import disnake
from disnake.ext import commands, tasks

from core import database, activity, github, schema, i18n


directory = os.path.dirname(os.path.realpath(__file__))

with open(f"{directory}/.version") as f:
    __version__ = f.read().rstrip("\n").rstrip("\r")

folder = f"{directory}/files"
config = configparser.ConfigParser()
config.read(f"{directory}/config.ini")
logo = str(
    config.get(
        "server",
        "logo",
        fallback="https://cdn.discordapp.com/attachments/671738683623473163/693451064904515645/spell_holy_weaponmastery.jpg",
    )
)
TOKEN = str(config.get("server", "token"))
botname = str(config.get("server", "name", fallback="Reaction Light"))
prefix = str(config.get("server", "prefix", fallback="rl!"))
language = str(config.get("server", "language", fallback="en-gb"))
botcolour = disnake.Colour(int(config.get("server", "colour", fallback="0xffff00"), 16))
system_channel = (
    int(config.get("server", "system_channel"))
    if config.get("server", "system_channel")
    else None
)

response = i18n.Response(f"{folder}/i18n", language, prefix)

intents = disnake.Intents.none()
intents.guild_messages = True
intents.guild_reactions = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=prefix,
    intents=intents
)

bot.remove_command("help")


activities_file = f"{directory}/files/activities.csv"
activities = activity.Activities(activities_file)

available_languages = os.listdir(f"{directory}/files/i18n")
available_languages = tuple([i.replace(".json", "") for i in available_languages if i.endswith(".json")])

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
        print(response.get("db-error-admin-check").format(exception=admins))
        return False

    try:
        member_roles = [role.id for role in member.roles]
        return [admin_role for admin_role in admins if admin_role in member_roles]

    except AttributeError:
        # Error raised from 'fake' users, such as webhooks
        return False


# Set of functions to get objects from cache, if not present they are fetched via an API call

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


async def getmember(guild, user_id):
    member = guild.get_member(user_id)
    if not member:
        member = await guild.fetch_member(user_id)

    return member


def restart():
    # Create a new python process of bot.py and stops the current one
    os.chdir(directory)
    python = "python" if platform == "win32" else "python3"
    cmd = os.popen(f"nohup {python} bot.py &")
    cmd.close()


async def database_updates():
    # Handles database schema updates
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
                response.get("db-error-fetching-systemchannels-server").format(
                    exception=server_channel, text=text
                ),
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

            except disnake.Forbidden:
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

        except disnake.NotFound:
            print(response.get("systemchannel-404"))

        except disnake.Forbidden:
            print(response.get("systemchannel-403"))

    else:
        print(text)


async def formatted_channel_list(channel):
    # Returns a formatted numbered list of reaction roles message present in a given channel
    all_messages = db.fetch_messages(channel.id)
    if isinstance(all_messages, Exception):
        await system_notification(
            channel.guild.id,
            response.get("db-error-fetching-messages").format(exception=all_messages),
        )
        return

    formatted_list = []
    counter = 1
    for msg_id in all_messages:
        try:
            old_msg = await channel.fetch_message(int(msg_id))

        except disnake.NotFound:
            # Skipping reaction-role messages that might have been deleted without updating CSVs
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
    current_activity = activities.get()
    await bot.change_presence(activity=disnake.Game(name=current_activity))


@tasks.loop(hours=24)
async def updates():
    # Sends a reminder once a day if there are updates available
    new_version = await github.check_for_updates(__version__)
    if new_version:
        changelog = await github.latest_changelog()
        em = disnake.Embed(
            title=f"Reaction Light v{new_version} - Changes",
            description=changelog,
            colour=botcolour,
        )
        em.set_footer(text=f"{botname}", icon_url=logo)
        await system_notification(
            None,
            response.get("update-notification").format(new_version=new_version),
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
            response.get("db-error-fetching-cleaning").format(exception=messages),
        )
        return

    for message in messages:
        try:
            channel_id = message[1]
            channel = await bot.fetch_channel(channel_id)

            await channel.fetch_message(message[0])

        except disnake.NotFound as e:
            # If unknown channel or unknown message
            if e.code == 10003 or e.code == 10008:
                delete = db.delete(message[0])

                if isinstance(delete, Exception):
                    await system_notification(
                        channel.guild.id,
                        response.get("db-error-fetching-cleaning").format(
                            exception=delete
                        ),
                    )
                    return

                await system_notification(
                    channel.guild.id,
                    response.get("db-message-delete-success").format(
                        message_id=message, channel=channel.mention
                    ),
                )

        except disnake.Forbidden:
            # If we can't fetch the channel due to the bot not being in the guild or permissions we usually cant mention it or get the guilds id using the channels object
            await system_notification(
                message[3],
                response.get("db-forbidden-message").format(
                    message_id=message[0], channel_id=message[1]
                ),
            )

    if isinstance(guilds, Exception):
        await system_notification(
            None,
            response.get("db-error-fetching-cleaning-guild").format(exception=guilds),
        )
        return

    for guild_id in guilds:
        try:
            await bot.fetch_guild(guild_id)
            if guild_id in cleanup_guild_ids:
                db.remove_cleanup_guild(guild_id)

        except disnake.Forbidden:
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
            response.get("db-error-fetching-cleanup-guild").format(
                exception=cleanup_guilds
            ),
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

            except disnake.Forbidden:
                delete = db.remove_guild(guild[0])
                delete2 = db.remove_cleanup_guild(guild[0])
                if isinstance(delete, Exception):
                    await system_notification(
                        None,
                        response.get("db-error-deleting-cleaning-guild").format(
                            exception=delete
                        ),
                    )
                    return

                elif isinstance(delete2, Exception):
                    await system_notification(
                        None,
                        response.get("db-error-deleting-cleaning-guild").format(
                            exception=delete2
                        ),
                    )
                    return


@tasks.loop(hours=6)
async def check_cleanup_queued_guilds():
    # Checks if an unreachable guild has become available again and removes it from the cleanup queue
    cleanup_guild_ids = db.fetch_cleanup_guilds(guild_ids_only=True)
    for guild_id in cleanup_guild_ids:
        try:
            await bot.fetch_guild(guild_id)
            db.remove_cleanup_guild(guild_id)

        except disnake.Forbidden:
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
                guild_id, response.get("db-error-reaction-add").format(exception=exists)
            )

        elif exists:
            # Checks that the message that was reacted to is a reaction-role message managed by the bot
            reactions = db.get_reactions(msg_id)

            if isinstance(reactions, Exception):
                await system_notification(
                    guild_id,
                    response.get("db-error-reaction-get").format(exception=reactions),
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
                guild = await getguild(guild_id)
                member = await getmember(guild, user_id)
                role = disnake.utils.get(guild.roles, id=role_id)
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
                                response.get("db-error-notification-check").format(
                                    exception=notify
                                ),
                            )
                            return

                        if notify:
                            await user.send(
                                response.get("new-role-dm").format(role_name=role.name)
                            )

                    except disnake.Forbidden:
                        await system_notification(
                            guild_id, response.get("permission-error-add")
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
            guild_id, response.get("db-error-reaction-remove").format(exception=exists)
        )

    elif exists:
        # Checks that the message that was unreacted to is a reaction-role message managed by the bot
        reactions = db.get_reactions(msg_id)

        if isinstance(reactions, Exception):
            await system_notification(
                guild_id,
                response.get("db-error-reaction-get").format(exception=reactions),
            )

        elif reaction in reactions:
            role_id = reactions[reaction]
            # Removes role if it has permissions, else 403 error is raised
            guild = await getguild(guild_id)
            member = await getmember(guild, user_id)

            role = disnake.utils.get(guild.roles, id=role_id)
            try:
                await member.remove_roles(role)
                notify = db.notify(guild_id)
                if isinstance(notify, Exception):
                    await system_notification(
                        guild_id,
                        response.get("db-error-notification-check").format(
                            exception=notify
                        ),
                    )
                    return

                if notify:
                    await member.send(
                        response.get("removed-role-dm").format(role_name=role.name)
                    )

            except disnake.Forbidden:
                await system_notification(
                    guild_id, response.get("permission-error-remove")
                )


# Command groups

@bot.slash_command(name="message")
async def message_group(inter):
    pass


@bot.slash_command(name="settings")
async def settings_group(inter):
    pass


@bot.slash_command(name="bot")
async def bot_group(inter):
    pass


@message_group.sub_command(name="new", description=response.get("brief-message-new"))
async def new(inter):
    if isadmin(inter.author, inter.guild.id):
        await inter.send(response.get("new-reactionrole-init"))
        rl_object = {}
        cancelled = False

        def check(message):
            return message.author.id == inter.author.id and message.content != ""

        if not cancelled:
            error_messages = []
            user_messages = []
            sent_reactions_message = await inter.channel.send(
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
                                (await inter.channel.send(response.get("new-reactionrole-error")))
                            )
                            continue

                        if reaction in rl_object["reactions"]:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        response.get("new-reactionrole-already-used")
                                    )
                                )
                            )
                            continue
                        else:
                            try:
                                await reactions_message.add_reaction(reaction)
                                rl_object["reactions"][reaction] = role
                            except disnake.HTTPException:
                                error_messages.append(
                                    (
                                        await inter.channel.send(
                                            response.get("new-reactionrole-emoji-403")
                                        )
                                    )
                                )
                                continue
                    else:
                        break
            except asyncio.TimeoutError:
                await inter.author.send(response.get("new-reactionrole-timeout"))
                cancelled = True
            finally:
                await sent_reactions_message.delete()
                for message in error_messages + user_messages:
                    await message.delete()

        if not cancelled:
            sent_limited_message = await inter.channel.send(
                response.get("new-reactionrole-limit")
            )

            def reaction_check(payload):
                return (
                    payload.member.id == inter.author.id
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
                await inter.author.send(response.get("new-reactionrole-timeout"))
                cancelled = True
            finally:
                await sent_limited_message.delete()

        if not cancelled:
            sent_oldmessagequestion_message = await inter.channel.send(
                response.get("new-reactionrole-old-or-new").format(
                    bot_mention=bot.user.mention
                )
            )

            def reaction_check2(payload):
                return (
                    payload.member.id == inter.author.id
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
                await inter.author.send(response.get("new-reactionrole-timeout"))
                cancelled = True
            finally:
                await sent_oldmessagequestion_message.delete()

        if not cancelled:
            error_messages = []
            user_messages = []
            if rl_object["old_message"]:
                sent_oldmessage_message = await inter.channel.send(
                    response.get("new-reactionrole-which-message").format(
                        bot_mention=bot.user.mention
                    )
                )

                def reaction_check3(payload):
                    return (
                        payload.user_id == inter.author.id
                        and payload.guild_id == inter.guild.id
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
                            except disnake.InvalidData:
                                channel = None
                            except disnake.HTTPException:
                                channel = None

                            if channel is None:
                                raise disnake.NotFound
                            try:
                                message = await channel.fetch_message(
                                    oldmessage_response_payload.message_id
                                )
                            except disnake.HTTPException:
                                raise disnake.NotFound
                            try:
                                await message.add_reaction("👌")
                                await message.remove_reaction("👌", message.guild.me)
                                await message.remove_reaction("🔧", inter.author)
                            except disnake.HTTPException:
                                raise disnake.NotFound
                            if db.exists(message.id):
                                raise ValueError
                            rl_object["message"] = dict(
                                message_id=message.id,
                                channel_id=message.channel.id,
                                guild_id=message.guild.id,
                            )
                            final_message = message
                            break
                        except disnake.NotFound:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        response.get(
                                            "new-reactionrole-permission-error"
                                        ).format(bot_mention=bot.user.mention)
                                    )
                                )
                            )
                        except ValueError:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        response.get("new-reactionrole-already-exists")
                                    )
                                )
                            )
                except asyncio.TimeoutError:
                    await inter.author.send(response.get("new-reactionrole-timeout"))
                    cancelled = True
                finally:
                    await sent_oldmessage_message.delete()
                    for message in error_messages:
                        await message.delete()
            else:
                sent_channel_message = await inter.channel.send(
                    response.get("new-reactionrole-target-channel")
                )
                try:
                    while True:
                        channel_message = await bot.wait_for(
                            "message", timeout=120, check=check
                        )
                        user_messages.append(channel_message)
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
                    await inter.author.send(response.get("new-reactionrole-timeout"))
                    cancelled = True
                finally:
                    await sent_channel_message.delete()
                    for message in error_messages + user_messages:
                        await message.delete()

        if not cancelled and "target_channel" in rl_object:
            error_messages = []
            user_messages = []
            selector_embed = disnake.Embed(
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
                    user_messages.append(message_message)
                    msg_values = message_message.content.split(" // ")
                    # This whole system could also be re-done using wait_for to make the syntax easier for the user
                    # But it would be a breaking change that would be annoying for thoose who have saved their message commands
                    # for editing.
                    selector_msg_body = (
                        msg_values[0] if msg_values[0].lower() != "none" else None
                    )
                    selector_embed = disnake.Embed(colour=botcolour)
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
                        except disnake.Forbidden:
                            error_messages.append(
                                (
                                    await message.channel.send(
                                        response.get(
                                            "new-reactionrole-message-send-permission-error"
                                        ).format(channel_mention=target_channel.mention)
                                    )
                                )
                            )
            except asyncio.TimeoutError:
                await inter.author.send(response.get("new-reactionrole-timeout"))
                cancelled = True
            finally:
                await sent_message_message.delete()
                for message in error_messages + user_messages:
                    await message.delete()

        if not cancelled:
            # Ait we are (almost) all done, now we just need to insert that into the database and add the reactions 💪
            try:
                r = db.add_reaction_role(rl_object)
            except database.DuplicateInstance:
                await inter.channel.send(response.get("new-reactionrole-already-exists"))
                return

            if isinstance(r, Exception):
                await system_notification(
                    inter.guild.id,
                    response.get("db-error-new-reactionrole").format(exception=r),
                )
                return

            for reaction, _ in rl_object["reactions"].items():
                await final_message.add_reaction(reaction)

        await inter.delete_original_message()

        if cancelled:
            await inter.channel.send(response.get("new-reactionrole-cancelled"))
    else:
        await inter.send(response.get("new-reactionrole-noadmin"))


@message_group.sub_command(name="edit", description=response.get("brief-message-edit"))
async def edit_selector(
    inter,
    channel: disnake.TextChannel = commands.Param(
        description=response.get("message-edit-option-channel")
    ),
    number: int = commands.Param(
        description=response.get("message-edit-option-number")
    ),
    message: str = commands.Param(
        description=response.get("message-edit-option-message"),
        default="none"
    ),
    title: str = commands.Param(
        description=response.get("message-edit-option-title"),
        default="none"
    ),
    description: str = commands.Param(
        description=response.get("message-edit-option-description"),
        default="none"
    ),
):
    if isadmin(inter.author, inter.guild.id):
        await inter.response.defer()
        all_messages = await formatted_channel_list(channel)
        if number == 0:
            if len(all_messages) == 1:
                await inter.edit_original_message(
                    content=response.get("edit-reactionrole-one").format(
                        channel_name=channel.name
                    )
                )

            elif len(all_messages) > 1:
                await inter.edit_original_message(
                    content=response.get("edit-reactionrole-instructions").format(
                        num_messages=len(all_messages),
                        channel_name=channel.name,
                        message_list="\n".join(all_messages),
                    )
                )

            else:
                await inter.edit_original_message(content=response.get("no-reactionrole-messages"))

        else:
            try:
                # Tries to edit the reaction-role message
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                all_messages = db.fetch_messages(channel.id)
                message = message if message.lower() != "none" else None
                title = title if title.lower() != "none" else None
                description = description if description.lower() != "none" else None

                if isinstance(all_messages, Exception):
                    await system_notification(
                        inter.guild.id,
                        response.get("db-error-fetching-messages").format(
                            message_ids=all_messages
                        ),
                    )
                    return

                counter = 1
                if all_messages:
                    message_to_edit_id = None
                    for msg_id in all_messages:
                        # Loop through all msg_ids and stops when the counter matches the user input
                        if counter == number:
                            message_to_edit_id = msg_id
                            break

                        counter += 1

                else:
                    await inter.send(response.get("reactionrole-not-exists"))
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))

                else:
                    await inter.send(response.get("select-valid-reactionrole"))
                    return
                await old_msg.edit(suppress=False)
                selector_msg_new_body = message
                selector_embed = disnake.Embed()

                if title:
                    selector_embed.title = title
                    selector_embed.colour = botcolour
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)

                if description:
                    selector_embed.description = description
                    selector_embed.colour = botcolour
                    selector_embed.set_footer(text=f"{botname}", icon_url=logo)

                try:

                    if selector_embed.title or selector_embed.description:
                        await old_msg.edit(
                            content=selector_msg_new_body, embed=selector_embed
                        )

                    else:
                        await old_msg.edit(content=selector_msg_new_body, embed=None)

                    await inter.edit_original_message(content=response.get("message-edited"))

                except disnake.Forbidden:
                    await inter.edit_original_message(content=response.get("other-author-error"))
                    return

                except disnake.HTTPException as e:
                    if e.code == 50006:
                        await inter.edit_original_message(content=response.get("empty-message-error"))

                    else:
                        guild_id = inter.guild.id
                        await system_notification(guild_id, str(e))

            except IndexError:
                await inter.edit_original_message(content=response.get("invalid-target-channel"))

            except disnake.Forbidden:
                await inter.edit_original_message(content=response.get("edit-permission-error"))

    else:
        await inter.send(response.get("not-admin"))


@message_group.sub_command(name="reaction", description=response.get("brief-message-reaction"))
async def edit_reaction(
    inter,
    channel: disnake.TextChannel = commands.Param(
        description=response.get("message-reaction-option-channel")
    ),
    action: str = commands.Param(
        description=response.get("message-reaction-option-action"),
        choices=("add", "remove")
    ),
    number: int = commands.Param(
        description=response.get("message-reaction-option-number")
    ),
    reaction: str = commands.Param(
        description=response.get("message-reaction-option-reaction"),
        default=None
    ),
    role: disnake.Role = commands.Param(
        description=response.get("message-reaction-option-role"),
        default=None
    ),
):
    if isadmin(inter.author, inter.guild.id):
        await inter.response.defer()
        if number == 0 or not reaction:
            all_messages = await formatted_channel_list(channel)
            if len(all_messages) == 1:
                await inter.edit_original_message(
                    content=response.get("reaction-edit-one").format(channel_name=channel.name)
                )
                return

            elif len(all_messages) > 1:
                await inter.edit_original_message(
                    content=response.get("reaction-edit-multi").format(
                        num_messages=len(all_messages),
                        channel_name=channel.name,
                        message_list="\n".join(all_messages),
                    )
                )
                return

            else:
                await inter.edit_original_message(content=response.get("no-reactionrole-messages"))
                return

        if action == "add":
            if not role:
                await inter.edit_original_message(content=response.get("no-role-mentioned"))
                return

        all_messages = db.fetch_messages(channel.id)
        if isinstance(all_messages, Exception):
            await system_notification(
                inter.guild.id,
                response.get("db-error-fetching-messages").format(
                    exception=all_messages
                ),
            )
            return

        counter = 1
        if all_messages:
            message_to_edit_id = None
            for msg_id in all_messages:
                # Loop through all msg_ids and stops when the counter matches the user input
                if counter == number:
                    message_to_edit_id = msg_id
                    break

                counter += 1

        else:
            await inter.edit_original_message(content=response.get("reactionrole-not-exists"))
            return

        if message_to_edit_id:
            message_to_edit = await channel.fetch_message(int(message_to_edit_id))

        else:
            await inter.edit_original_message(content=response.get("select-valid-reactionrole"))
            return

        if action == "add":
            try:
                # Check that the bot can actually use the emoji
                await message_to_edit.add_reaction(reaction)

            except disnake.HTTPException:
                await inter.edit_original_message(content=response.get("new-reactionrole-emoji-403"))
                return

            react = db.add_reaction(message_to_edit.id, role.id, reaction)
            if isinstance(react, Exception):
                await system_notification(
                    inter.guild.id,
                    response.get("db-error-add-reaction").format(
                        channel_mention=message_to_edit.channel.mention, exception=react
                    ),
                )
                return

            if not react:
                await inter.edit_original_message(content=response.get("reaction-edit-already-exists"))
                return

            await inter.edit_original_message(content=response.get("reaction-edit-add-success"))

        elif action == "remove":
            try:
                await message_to_edit.clear_reaction(reaction)

            except disnake.HTTPException:
                await inter.edit_original_message(content=response.get("reaction-edit-invalid-reaction"))
                return

            react = db.remove_reaction(message_to_edit.id, reaction)
            if isinstance(react, Exception):
                await system_notification(
                    inter.guild.id,
                    response.get("db-error-remove-reaction").format(
                        channel_mention=message_to_edit.channel.mention, exception=react
                    ),
                )
                return

            await inter.edit_original_message(content=response.get("reaction-edit-remove-success"))

    else:
        await inter.send(response.get("not-admin"))


@settings_group.sub_command(
    name="systemchannel", description=response.get("brief-settings-systemchannel")
)
async def set_systemchannel(
    inter,
    channel_type: str = commands.Param(
        description=response.get("settings-systemchannel-option-type"),
        choices=("main", "server", "explanation")
    ),
    channel: disnake.TextChannel = commands.Param(
        description=response.get("settings-systemchannel-option-channel"),
        default=None
    ),
):
    if isadmin(inter.author, inter.guild.id):
        global system_channel
        await inter.response.defer()
        if not channel or channel_type not in ("main", "server"):
            server_channel = db.fetch_systemchannel(inter.guild.id)
            if isinstance(server_channel, Exception):
                await system_notification(
                    None,
                    response.get("db-error-fetching-systemchannels").format(
                        exception=server_channel
                    ),
                )
                return

            if server_channel:
                server_channel = server_channel[0][0]

            main_text = (
                (await getchannel(system_channel)).mention if system_channel else "none"
            )
            server_text = (
                (await getchannel(server_channel)).mention if server_channel else "none"
            )
            await inter.edit_original_message(
                content=response.get("systemchannels-info").format(
                    main_channel=main_text, server_channel=server_text
                )
            )
            return

        bot_user = inter.guild.get_member(bot.user.id)
        bot_permissions = channel.permissions_for(bot_user)
        writable = bot_permissions.read_messages
        readable = bot_permissions.view_channel
        if not writable or not readable:
            await inter.edit_original_message(content=response.get("permission-error-channel"))
            return

        if channel_type == "main":
            system_channel = str(channel.id)
            config["server"]["system_channel"] = system_channel
            with open(f"{directory}/config.ini", "w") as configfile:
                config.write(configfile)

        elif channel_type == "server":
            add_channel = db.add_systemchannel(inter.guild.id, channel.id)

            if isinstance(add_channel, Exception):
                await system_notification(
                    inter.guild.id,
                    response.get("db-error-adding-systemchannels").format(
                        exception=add_channel
                    ),
                )
                return

        await inter.edit_original_message(content=response.get("systemchannels-success"))

    else:
        await inter.edit_original_message(content=response.get("not-admin"))


@settings_group.sub_command(name="notify", description=response.get("brief-settings-notify"))
async def toggle_notify(inter):
    if isadmin(inter.author, inter.guild.id):
        await inter.response.defer()
        notify = db.toggle_notify(inter.guild.id)
        if notify:
            await inter.edit_original_message(content=response.get("notifications-on"))
        else:
            await inter.edit_original_message(content=response.get("notifications-off"))


@commands.is_owner()
@settings_group.sub_command(name="language", description=response.get("brief-settings-language"))
async def set_language(
    inter,
    new_language: str = commands.Param(
        name="language",
        description=response.get("settings-language-option-language"),
        choices=available_languages
    ),
):
    await inter.response.defer()
    global language
    global response
    language = new_language
    config["server"]["language"] = language
    with open(f"{directory}/config.ini", "w") as configfile:
        config.write(configfile)
    response.language = language
    await inter.edit_original_message(content=response.get("language-success"))


@commands.is_owner()
@settings_group.sub_command(name="colour", description=response.get("brief-settings-colour"))
async def set_colour(
    inter,
    colour: str = commands.Param(
        description=response.get("settings-colour-option-colour")
    ),
):
    global botcolour
    await inter.response.defer()
    try:
        botcolour = disnake.Colour(int(colour, 16))

        config["server"]["colour"] = colour
        with open(f"{directory}/config.ini", "w") as configfile:
            config.write(configfile)

        example = disnake.Embed(
            title=response.get("example-embed"),
            description=response.get("example-embed-new-colour"),
            colour=botcolour,
        )
        await inter.edit_original_message(content=response.get("colour-changed"), embed=example)

    except ValueError:
        await inter.edit_original_message(content=response.get("colour-hex-error"))


@commands.is_owner()
@settings_group.sub_command(name="activity", description=response.get("brief-settings-activity"))
async def change_activity(
    inter,
    action: str = commands.Param(
        description=response.get("settings-activity-option-action"),
        choices=("add", "remove", "list")
    ),
    activity: str = commands.Param(
        description=response.get("settings-activity-option-activity"),
        default=None
    ),
):
    await inter.response.defer()
    if action == "add" and activity:
        if "," in activity:
            await inter.send(response.get("activity-no-commas"))

        else:
            activities.add(activity)
            await inter.send(
                response.get("activity-success").format(new_activity=activity)
            )

    elif action == "list":
        if activities.activity_list:
            formatted_list = []
            for item in activities.activity_list:
                formatted_list.append(f"`{item}`")

            await inter.send(
                response.get("current-activities").format(
                    activity_list="\n- ".join(formatted_list)
                )
            )

        else:
            await inter.send(response.get("no-current-activities"))

    elif action == "remove" and activity:
        removed = activities.remove(activity)
        if removed:
            await inter.send(
                response.get("rm-activity-success").format(activity_to_delete=activity)
            )

        else:
            await inter.send(response.get("rm-activity-not-exists"))

    else:
        await inter.send(response.get("activity-add-list-remove"))


@bot.slash_command(name="help", description=response.get("brief-help"))
async def hlp(inter):
    if isadmin(inter.author, inter.guild.id):
        await inter.response.defer()
        await inter.edit_original_message(
            content=response.get("help-messages-title")
            + response.get("help-new")
            + response.get("help-edit")
            + response.get("help-reaction")
            + response.get("help-settings-title")
            + response.get("help-notify")
            + response.get("help-colour")
            + response.get("help-activity")
            + response.get("help-systemchannel")
            + response.get("help-language")
            + response.get("help-admins-title")
            + response.get("help-admin")
            + response.get("help-bot-control-title")
            + response.get("help-kill")
            + response.get("help-restart")
            + response.get("help-update")
            + response.get("help-version")
            + response.get("help-footer").format(version=__version__)
        )

    else:
        await inter.edit_original_message(content=response.get("not-admin"))


@bot.slash_command(name="admin", description=response.get("brief-admin"))
@commands.has_permissions(administrator=True)
async def admin(
    inter,
    action: str = commands.Param(description=response.get("admin-option-action"), choices=("add", "remove", "list")),
    role: disnake.Role = commands.Param(
        description=response.get("admin-option-role"),
        default=None
    ),
):
    await inter.response.defer()
    if role is None or action == "list":
        # Lists all admin IDs in the database, mentioning them if possible
        admin_ids = db.get_admins(inter.guild.id)

        if isinstance(admin_ids, Exception):
            await system_notification(
                inter.guild.id,
                response.get("db-error-fetching-admins").format(exception=admin_ids),
            )
            return

        adminrole_objects = []
        for admin_id in admin_ids:
            adminrole_objects.append(
                disnake.utils.get(inter.guild.roles, id=admin_id).mention
            )

        if adminrole_objects:
            await inter.edit_original_message(
                content=response.get("adminlist-local").format(
                    admin_list="\n- ".join(adminrole_objects)
                )
            )
        else:
            await inter.edit_original_message(content=response.get("adminlist-local-empty"))

    elif action == "add":
        # Adds an admin role ID to the database
        add = db.add_admin(role.id, inter.guild.id)

        if isinstance(add, Exception):
            await system_notification(
                inter.guild.id,
                response.get("db-error-admin-add").format(exception=add),
            )
            return

        await inter.edit_original_message(content=response.get("admin-add-success"))

    elif action == "remove":
        # Removes an admin role ID from the database
        remove = db.remove_admin(role.id, inter.guild.id)

        if isinstance(remove, Exception):
            await system_notification(
                inter.guild.id,
                response.get("db-error-admin-remove").format(exception=remove),
            )
            return

        await inter.edit_original_message(content=response.get("admin-remove-success"))


@bot_group.sub_command(name="version", description=response.get("brief-version"))
async def print_version(inter):
    if isadmin(inter.author, inter.guild.id):
        await inter.response.defer()
        latest = await github.get_latest()
        changelog = await github.latest_changelog()
        em = disnake.Embed(
            title=f"Reaction Light v{latest} - Changes",
            description=changelog,
            colour=botcolour,
        )
        em.set_footer(text=f"{botname}", icon_url=logo)
        await inter.edit_original_message(
            content=response.get("version").format(version=__version__, latest_version=latest),
            embed=em,
        )

    else:
        await inter.edit_original_message(content=response.get("not-admin"))


@commands.is_owner()
@bot_group.sub_command(name="kill", description=response.get("brief-kill"))
async def kill(inter):
    await inter.response.defer()
    await inter.edit_original_message(content=response.get("shutdown"))
    await bot.close()


@commands.is_owner()
@bot_group.sub_command(name="restart", description=response.get("brief-restart"))
async def restart_cmd(inter):
    if platform != "win32":
        restart()
        await inter.response.defer()
        await inter.edit_original_message(content=response.get("restart"))
        await bot.close()

    else:
        await inter.send(response.get("windows-error"))


@commands.is_owner()
@bot_group.sub_command(name="update", description=response.get("brief-update"))
async def update(inter):
    if platform != "win32":
        await inter.response.defer()
        await inter.edit_original_message(content=response.get("attempting-update"))
        os.chdir(directory)
        cmd = os.popen("git fetch")
        cmd.close()
        cmd = os.popen("git pull")
        cmd.close()
        await inter.edit_original_message(content=response.get("database-backup"))
        copy(db_file, f"{db_file}.bak")
        restart()
        await inter.edit_original_message(content=response.get("restart"))
        await bot.close()

    else:
        await inter.send(response.get("windows-error"))


@bot.event
async def on_command_error(inter, error):
    if isinstance(error, commands.NotOwner):
        await inter.send(response.get("not-owner"))
    else:
        traceback.print_tb(error.__traceback__)
        print(error)


try:
    bot.run(TOKEN)

except disnake.PrivilegedIntentsRequired:
    print(response.get("login-failure-intents"))

except disnake.errors.LoginFailure:
    print(response.get("login-failure-token"))
