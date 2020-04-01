from os import path
import sqlite3
from random import randint

# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

directory = path.dirname(path.realpath(__file__))
conn = sqlite3.connect(f"{directory}/files/reactionlight.db")

cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS 'messages' ('message_id' INT, 'channel' INT, 'reactionrole_id' INT);"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS 'reactionroles' ('reactionrole_id' INT, 'reaction' NVCARCHAR, 'role_id' INT);"
)
cursor.execute("CREATE TABLE IF NOT EXISTS 'admins' ('role_id' INT);")
conn.commit()
cursor.close()

reactionrole_creation = {}


class ReactionRoleCreationTracker:
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        self.step = 0
        self.target_channel = None
        self.combos = {}
        self.message_id = None
        self._generate_reactionrole_id()

    def _generate_reactionrole_id(self):
        while True:
            self.reactionrole_id = randint(0, 100000)
            c.execute(
                "SELECT * FROM messages WHERE reactionrole_id = ?", (self.reactionrole_id,)
            )
            already_exists = c.fetchall()
            if already_exists:
                continue
            break

    def commit(self):
        c = conn.cursor()
        c.execute(
            "INSERT INTO 'messages' ('message_id', 'channel', 'reactionrole_id') values(?, ?, ?);", (self.message_id, self.target_channel, self.reactionrole_id)
        )
        for reaction in self.combos:
            role_id = self.combos[reaction]
            c.execute(
                "INSERT INTO 'reactionroles' ('reactionrole_id', 'reaction', 'role_id') values(?, ?, ?);", (self.reactionrole_id, reaction, role_id)
            )
        conn.commit()
        c.close()


def start_creation(user, channel):
    tracker = ReactionRoleCreationTracker(user, channel)
    if not f"{user}_{channel}" in reactionrole_creation:
        reactionrole_creation[f"{user}_{channel}"] = tracker
        return True
    return False


def abort(user, channel):
    if f"{user}_{channel}" in reactionrole_creation:
        del reactionrole_creation[f"{user}_{channel}"]
        return True
    return False


def step(user, channel):
    if f"{user}_{channel}" in reactionrole_creation:
        tracker = reactionrole_creation[f"{user}_{channel}"]
        return tracker.step
    return None


def get_targetchannel(user, channel):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    return tracker.target_channel


def get_combos(user, channel):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    return tracker.combos


def step0(user, channel):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    tracker.step += 1


def step1(user, channel, target_channel):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    tracker.target_channel = target_channel
    tracker.step += 1


def step2(user, channel, role=None, reaction=None, done=False):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    if not done:
        tracker.combos[reaction] = role
    else:
        tracker.step += 1


def end_creation(user, channel, message_id):
    tracker = reactionrole_creation[f"{user}_{channel}"]
    tracker.message_id = message_id
    try:
        tracker.commit()
    except sqlite3.Error as e:
        return e
    del reactionrole_creation[f"{user}_{channel}"]


def exists(message_id):
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM messages WHERE message_id = ?;", (message_id,))
        result = c.fetchall()
        c.close()
        return result
    except sqlite3.Error as e:
        return e


def get_reactions(message_id):
    try:
        c = conn.cursor()
        c.execute(
            "SELECT reactionrole_id FROM messages WHERE message_id = ?;", (message_id,)
        )
        reactionrole_id = c.fetchall()[0][0]
        c.execute(
            "SELECT reaction, role_id FROM reactionroles WHERE reactionrole_id = ?;", (reactionrole_id,)
        )
        combos = {}
        for row in c:
            reaction = row[0]
            role_id = row[1]
            combos[reaction] = role_id
        c.close()
        return combos
    except sqlite3.Error as e:
        return e


def fetch_messages(channel):
    try:
        c = conn.cursor()
        c.execute("SELECT message_id FROM messages WHERE channel = ?;", (channel,))
        all_messages_in_channel = []
        for row in c:
            message_id = int(row[0])
            all_messages_in_channel.append(message_id)
        c.close()
        return all_messages_in_channel
    except sqlite3.Error as e:
        return e


def fetch_all_messages():
    try:
        c = conn.cursor()
        c.execute(f"SELECT message_id, channel FROM messages;")
        all_messages = {}
        for row in c:
            message_id = int(row[0])
            channel_id = int(row[1])
            all_messages[message_id] = channel_id
        c.close()
        return all_messages
    except sqlite3.Error as e:
        return e


def delete(message_id):
    try:
        c = conn.cursor()
        c.execute(
            f"SELECT reactionrole_id FROM messages WHERE message_id = '{message_id}';"
        )
        reactionrole_id = c.fetchall()[0][0]
        c.execute(f"DELETE FROM messages WHERE reactionrole_id = '{reactionrole_id}'")
        c.execute(f"DELETE FROM reactionroles WHERE reactionrole_id = '{reactionrole_id}'")
        conn.commit()
        c.close()
    except sqlite3.Error as e:
        return e


def add_admin(role):
    try:
        c = conn.cursor()
        c.execute("INSERT INTO 'admins' ('role_id') values(?);", (role,))
        conn.commit()
        c.close()
    except sqlite3.Error as e:
        return e


def remove_admin(role):
    try:
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE role_id = ?;", (role,))
        conn.commit()
        c.close()
    except sqlite3.Error as e:
        return e


def get_admins():
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM admins;")
        admins = []
        for row in c:
            role_id = row[0]
            admins.append(role_id)
        c.close()
        return admins
    except sqlite3.Error as e:
        return e
