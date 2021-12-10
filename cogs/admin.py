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
from disnake.ext import commands
from cogs.utils.i18n import response


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="admin", description=response.get("brief-admin"))
    @commands.has_permissions(administrator=True)
    async def admin(
        self,
        inter,
        action: str = commands.Param(description=response.get("admin-option-action"), choices=("add", "remove", "list")),
        role: disnake.Role = commands.Param(description=response.get("admin-option-role"), default=None),
    ):
        await inter.response.defer()
        if role is None or action == "list":
            # Lists all admin IDs in the database, mentioning them if possible
            try:
                admin_ids = self.bot.db.get_admins(inter.guild.id)
            except DatabaseError as error:
                await self.bot.report(response.get("db-error-fetching-admins").format(exception=error), inter.guild.id)
                return

            adminrole_objects = []
            for admin_id in admin_ids:
                adminrole_objects.append(disnake.utils.get(inter.guild.roles, id=admin_id).mention)

            if adminrole_objects:
                await inter.edit_original_message(
                    content=response.get("adminlist-local").format(admin_list="\n- ".join(adminrole_objects))
                )
            else:
                await inter.edit_original_message(content=response.get("adminlist-local-empty"))

        elif action == "add":
            # Adds an admin role ID to the database
            try:
                self.bot.db.add_admin(role.id, inter.guild.id)
            except DatabaseError as error:
                await self.bot.report(response.get("db-error-admin-add").format(exception=error), inter.guild.id)
                return

            await inter.edit_original_message(content=response.get("admin-add-success"))

        elif action == "remove":
            # Removes an admin role ID from the database
            try:
                self.bot.db.remove_admin(role.id, inter.guild.id)
            except DatabaseError as error:
                await self.bot.report(response.get("db-error-admin-remove").format(exception=error), inter.guild.id)
                return

            await inter.edit_original_message(content=response.get("admin-remove-success"))


def setup(bot):
    bot.add_cog(Admin(bot))
