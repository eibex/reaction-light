from os import path
import sqlite3
from random import randint

# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

directory = path.dirname(path.realpath(__file__))
database = sqlite3.connect(f"{directory}/files/reactionlight.db")
db = database.cursor()

db.execute(
    "CREATE TABLE IF NOT EXISTS 'messages' ('message_id' INT, 'channel' INT, 'reactionrole_id' INT);"
)
db.execute(
    "CREATE TABLE IF NOT EXISTS 'reactionroles' ('reactionrole_id' INT, 'reaction' NVCARCHAR, 'role_id' INT);"
)
db.execute(
    "CREATE TABLE IF NOT EXISTS 'admins' ('role_id' INT);"
)

reactionrole_creation = {}


class ReactionRoleCreationTracker:
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        self.step = 1
        self.target_channel = None
        self.combos = {}
        self.message_id = None
        self._generate_reactionrole_id()

    def _generate_reactionrole_id(self):
        while True:
            self.reactionrole_id = randint(0, 100000)
            db.execute(
                f"SELECT * FROM messages WHERE reactionrole_id = '{self.reactionrole_id}'"
            )
            already_exists = db.fetchall()
            if already_exists:
                continue
            break

    def commit(self):
        db.execute(
            f"INSERT INTO 'messages' ('message_id', 'channel', 'reactionrole_id') values('{self.message_id}', '{self.target_channel}', '{self.reactionrole_id}');"
        )
        for reaction in self.combos:
            role_id = self.combos[reaction]
            db.execute(
                f"INSERT INTO 'reactionroles' ('reactionrole_id', 'reaction', 'role_id') values('{self.reactionrole_id}', '{reaction}', '{role_id}');"
            )
        database.commit()


def start_creation(user, channel):
    tracker = ReactionRoleCreationTracker(user, channel)
    reactionrole_creation[f"{user}_{channel}"] = tracker


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
    tracker.commit()
    del reactionrole_creation[f"{user}_{channel}"]


def exists(message_id):
    db.execute(f"SELECT * FROM messages WHERE message_id = '{message_id}';")
    result = db.fetchall()
    return result


def get_reactions(message_id):
    db.execute(
        f"SELECT reactionrole_id FROM messages WHERE message_id = '{message_id}';"
    )
    reactionrole_id = db.fetchall()[0][0]
    db.execute(
        f"SELECT reaction, role_id FROM reactionroles WHERE reactionrole_id = '{reactionrole_id}';"
    )
    combos = {}
    for row in db:
        reaction = row[0]
        role_id = row[1]
        combos[reaction] = role_id
    return combos


def fetch_messages(channel):
    db.execute(f"SELECT message_id FROM messages WHERE channel = '{channel}';")
    all_messages = []
    for row in db:
        message_id = int(row[0])
        all_messages.append(message_id)
    return all_messages


def add_admin(role):
    db.execute(f"INSERT INTO 'admins' ('role_id') values('{role}');")
    database.commit()


def remove_admin(role):
    db.execute(f"DELETE FROM admins WHERE role_id = '{role}';")
    database.commit()


def get_admins():
    db.execute(f"SELECT * FROM admins;")
    admins = []
    for row in db:
        role_id = row[0]
        admins.append(role_id)
    return admins
