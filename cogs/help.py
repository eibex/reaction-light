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


from disnake.ext import commands
from cogs.utils.i18n import StaticResponse

static_response = StaticResponse()


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="help", description=static_response.get("brief-help"))
    @commands.guild_only()
    async def hlp(self, inter):
        if self.bot.isadmin(inter.author, inter.guild.id):
            await inter.response.defer()
            await inter.edit_original_message(
                content=self.bot.response.get("help-messages-title", guild_id=inter.guild.id)
                + self.bot.response.get("help-new", guild_id=inter.guild.id)
                + self.bot.response.get("help-edit", guild_id=inter.guild.id)
                + self.bot.response.get("help-reaction", guild_id=inter.guild.id)
                + self.bot.response.get("help-settings-title", guild_id=inter.guild.id)
                + self.bot.response.get("help-notify", guild_id=inter.guild.id)
                + self.bot.response.get("help-colour", guild_id=inter.guild.id)
                + self.bot.response.get("help-activity", guild_id=inter.guild.id)
                + self.bot.response.get("help-systemchannel", guild_id=inter.guild.id)
                + self.bot.response.get("help-language", guild_id=inter.guild.id)
                + self.bot.response.get("help-admins-title", guild_id=inter.guild.id)
                + self.bot.response.get("help-admin", guild_id=inter.guild.id)
                + self.bot.response.get("help-bot-control-title", guild_id=inter.guild.id)
                + self.bot.response.get("help-kill", guild_id=inter.guild.id)
                + self.bot.response.get("help-restart", guild_id=inter.guild.id)
                + self.bot.response.get("help-update", guild_id=inter.guild.id)
                + self.bot.response.get("help-version", guild_id=inter.guild.id)
                + self.bot.response.get("help-footer", guild_id=inter.guild.id).format(version=self.bot.version)
            )
        else:
            await inter.send(content=self.bot.response.get("not-admin", guild_id=inter.guild.id))


def setup(bot):
    bot.add_cog(Help(bot))
