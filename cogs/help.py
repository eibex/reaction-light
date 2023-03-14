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
from cogs.utils.i18n import response


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="help", description=response.get("brief-help"))
    async def hlp(self, inter):
        if self.bot.isadmin(inter.author, inter.guild.id):
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
                + response.get("help-footer").format(version=self.bot.version)
            )
        else:
            await inter.send(content=response.get("not-admin"))


def setup(bot):
    bot.add_cog(Help(bot))
