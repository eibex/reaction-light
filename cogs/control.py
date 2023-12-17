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
from sys import platform
from shutil import copy
import disnake
from disnake.ext import commands, tasks
from cogs.utils import github
from cogs.utils.i18n import StaticResponse

static_response = StaticResponse()


class Control(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # pylint: disable=no-member
        self.updates.start()

    def restart(self):
        # Create a new python process of bot.py and stops the current one
        os.chdir(self.bot.directory)
        python = "python" if platform == "win32" else "python3"
        cmd = os.popen(f"nohup {python} bot.py &")
        cmd.close()

    @tasks.loop(hours=24)
    async def updates(self):
        await self.bot.wait_until_ready()
        # Sends a reminder once a day if there are updates available
        new_version = await github.check_for_updates(self.bot.version)

        if new_version:
            changelog = await github.latest_changelog()
            em = disnake.Embed(
                title=f"Reaction Light v{new_version} - Changes", description=changelog, colour=self.bot.config.botcolour
            )
            em.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)
            await self.bot.report(self.bot.response.get("update-notification").format(new_version=new_version), embed=em)

    @commands.slash_command(name="bot")
    async def controlbot_group(self, inter):
        pass

    @controlbot_group.sub_command(name="version", description=static_response.get("brief-version"))
    @commands.guild_only()
    async def print_version(self, inter):
        await inter.response.defer()
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.edit_original_message(content=self.bot.response.get("not-admin", guild_id=inter.guild.id))
            return

        latest = await github.get_latest()
        changelog = await github.latest_changelog()
        em = disnake.Embed(title=f"Reaction Light v{latest} - Changes", description=changelog, colour=self.bot.config.botcolour)
        em.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)
        await inter.edit_original_message(
            content=self.bot.response.get("version", guild_id=inter.guild.id).format(
                version=self.bot.version, latest_version=latest
            ),
            embed=em,
        )

    @commands.is_owner()
    @controlbot_group.sub_command(name="kill", description=static_response.get("brief-kill"))
    async def kill(self, inter):
        await inter.response.defer()
        await inter.edit_original_message(content=self.bot.response.get("shutdown", guild_id=inter.guild.id))
        await self.bot.close()

    @commands.is_owner()
    @controlbot_group.sub_command(name="restart", description=static_response.get("brief-restart"))
    async def restart_cmd(self, inter):
        if platform != "win32":
            self.restart()
            await inter.response.defer()
            await inter.edit_original_message(content=self.bot.response.get("restart", guild_id=inter.guild.id))
            await self.bot.close()
        else:
            await inter.send(self.bot.response.get("windows-error", guild_id=inter.guild.id))

    @commands.is_owner()
    @controlbot_group.sub_command(name="update", description=static_response.get("brief-update"))
    async def update(self, inter):
        if platform != "win32":
            await inter.response.defer()
            await inter.edit_original_message(content=self.bot.response.get("attempting-update", guild_id=inter.guild.id))
            os.chdir(self.bot.directory)
            cmd = os.popen("git fetch")
            cmd.close()
            cmd = os.popen("git pull")
            cmd.close()
            await inter.channel.send(self.bot.response.get("database-backup", guild_id=inter.guild.id))
            copy(f"{self.bot.directory}/files/reactionlight.db", f"{self.bot.directory}/files/reactionlight.db.bak")
            self.restart()
            await inter.channel.send(self.bot.response.get("restart", guild_id=inter.guild.id))
            await self.bot.close()
        else:
            await inter.send(self.bot.response.get("windows-error", guild_id=inter.guild.id))


def setup(bot):
    bot.add_cog(Control(bot))
