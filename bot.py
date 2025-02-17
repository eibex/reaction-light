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
from sqlite3 import Error as DatabaseError
import disnake
from disnake.ext import commands
from cogs.utils import database, activity, parser, version, schema
from cogs.utils.i18n import Response, StaticResponse
from config import docker


static_response = StaticResponse()

extensions = (
    "cogs.admin",
    "cogs.cleaner",
    "cogs.control",
    "cogs.errors",
    "cogs.help",
    "cogs.message",
    "cogs.ready",
    "cogs.roles",
    "cogs.settings",
)


class ReactionLight(commands.InteractionBot):
    def __init__(self):
        self.directory = os.path.dirname(os.path.realpath(__file__))
        self.config = parser.Config(self.directory)
        self.activities = activity.Activities(f"{self.directory}/files/activities.csv")
        self.db = database.Database(f"{self.directory}/files/reactionlight.db")
        self.version = version.get(self.directory)
        self.response = Response(self, f"{self.directory}/i18n", self.config.language)
        intents = disnake.Intents(message_content=True, guild_messages=True, guild_reactions=True, guilds=True)
        super().__init__(intents=intents)

        for extension in extensions:
            self.load_extension(extension)

    def isadmin(self, member, guild_id):
        # Checks if command author has an admin role that was added with rl!admin
        try:
            admins = self.db.get_admins(guild_id)
        except DatabaseError as error:
            print(self.response.get("db-error-admin-check").format(exception=error))
            return False

        try:
            member_roles = [role.id for role in member.roles]
            return [admin_role for admin_role in admins if admin_role in member_roles]

        except AttributeError:
            # Error raised from 'fake' users, such as webhooks
            return False

    async def database_updates(self):
        # Handles database schema updates
        handler = schema.SchemaHandler(f"{self.directory}/files/reactionlight.db", self)
        if handler.version == 0:
            handler.zero_to_one()
            try:
                messages = self.db.fetch_all_messages()
            except DatabaseError:
                print("Couldn't fetch messages while migrating")
                return

            for message in messages:
                channel_id = message[1]
                channel = await self.getchannel(channel_id)
                try:
                    self.db.add_guild(channel.id, channel.guild.id)
                except DatabaseError:
                    print("Couldn't add guilds while migrating")
                    return

        if handler.version == 1:
            handler.one_to_two()

        if handler.version == 2:
            handler.two_to_three()

        if handler.version == 3:
            handler.three_to_four()

        if handler.version == 4:
            handler.four_to_five()

        if handler.version == 5:
            handler.five_to_six()

    async def report(self, text, guild_id=None, embed=None):
        # Send a message to the system channel (if set)
        if guild_id:
            try:
                server_channel = self.db.fetch_systemchannel(guild_id)
            except DatabaseError as error:
                await self.report(self.response.get("db-error-fetching-systemchannels-server").format(exception=error, text=text))
                return

            if server_channel:
                server_channel = server_channel[0][0]

            if server_channel:
                try:
                    target_channel = await self.getchannel(server_channel)
                    if embed:
                        await target_channel.send(text, embed=embed)
                    else:
                        await target_channel.send(text)
                except disnake.Forbidden:
                    await self.report(text)
            else:
                if embed:
                    await self.report(text, embed=embed)
                else:
                    await self.report(text)
        elif self.config.system_channel:
            try:
                target_channel = await self.getchannel(self.config.system_channel)
                if embed:
                    await target_channel.send(text, embed=embed)
                else:
                    await target_channel.send(text)
            except disnake.NotFound:
                print(self.response.get("systemchannel-404"))
            except disnake.Forbidden:
                print(self.response.get("systemchannel-403"))
        else:
            print(text)

    # Set of functions to get objects from cache, if not present they are fetched via an API call
    async def getchannel(self, channel_id):
        channel = self.get_channel(channel_id)
        if not channel:
            channel = await self.fetch_channel(channel_id)
        return channel

    async def getguild(self, guild_id):
        guild = self.get_guild(guild_id)
        if not guild:
            guild = await self.fetch_guild(guild_id)
        return guild

    async def getuser(self, user_id):
        user = self.get_user(user_id)
        if not user:
            user = await self.fetch_user(user_id)
        return user

    async def getmember(self, guild, user_id):
        member = guild.get_member(user_id)
        if not member:
            member = await guild.fetch_member(user_id)
        return member

docker.setup(os.path.realpath(__file__))

rl = ReactionLight()

try:
    rl.run(rl.config.token, reconnect=True)
except disnake.PrivilegedIntentsRequired:
    print(static_response.get("login-failure-intents"))
except disnake.errors.LoginFailure:
    print(static_response.get("login-failure-token"))
