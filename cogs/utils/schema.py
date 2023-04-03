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


import sqlite3
import disnake

from cogs.utils.sanitizing import sanitize_emoji


class SchemaHandler:
    def __init__(self, database, client):
        self.database = database
        self.client = client
        self.version = self.version_check()

    def version_check(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM dbinfo;")
        version = cursor.fetchall()
        cursor.close()
        conn.close()
        if not version:
            self.set_version(0)
            return 0

        version = version[0][0]
        return version

    def set_version(self, version):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        if version > 0:
            previous = version - 1
            cursor.execute("UPDATE dbinfo SET version = ? WHERE version = ?;", (version, previous))

        else:
            cursor.execute("INSERT INTO dbinfo(version) values(?);", (version,))

        conn.commit()
        cursor.close()
        conn.close()
        self.version = version

    def zero_to_one(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "guild_id" not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN 'guild_id' INT;")
            conn.commit()

        cursor.close()
        conn.close()
        self.set_version(1)

    def one_to_two(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(admins);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "guild_id" not in columns:
            cursor.execute("SELECT role_id FROM admins")
            admins = cursor.fetchall()
            admins2 = []
            for admin in admins:
                admins2.append(admin[0])
            admins = admins2
            guilds = {}
            for guild in self.client.guilds:
                guilds[guild.id] = []
                for admin_id in admins:
                    role = disnake.utils.get(guild.roles, id=admin_id)
                    if role is not None:
                        guilds[guild.id].append(role.id)

            cursor.execute("ALTER TABLE admins ADD COLUMN 'guild_id' INT;")
            conn.commit()
            for guild in guilds:
                for admin_id in guilds[guild]:
                    cursor.execute("UPDATE admins SET guild_id = ? WHERE role_id = ?;", (guild, admin_id))
            cursor.execute("DELETE FROM admins WHERE guild_id IS NULL;")
            conn.commit()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='systemchannels';")
        systemchannels_table = cursor.fetchall()
        if systemchannels_table:
            cursor.execute("SELECT * FROM systemchannels;")
            entries = cursor.fetchall()
            for entry in entries:
                guild_id = entry[0]
                channel_id = entry[1]
                notify = 0  # Set default to not notify
                cursor.execute(
                    "INSERT INTO guild_settings ('guild_id', 'notify', 'systemchannel') values(?, ?, ?);",
                    (guild_id, notify, channel_id),
                )
            cursor.execute("DROP TABLE systemchannels;")
            conn.commit()

        cursor.close()
        conn.close()
        self.set_version(2)

    def two_to_three(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "limit_to_one" not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN 'limit_to_one' INT;")
            cursor.execute("UPDATE messages SET limit_to_one = 0 WHERE limit_to_one IS NULL;")
            conn.commit()

        cursor.close()
        conn.close()
        self.set_version(3)

    def three_to_four(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(reactionroles);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "message_id" not in columns:
            cursor.execute("SELECT reactionrole_id, reaction, role_id FROM reactionroles;")
            result = cursor.fetchall()

            targets = []
            for reaction_role in result:
                reaction: str = reaction_role[1]
                sanitized_reaction = sanitize_emoji(reaction)
                if reaction != sanitized_reaction:
                    reaction_role = list(reaction_role)
                    reaction_role[1] = sanitized_reaction
                    targets.append(reaction_role)

            if targets:
                # Repack targets for query
                # reactionrole_id, reaction, role_id -> reaction, reactionrole_id, role_id
                targets = [(i[1], i[0], i[2]) for i in targets]
                cursor.executemany("UPDATE reactionroles SET reaction = ? WHERE reactionrole_id = ? AND role_id = ?;", targets)
                conn.commit()

        cursor.close()
        conn.close()

        self.set_version(4)

    def four_to_five(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(reactionroles);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "message_id" not in columns:
            cursor.execute("ALTER TABLE reactionroles ADD COLUMN 'message_id' INT;")
            cursor.execute("SELECT reactionrole_id, message_id FROM messages;")
            result = cursor.fetchall()
            for reaction_role in result:
                reactionrole_id: int = reaction_role[0]
                message_id: int = reaction_role[1]
                cursor.execute(
                    "UPDATE reactionroles SET message_id = ? WHERE reactionrole_id = ?;", (message_id, reactionrole_id)
                )

            cursor.execute("SELECT message_id, reaction, role_id FROM reactionroles;")
            reactionroles = cursor.fetchall()
            cursor.execute("SELECT message_id, channel, guild_id, limit_to_one FROM messages;")
            messages = cursor.fetchall()
            cursor.execute("DROP TABLE reactionroles;")
            cursor.execute("DROP TABLE messages;")
            cursor.execute("CREATE TABLE 'reactionroles' ('message_id' INT, 'reaction' NVCARCHAR, 'role_id' INT);")
            cursor.execute("CREATE TABLE 'messages' ('message_id' INT, 'channel' INT, 'guild_id' INT, 'limit_to_one' INT);")
            cursor.executemany(
                "INSERT INTO 'reactionroles' ('message_id', 'reaction', 'role_id') values(?, ?, ?);", reactionroles
            )
            cursor.executemany(
                "INSERT INTO 'messages' ('message_id', 'channel', 'guild_id', 'limit_to_one') values(?, ?, ?, ?);", messages
            )
            conn.commit()

        cursor.close()
        conn.close()

        self.set_version(5)

    def five_to_six(self):
        """Add language to guild_settings if it does not exist"""
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(guild_settings);")
        result = cursor.fetchall()
        columns = [value[1] for value in result]
        if "language" not in columns:
            cursor.execute("ALTER TABLE guild_settings ADD COLUMN 'language' TEXT NULL;")
            conn.commit()

        cursor.close()
        conn.close()

        self.set_version(6)