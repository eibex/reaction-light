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

import disnake
from disnake.ext import commands, tasks
from cogs.utils.i18n import response


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.maintain_presence.start()

    @tasks.loop(seconds=30)
    async def maintain_presence(self):
        await self.bot.wait_until_ready()
        # Loops through the activities specified in activities.csv
        current_activity = self.bot.activities.get()
        await self.bot.change_presence(activity=disnake.Game(name=current_activity))

    @commands.slash_command(name="settings")
    async def settings_group(self, inter):
        pass

    @settings_group.sub_command(name="systemchannel", description=response.get("brief-settings-systemchannel"))
    async def set_systemchannel(
        self,
        inter,
        channel_type: str = commands.Param(
            description=response.get("settings-systemchannel-option-type"), choices=("main", "server", "explanation")
        ),
        channel: disnake.TextChannel = commands.Param(
            description=response.get("settings-systemchannel-option-channel"), default=None
        ),
    ):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.send(content=response.get("not-admin"))
            return

        await inter.response.defer()
        if not channel or channel_type not in ("main", "server"):
            server_channel = self.bot.db.fetch_systemchannel(inter.guild.id)
            if isinstance(server_channel, Exception):
                await self.bot.report(response.get("db-error-fetching-systemchannels").format(exception=server_channel))
                return

            if server_channel:
                server_channel = server_channel[0][0]

            main_text = (
                (await self.bot.getchannel(self.bot.config.system_channel)).mention if self.bot.config.system_channel else "none"
            )
            server_text = (await self.bot.getchannel(server_channel)).mention if server_channel else "none"
            await inter.edit_original_message(
                content=response.get("systemchannels-info").format(main_channel=main_text, server_channel=server_text)
            )
            return

        bot_user = inter.guild.get_member(self.bot.user.id)
        bot_permissions = channel.permissions_for(bot_user)
        writable = bot_permissions.read_messages
        readable = bot_permissions.view_channel
        if not writable or not readable:
            await inter.edit_original_message(content=response.get("permission-error-channel"))
            return

        if channel_type == "main":
            self.bot.config.update("server", "system_channel", str(channel.id))
        elif channel_type == "server":
            add_channel = self.bot.db.add_systemchannel(inter.guild.id, channel.id)

            if isinstance(add_channel, Exception):
                await self.bot.report(response.get("db-error-adding-systemchannels").format(exception=add_channel), inter.guild.id)
                return

        await inter.edit_original_message(content=response.get("systemchannels-success"))

    @settings_group.sub_command(name="notify", description=response.get("brief-settings-notify"))
    async def toggle_notify(self, inter):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            return

        await inter.response.defer()
        notify = self.bot.db.toggle_notify(inter.guild.id)
        if notify:
            await inter.edit_original_message(content=response.get("notifications-on"))
        else:
            await inter.edit_original_message(content=response.get("notifications-off"))

    @commands.is_owner()
    @settings_group.sub_command(name="language", description=response.get("brief-settings-language"))
    async def set_language(
        self,
        inter,
        language: str = commands.Param(
            description=response.get("settings-language-option-language"), choices=response.languages()
        ),
    ):
        await inter.response.defer()
        self.bot.config.update("server", "language", language)
        response.language = language
        await inter.edit_original_message(content=response.get("language-success"))

    @commands.is_owner()
    @settings_group.sub_command(name="colour", description=response.get("brief-settings-colour"))
    async def set_colour(self, inter, colour: str = commands.Param(description=response.get("settings-colour-option-colour"))):
        await inter.response.defer()
        try:
            self.bot.config.botcolour = disnake.Colour(int(colour, 16))
            self.bot.config.update("server", "colour", colour)
            example = disnake.Embed(
                title=response.get("example-embed"),
                description=response.get("example-embed-new-colour"),
                colour=self.bot.config.botcolour,
            )
            await inter.edit_original_message(content=response.get("colour-changed"), embed=example)

        except ValueError:
            await inter.edit_original_message(content=response.get("colour-hex-error"))

    @commands.is_owner()
    @settings_group.sub_command(name="activity", description=response.get("brief-settings-activity"))
    async def change_activity(
        self,
        inter,
        action: str = commands.Param(
            description=response.get("settings-activity-option-action"), choices=("add", "remove", "list")
        ),
        activity: str = commands.Param(description=response.get("settings-activity-option-activity"), default=None),
    ):
        await inter.response.defer()
        if action == "add" and activity:
            if "," in activity:
                await inter.send(response.get("activity-no-commas"))

            else:
                self.bot.activities.add(activity)
                await inter.send(response.get("activity-success").format(new_activity=activity))
        elif action == "list":
            if self.bot.activities.activity_list:
                formatted_list = []
                for item in self.bot.activities.activity_list:
                    formatted_list.append(f"`{item}`")

                await inter.send(response.get("current-activities").format(activity_list="\n- ".join(formatted_list)))

            else:
                await inter.send(response.get("no-current-activities"))
        elif action == "remove" and activity:
            removed = self.bot.activities.remove(activity)
            if removed:
                await inter.send(response.get("rm-activity-success").format(activity_to_delete=activity))
            else:
                await inter.send(response.get("rm-activity-not-exists"))
        else:
            await inter.send(response.get("activity-add-list-remove"))


def setup(bot):
    bot.add_cog(Settings(bot))
