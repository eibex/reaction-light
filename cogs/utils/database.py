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
from random import randint


def initialize(database):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'messages' ('message_id' INT, 'channel' INT,"
        " 'guild_id' INT, 'limit_to_one' INT);"
    )
    cursor.execute("CREATE TABLE IF NOT EXISTS 'reactionroles' ('message_id' INT, 'reaction' NVCARCHAR, 'role_id' INT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS 'admins' ('role_id' INT, 'guild_id' INT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS 'cleanup_queue_guilds' ('guild_id' INT, 'unix_timestamp' INT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS 'dbinfo' ('version' INT);")
    cursor.execute("CREATE TABLE IF NOT EXISTS 'guild_settings' ('guild_id' INT, 'notify' INT, 'systemchannel' INT);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS guild_id_idx ON guild_settings (guild_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS message_idx ON messages (message_id);")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS guild_id_index ON cleanup_queue_guilds (guild_id);")
    conn.commit()
    cursor.close()
    conn.close()


class DuplicateInstance(Exception):
    pass


class Database:
    def __init__(self, database):
        self.database = database
        initialize(self.database)

        self.reactionrole_creation = {}

    def add_reaction_role(self, rl_dict: dict):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        if self.exists(rl_dict["message"]["message_id"]):
            raise DuplicateInstance("The message id is already in use!")
        cursor.execute(
            "INSERT INTO 'messages' ('message_id', 'channel',"
            " 'guild_id', 'limit_to_one') values(?, ?, ?, ?);",
            (
                rl_dict["message"]["message_id"],
                rl_dict["message"]["channel_id"],
                rl_dict["message"]["guild_id"],
                rl_dict["limit_to_one"],
            ),
        )
        combos = [(rl_dict["message"]["message_id"], reaction, role_id) for reaction, role_id in rl_dict["reactions"].items()]
        cursor.executemany("INSERT INTO 'reactionroles' ('message_id', 'reaction', 'role_id') values(?, ?, ?);", combos)
        conn.commit()
        cursor.close()
        conn.close()

    def exists(self, message_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE message_id = ?;", (message_id,))
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

    def get_reactions(self, message_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT reaction, role_id FROM reactionroles WHERE message_id = ?;", (message_id,))
        combos = {}
        for row in cursor:
            reaction = row[0]
            role_id = row[1]
            combos[reaction] = role_id

        cursor.close()
        conn.close()
        return combos

    def isunique(self, message_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT limit_to_one FROM messages WHERE message_id = ?;", (message_id,))
        unique = cursor.fetchall()[0][0]
        cursor.close()
        conn.close()
        return unique

    def fetch_messages(self, channel):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id FROM messages WHERE channel = ?;", (channel,))
        all_messages_in_channel = []
        for row in cursor:
            message_id = int(row[0])
            all_messages_in_channel.append(message_id)

        cursor.close()
        conn.close()
        return all_messages_in_channel

    def fetch_all_messages(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages;")
        all_messages = cursor.fetchall()

        cursor.close()
        conn.close()
        return all_messages

    def add_guild(self, channel_id, guild_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("UPDATE messages SET guild_id = ? WHERE channel = ?;", (guild_id, channel_id))
        conn.commit()
        cursor.close()
        conn.close()

    def remove_guild(self, guild_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        # Deleting the guilds reaction-role database entries
        cursor.execute("SELECT message_id FROM messages WHERE guild_id = ?;", (guild_id,))
        results = cursor.fetchall()
        if results:
            for result in results:
                message_id = result[0]
                cursor.execute("DELETE FROM messages WHERE message_id = ?;", (message_id,))
                cursor.execute("DELETE FROM reactionroles WHERE message_id = ?;", (message_id,))
        # Deleting the guilds guild_settings database entries
        cursor.execute("DELETE FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        # Delete the guilds admin roles
        cursor.execute("DELETE FROM admins WHERE guild_id = ?;", (guild_id,))
        # Delete the guilds potencial cleanup_queue entries
        cursor.execute("DELETE FROM cleanup_queue_guilds WHERE guild_id=?;", (guild_id,))
        conn.commit()

        cursor.close()
        conn.close()

    def delete(self, message_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE message_id = ?;", (message_id,))
        cursor.execute("DELETE FROM reactionroles WHERE message_id = ?;", (message_id,))
        conn.commit()
        cursor.close()
        conn.close()

    def add_admin(self, role_id: int, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO 'admins' ('role_id', 'guild_id') values(?,?);", (role_id, guild_id))
        conn.commit()
        cursor.close()
        conn.close()

    def remove_admin(self, role_id: int, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE role_id = ? AND guild_id = ?;", (role_id, guild_id))
        conn.commit()
        cursor.close()
        conn.close()

    def get_admins(self, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE guild_id = ?;", (guild_id,))
        admins = []
        for row in cursor:
            role_id = row[0]
            admins.append(role_id)

        cursor.close()
        conn.close()
        return admins

    def insert_guildsettings(self, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        notify = 0
        channel_id = 0
        cursor.execute(
            "INSERT OR IGNORE INTO guild_settings ('guild_id', 'notify', 'systemchannel') values(?, ?, ?);",
            (guild_id, notify, channel_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def add_systemchannel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        self.insert_guildsettings(guild_id)
        cursor.execute("UPDATE guild_settings SET systemchannel = ? WHERE guild_id = ?;", (channel_id, guild_id))
        conn.commit()
        cursor.close()
        conn.close()

    def remove_systemchannel(self, guild_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        channel_id = 0  # Set to false
        self.insert_guildsettings(guild_id)
        cursor.execute("UPDATE guild_settings SET systemchannel = ? WHERE guild_id = ?;", (channel_id, guild_id))
        conn.commit()
        cursor.close()
        conn.close()

    def fetch_systemchannel(self, guild_id):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT systemchannel FROM guild_settings WHERE guild_id = ?;", (guild_id,))
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

    def fetch_all_guilds(self):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id FROM messages;")
        message_guilds = cursor.fetchall()

        cursor.execute("SELECT guild_id FROM guild_settings;")
        systemchannel_guilds = cursor.fetchall()

        cursor.execute("SELECT guild_id FROM admins;")
        admin_guilds = cursor.fetchall()

        guilds = message_guilds + systemchannel_guilds + admin_guilds

        # Removes any duplicate guilds from the list
        guilds = list(dict.fromkeys(guilds))
        guild_ids = []
        for guild in guilds:
            if guild[0] is not None:
                guild_ids.append(guild[0])

        cursor.close()
        conn.close()
        return guild_ids

    def add_reaction(self, message_id, role_id, reaction):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reactionroles WHERE message_id = ? AND reaction = ?;", (message_id, reaction))
        exists = cursor.fetchall()
        if exists:
            cursor.close()
            conn.close()
            return False

        cursor.execute(
            "INSERT INTO reactionroles ('message_id', 'reaction', 'role_id') values(?, ?, ?);",
            (message_id, reaction, role_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def remove_reaction(self, message_id, reaction):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reactionroles WHERE message_id = ? AND reaction = ?;", (message_id, reaction))
        conn.commit()
        cursor.close()
        conn.close()

    def add_cleanup_guild(self, guild_id: int, unix_timestamp: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO 'cleanup_queue_guilds' ('guild_id', 'unix_timestamp') values(?,?);", (guild_id, unix_timestamp)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def remove_cleanup_guild(self, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cleanup_queue_guilds WHERE guild_id=?;", (guild_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True

    def fetch_cleanup_guilds(self, guild_ids_only=False):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        if guild_ids_only:
            cursor.execute("SELECT guild_id FROM cleanup_queue_guilds;")
            guilds = cursor.fetchall()
            guild_ids = []
            for guild in guilds:
                guild_ids.append(guild[0])
            guilds = guild_ids
        else:
            cursor.execute("SELECT * FROM cleanup_queue_guilds;")
            guilds = cursor.fetchall()
        cursor.close()
        conn.close()
        return guilds

    def toggle_notify(self, guild_id: int):
        # SQLite doesn't support booleans
        # INTs are used: 1 = True, 0 = False
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        self.insert_guildsettings(guild_id)
        cursor.execute("SELECT notify FROM guild_settings WHERE guild_id = ?", (guild_id,))
        results = cursor.fetchall()
        notify = results[0][0]
        if notify:
            notify = 0
            cursor.execute("UPDATE guild_settings SET notify = ? WHERE guild_id = ?", (notify, guild_id))

        else:
            notify = 1
            cursor.execute("UPDATE guild_settings SET notify = ? WHERE guild_id = ?", (notify, guild_id))
        conn.commit()
        cursor.close()
        conn.close()
        return notify

    def notify(self, guild_id: int):
        # SQLite doesn't support booleans
        # INTs are used: 1 = True, 0 = False
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        self.insert_guildsettings(guild_id)
        cursor.execute("SELECT notify FROM guild_settings WHERE guild_id = ?", (guild_id,))
        results = cursor.fetchall()
        notify = results[0][0]
        cursor.close()
        conn.close()
        return notify
