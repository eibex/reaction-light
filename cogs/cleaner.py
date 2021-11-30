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

from datetime import datetime
import disnake
from disnake.ext import commands, tasks
from cogs.utils.i18n import response


class Cleaner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleandb.start()
        self.check_cleanup_queued_guilds.start()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.bot.db.add_cleanup_guild(guild.id, round(datetime.utcnow().timestamp()))

    @tasks.loop(hours=24)
    async def cleandb(self):
        await self.bot.wait_until_ready()
        # Cleans the database by deleting rows of reaction role messages that don't exist anymore
        messages = self.bot.db.fetch_all_messages()
        guilds = self.bot.db.fetch_all_guilds()
        # Get the cleanup queued guilds
        cleanup_guild_ids = self.bot.db.fetch_cleanup_guilds(guild_ids_only=True)

        if isinstance(messages, Exception):
            await self.bot.system_notification(None, response.get("db-error-fetching-cleaning").format(exception=messages))
            return

        for message in messages:
            try:
                channel_id = message[1]
                channel = await self.bot.fetch_channel(channel_id)

                await channel.fetch_message(message[0])

            except disnake.NotFound as e:
                # If unknown channel or unknown message
                if e.code == 10003 or e.code == 10008:
                    delete = self.bot.db.delete(message[0])

                    if isinstance(delete, Exception):
                        await self.bot.system_notification(
                            channel.guild.id, response.get("db-error-fetching-cleaning").format(exception=delete)
                        )
                        return

                    await self.bot.system_notification(
                        channel.guild.id,
                        response.get("db-message-delete-success").format(message_id=message, channel=channel.mention),
                    )
            except disnake.Forbidden:
                # If we can't fetch the channel due to the bot not being in the guild or permissions we usually cant mention it or get the guilds id using the channels object
                await self.bot.system_notification(
                    message[3], response.get("db-forbidden-message").format(message_id=message[0], channel_id=message[1])
                )

        if isinstance(guilds, Exception):
            await self.bot.system_notification(None, response.get("db-error-fetching-cleaning-guild").format(exception=guilds))
            return

        for guild_id in guilds:
            try:
                await self.bot.fetch_guild(guild_id)
                if guild_id in cleanup_guild_ids:
                    self.bot.db.remove_cleanup_guild(guild_id)
            except disnake.Forbidden:
                # If unknown guild
                if guild_id in cleanup_guild_ids:
                    continue
                else:
                    self.bot.db.add_cleanup_guild(guild_id, round(datetime.utcnow().timestamp()))

        cleanup_guilds = self.bot.db.fetch_cleanup_guilds()

        if isinstance(cleanup_guilds, Exception):
            await self.bot.system_notification(
                None, response.get("db-error-fetching-cleanup-guild").format(exception=cleanup_guilds)
            )
            return

        current_timestamp = round(datetime.utcnow().timestamp())

        for guild in cleanup_guilds:
            if int(guild[1]) - current_timestamp <= -86400:
                # The guild has been invalid / unreachable for more than 24 hrs, try one more fetch then give up and purge the guilds database entries
                try:
                    await self.bot.fetch_guild(guild[0])
                    self.bot.db.remove_cleanup_guild(guild[0])
                    continue
                except disnake.Forbidden:
                    delete = self.bot.db.remove_guild(guild[0])
                    delete2 = self.bot.db.remove_cleanup_guild(guild[0])
                    if isinstance(delete, Exception):
                        await self.bot.system_notification(
                            None, response.get("db-error-deleting-cleaning-guild").format(exception=delete)
                        )
                        return
                    elif isinstance(delete2, Exception):
                        await self.bot.system_notification(
                            None, response.get("db-error-deleting-cleaning-guild").format(exception=delete2)
                        )
                        return

    @tasks.loop(hours=6)
    async def check_cleanup_queued_guilds(self):
        await self.bot.wait_until_ready()
        # Checks if an unreachable guild has become available again and removes it from the cleanup queue
        cleanup_guild_ids = self.bot.db.fetch_cleanup_guilds(guild_ids_only=True)
        for guild_id in cleanup_guild_ids:
            try:
                await self.bot.fetch_guild(guild_id)
                self.bot.db.remove_cleanup_guild(guild_id)

            except disnake.Forbidden:
                continue


def setup(bot):
    bot.add_cog(Cleaner(bot))
