from os import path
import sqlite3

# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex

directory = path.dirname(path.realpath(__file__))
database = sqlite3.connect(f"{directory}/files/reactionlight.db")
db = database.cursor()

embeds_creation = {}

class EmbedCreationTracker:
    def __init__(self, user, channel):
        self.user = user
        self.channel = channel
        self.step = 1
        self.target_channel = None
        self.combos = {}
        self.message_id = None

    def commit(self):
        db.execute(f"CREATE TABLE '{self.message_id}' ('reaction' NVCARCHAR, 'role_id' INT);")
        for reaction in self.combos:
            role_id = self.combos[reaction]
            db.execute(f"INSERT INTO '{self.message_id}' ('reaction', 'role_id') values('{reaction}', '{role_id}');")
            print(f"Adding {reaction} ++ {role_id} to {self.message_id}")
        database.commit()


def step(user, channel):
    if f"{user}_{channel}" in embeds_creation:
        tracker = embeds_creation[f"{user}_{channel}"]
        return tracker.step
    else:
        return None


def start_creation(user, channel):
    tracker = EmbedCreationTracker(user, channel)
    embeds_creation[f"{user}_{channel}"] = tracker


def get_targetchannel(user, channel):
    tracker = embeds_creation[f"{user}_{channel}"]
    return tracker.target_channel


def get_combos(user, channel):
    tracker = embeds_creation[f"{user}_{channel}"]
    return tracker.combos


def step1(user, channel, target_channel):
    tracker = embeds_creation[f"{user}_{channel}"]
    tracker.target_channel = target_channel
    tracker.step += 1


def step2(user, channel, role=None, reaction=None, done=False):
    tracker = embeds_creation[f"{user}_{channel}"]
    if not done:
        tracker.combos[reaction] = role
    else:
        tracker.step += 1


def end_creation(user, channel, message_id):
    tracker = embeds_creation[f"{user}_{channel}"]
    tracker.message_id = message_id
    tracker.commit()
    del embeds_creation[f"{user}_{channel}"]
    del tracker


def exists(message_id):
    db.execute(f"select name from sqlite_master where type='table' and name='{message_id}';")
    result = db.fetchall()
    return result


def get_reactions(message_id):
    db.execute(f"select * from '{message_id}';")
    combos = {}
    for row in db:
        reaction = row[0]
        role_id = row[1]
        combos[reaction] = role_id
    return combos
