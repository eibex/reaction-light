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

from sqlite3 import Error as DatabaseError
import disnake
from disnake.ext import commands, tasks
from cogs.utils.i18n import StaticResponse

static_response = StaticResponse()


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pylint: disable=no-member
        # self.maintain_presence.start()

    # @tasks.loop(seconds=30)
    # async def maintain_presence(self):
    #     await self.bot.wait_until_ready()
    #     # Loops through the activities specified in activities.csv
    #     current_activity = self.bot.activities.get()
    #     await self.bot.change_presence(activity=disnake.Game(name=current_activity))

    @commands.slash_command(name="settings")
    async def settings_group(self, inter):
        pass

    @settings_group.sub_command(name="systemchannel", description=static_response.get("brief-settings-systemchannel"))
    @commands.guild_only()
    async def set_systemchannel(
        self,
        inter,
        channel_type: str = commands.Param(
            description=static_response.get("settings-systemchannel-option-type"), choices={"main", "server", "explanation"}
        ),
        channel: disnake.TextChannel = commands.Param(
            description=static_response.get("settings-systemchannel-option-channel"), default=None
        ),
    ):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.send(content=self.bot.response.get("not-admin", guild_id=inter.guild.id))
            return

        await inter.response.defer()
        if not channel or channel_type not in ("main", "server"):
            try:
                server_channel = self.bot.db.fetch_systemchannel(inter.guild.id)
            except DatabaseError as error:
                await self.bot.report(self.bot.response.get("db-error-fetching-systemchannels").format(exception=error))
                return

            if server_channel:
                server_channel = server_channel[0][0]

            main_text = (
                (await self.bot.getchannel(self.bot.config.system_channel)).mention if self.bot.config.system_channel else "none"
            )
            server_text = (await self.bot.getchannel(server_channel)).mention if server_channel else "none"
            await inter.edit_original_message(
                content=self.bot.response.get("systemchannels-info", guild_id=inter.guild.id).format(
                    main_channel=main_text, server_channel=server_text
                )
            )
            return

        bot_user = inter.guild.get_member(self.bot.user.id)
        bot_permissions = channel.permissions_for(bot_user)
        writable = bot_permissions.read_messages
        readable = bot_permissions.view_channel
        if not writable or not readable:
            await inter.edit_original_message(content=self.bot.response.get("permission-error-channel", guild_id=inter.guild.id))
            return

        if channel_type == "main":
            self.bot.config.update("server", "system_channel", str(channel.id))
        elif channel_type == "server":
            try:
                self.bot.db.add_systemchannel(inter.guild.id, channel.id)
            except DatabaseError as error:
                await self.bot.report(
                    self.bot.response.get("db-error-adding-systemchannels", guild_id=inter.guild.id).format(exception=error),
                    inter.guild.id,
                )
                return

        await inter.edit_original_message(content=self.bot.response.get("systemchannels-success", guild_id=inter.guild.id))

    @settings_group.sub_command(name="notify", description=static_response.get("brief-settings-notify"))
    @commands.guild_only()
    async def toggle_notify(self, inter):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            return

        await inter.response.defer()
        try:
            notify = self.bot.db.toggle_notify(inter.guild.id)
        except DatabaseError as error:
            await self.bot.report(
                self.bot.response.get("db-error-toggle-notify", guild_id=inter.guild.id).format(exception=error), inter.guild.id
            )
            return
        if notify:
            await inter.edit_original_message(content=self.bot.response.get("notifications-on", guild_id=inter.guild.id))
        else:
            await inter.edit_original_message(content=self.bot.response.get("notifications-off", guild_id=inter.guild.id))

    @settings_group.sub_command(name="language", description=static_response.get("brief-settings-language"))
    async def set_language(
        self,
        inter,
        _range: str = commands.Param(
            name="range", description=static_response.get("settings-language-option-range"), choices={"global", "server"}
        ),
        language: str = commands.Param(
            description=static_response.get("settings-language-option-language"), choices=static_response.languages()
        ),
    ):
        await inter.response.defer()
        if _range == "server":
            if not inter.guild:
                await inter.send(content=self.bot.response.get("no-dm-parameters").format(parameters="server"))
                return
            # Check admin
            if not self.bot.isadmin(inter.author, inter.guild.id):
                await inter.send(content=self.bot.response.get("not-admin", guild_id=inter.guild.id))
                return
            self.bot.db.set_language(inter.guild.id, language)
        else:
            # Check if bot owner
            if not await self.bot.is_owner(inter.author):
                await inter.send(content=self.bot.response.get("not-owner", guild_id=inter.guild.id if inter.guild else None))
                return

            self.bot.config.update("server", "language", language)
            self.bot.response.global_language = language

        await inter.edit_original_message(content=self.bot.response.get("language-success", guild_id=inter.guild.id if inter.guild else None))

    @commands.is_owner()
    @settings_group.sub_command(name="colour", description=static_response.get("brief-settings-colour"))
    async def set_colour(
        self, inter, colour: str = commands.Param(description=static_response.get("settings-colour-option-colour"))
    ):
        await inter.response.defer()
        guild_id_or_none = inter.guild.id if inter.guild else None
        try:
            self.bot.config.botcolour = disnake.Colour(int(colour, 16))
            self.bot.config.update("server", "colour", colour)
            example = disnake.Embed(
                title=self.bot.response.get("example-embed", guild_id=guild_id_or_none),
                description=self.bot.response.get("example-embed-new-colour", guild_id=guild_id_or_none),
                colour=self.bot.config.botcolour,
            )
            await inter.edit_original_message(
                content=self.bot.response.get("colour-changed", guild_id=guild_id_or_none), embed=example
            )

        except ValueError:
            await inter.edit_original_message(content=self.bot.response.get("colour-hex-error", guild_id=guild_id_or_none))

    @commands.is_owner()
    @settings_group.sub_command(name="activity", description=static_response.get("brief-settings-activity"))
    async def change_activity(
        self,
        inter,
        action: str = commands.Param(
            description=static_response.get("settings-activity-option-action"), choices={"add", "remove", "list"}
        ),
        activity: str = commands.Param(description=static_response.get("settings-activity-option-activity"), default=None),
    ):
        await inter.response.defer()
        guild_id_or_none = inter.guild.id if inter.guild else None
        if action == "add" and activity:
            if "," in activity:
                await inter.send(self.bot.response.get("activity-no-commas", guild_id=guild_id_or_none))

            else:
                self.bot.activities.add(activity)
                await inter.send(self.bot.response.get("activity-success", guild_id=guild_id_or_none).format(new_activity=activity))
        elif action == "list":
            if self.bot.activities.activity_list:
                formatted_list = []
                for item in self.bot.activities.activity_list:
                    formatted_list.append(f"`{item}`")

                await inter.send(
                    self.bot.response.get("current-activities", guild_id=guild_id_or_none).format(
                        activity_list="\n- ".join(formatted_list)
                    )
                )

            else:
                await inter.send(self.bot.response.get("no-current-activities", guild_id=guild_id_or_none))
        elif action == "remove" and activity:
            removed = self.bot.activities.remove(activity)
            if removed:
                await inter.send(
                    self.bot.response.get("rm-activity-success", guild_id=guild_id_or_none).format(activity_to_delete=activity)
                )
            else:
                await inter.send(self.bot.response.get("rm-activity-not-exists", guild_id=guild_id_or_none))
        else:
            await inter.send(self.bot.response.get("activity-add-list-remove", guild_id=guild_id_or_none))


def setup(bot):
    bot.add_cog(Settings(bot))
