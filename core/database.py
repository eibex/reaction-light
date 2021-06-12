"""
MIT License

Copyright (c) 2019-2021 eibex

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
        " 'reactionrole_id' INT, 'guild_id' INT, 'limit_to_one' INT);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'reactionroles' ('reactionrole_id' INT, 'reaction'"
        " NVCARCHAR, 'role_id' INT);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'admins' ('role_id' INT, 'guild_id' INT);"
    )
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'cleanup_queue_guilds' ('guild_id' INT, 'unix_timestamp' INT);"
    )
    cursor.execute("CREATE TABLE IF NOT EXISTS 'dbinfo' ('version' INT);")
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS 'guild_settings' ('guild_id' INT, 'notify' INT, 'systemchannel' INT);"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS guild_id_idx ON guild_settings (guild_id);"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS reactionrole_idx ON messages (reactionrole_id);"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS guild_id_index ON cleanup_queue_guilds (guild_id);"
    )
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
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            if self.exists(rl_dict["message"]["message_id"]):
                raise DuplicateInstance("The message id is already in use!")
            while True:
                try:
                    reactionrole_id = randint(0, 100000)
                    cursor.execute(
                        "INSERT INTO 'messages' ('message_id', 'channel', 'reactionrole_id',"
                        " 'guild_id', 'limit_to_one') values(?, ?, ?, ?, ?);",
                        (
                            rl_dict["message"]["message_id"],
                            rl_dict["message"]["channel_id"],
                            reactionrole_id,
                            rl_dict["message"]["guild_id"],
                            rl_dict["limit_to_one"],
                        ),
                    )
                    break
                except sqlite3.IntegrityError:
                    continue
            combos = [
                (reactionrole_id, reaction, role_id)
                for reaction, role_id in rl_dict["reactions"].items()
            ]
            cursor.executemany(
                "INSERT INTO 'reactionroles' ('reactionrole_id', 'reaction', 'role_id') values(?, ?, ?);",
                combos,
            )
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            return e

    def exists(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE message_id = ?;", (message_id,)
            )
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result

        except sqlite3.Error as e:
            return e

    def get_reactions(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;",
                (message_id,),
            )
            reactionrole_id = cursor.fetchall()[0][0]
            cursor.execute(
                "SELECT reaction, role_id FROM reactionroles WHERE reactionrole_id"
                " = ?;",
                (reactionrole_id,),
            )
            combos = {}
            for row in cursor:
                reaction = row[0]
                role_id = row[1]
                combos[reaction] = role_id

            cursor.close()
            conn.close()
            return combos

        except sqlite3.Error as e:
            return e

    def isunique(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT limit_to_one FROM messages WHERE message_id = ?;",
                (message_id,),
            )
            unique = cursor.fetchall()[0][0]
            cursor.close()
            conn.close()
            return unique
        except sqlite3.Error as e:
            return e

    def fetch_messages(self, channel):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message_id FROM messages WHERE channel = ?;", (channel,)
            )
            all_messages_in_channel = []
            for row in cursor:
                message_id = int(row[0])
                all_messages_in_channel.append(message_id)

            cursor.close()
            conn.close()
            return all_messages_in_channel

        except sqlite3.Error as e:
            return e

    def fetch_all_messages(self):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages;")
            all_messages = cursor.fetchall()

            cursor.close()
            conn.close()
            return all_messages

        except sqlite3.Error as e:
            return e

    def add_guild(self, channel_id, guild_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE messages SET guild_id = ? WHERE channel = ?;",
                (guild_id, channel_id),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def remove_guild(self, guild_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            # Deleting the guilds reaction-role database entries
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE guild_id = ?;",
                (guild_id,),
            )
            results = cursor.fetchall()
            if results:
                for result in results:
                    reactionrole_id = result[0]
                    cursor.execute(
                        "DELETE FROM messages WHERE reactionrole_id = ?;",
                        (reactionrole_id,),
                    )
                    cursor.execute(
                        "DELETE FROM reactionroles WHERE reactionrole_id = ?;",
                        (reactionrole_id,),
                    )
            # Deleting the guilds guild_settings database entries
            cursor.execute(
                "DELETE FROM guild_settings WHERE guild_id = ?;",
                (guild_id,),
            )
            # Delete the guilds admin roles
            cursor.execute(
                "DELETE FROM admins WHERE guild_id = ?;",
                (guild_id,),
            )
            # Delete the guilds potencial cleanup_queue entries
            cursor.execute(
                "DELETE FROM cleanup_queue_guilds WHERE guild_id=?;", (guild_id,)
            )
            conn.commit()

            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def delete(self, message_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;",
                (message_id,),
            )

            result = cursor.fetchone()
            if result:
                reactionrole_id = result[0]
                cursor.execute(
                    "DELETE FROM messages WHERE reactionrole_id = ?;",
                    (reactionrole_id,),
                )
                cursor.execute(
                    "DELETE FROM reactionroles WHERE reactionrole_id = ?;",
                    (reactionrole_id,),
                )
                conn.commit()

            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def add_admin(self, role_id: int, guild_id: int):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO 'admins' ('role_id', 'guild_id') values(?,?);",
                (role_id, guild_id),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def remove_admin(self, role_id: int, guild_id: int):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM admins WHERE role_id = ? AND guild_id = ?;",
                (role_id, guild_id),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def get_admins(self, guild_id: int):
        try:
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

        except sqlite3.Error as e:
            return e

    def insert_guildsettings(self, guild_id: int):
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        notify = 0
        channel_id = 0
        cursor.execute(
            "INSERT OR IGNORE INTO guild_settings ('guild_id', 'notify', 'systemchannel')"
            " values(?, ?, ?);",
            (guild_id, notify, channel_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

    def add_systemchannel(self, guild_id, channel_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            self.insert_guildsettings(guild_id)
            cursor.execute(
                "UPDATE guild_settings SET systemchannel = ? WHERE guild_id = ?;",
                (channel_id, guild_id),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def remove_systemchannel(self, guild_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            channel_id = 0  # Set to false
            self.insert_guildsettings(guild_id)
            cursor.execute(
                "UPDATE guild_settings SET systemchannel = ? WHERE guild_id = ?;",
                (channel_id, guild_id),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def fetch_systemchannel(self, guild_id):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT systemchannel FROM guild_settings WHERE guild_id = ?;",
                (guild_id,),
            )
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result

        except sqlite3.Error as e:
            return e

    def fetch_all_guilds(self):
        try:
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

        except sqlite3.Error as e:
            return e

    def add_reaction(self, message_id, role_id, reaction):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;",
                (message_id,),
            )
            reactionrole_id = cursor.fetchall()[0][0]
            cursor.execute(
                "SELECT * FROM reactionroles WHERE reactionrole_id = ? AND reaction = ?;",
                (reactionrole_id, reaction),
            )
            exists = cursor.fetchall()
            if exists:
                cursor.close()
                conn.close()
                return False

            cursor.execute(
                "INSERT INTO reactionroles ('reactionrole_id', 'reaction', 'role_id')"
                " values(?, ?, ?);",
                (reactionrole_id, reaction, role_id),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except sqlite3.Error as e:
            return e

    def remove_reaction(self, message_id, reaction):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reactionrole_id FROM messages WHERE message_id = ?;",
                (message_id,),
            )
            reactionrole_id = cursor.fetchall()[0][0]
            cursor.execute(
                "DELETE FROM reactionroles WHERE reactionrole_id = ? AND reaction = ?;",
                (reactionrole_id, reaction),
            )
            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            return e

    def add_cleanup_guild(self, guild_id: int, unix_timestamp: int):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO 'cleanup_queue_guilds' ('guild_id', 'unix_timestamp') values(?,?);",
                (guild_id, unix_timestamp),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except sqlite3.Error as e:
            return e

    def remove_cleanup_guild(self, guild_id: int):
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM cleanup_queue_guilds WHERE guild_id=?;", (guild_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True

        except sqlite3.Error as e:
            return e

    def fetch_cleanup_guilds(self, guild_ids_only=False):
        try:
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

        except sqlite3.Error as e:
            return e

    def toggle_notify(self, guild_id: int):
        # SQLite doesn't support booleans
        # INTs are used: 1 = True, 0 = False
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            self.insert_guildsettings(guild_id)
            cursor.execute(
                "SELECT notify FROM guild_settings WHERE guild_id = ?", (guild_id,)
            )
            results = cursor.fetchall()
            notify = results[0][0]
            if notify:
                notify = 0
                cursor.execute(
                    "UPDATE guild_settings SET notify = ? WHERE guild_id = ?",
                    (notify, guild_id),
                )

            else:
                notify = 1
                cursor.execute(
                    "UPDATE guild_settings SET notify = ? WHERE guild_id = ?",
                    (notify, guild_id),
                )
            conn.commit()
            cursor.close()
            conn.close()
            return notify

        except sqlite3.Error as e:
            return e

    def notify(self, guild_id: int):
        # SQLite doesn't support booleans
        # INTs are used: 1 = True, 0 = False
        try:
            conn = sqlite3.connect(self.database)
            cursor = conn.cursor()
            self.insert_guildsettings(guild_id)
            cursor.execute(
                "SELECT notify FROM guild_settings WHERE guild_id = ?", (guild_id,)
            )
            results = cursor.fetchall()
            notify = results[0][0]
            cursor.close()
            conn.close()
            return notify

        except sqlite3.Error as e:
            return e
