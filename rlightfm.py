from random import randint
from shutil import copy
from os import path
import csv

folder = "{}/files".format(path.dirname(path.realpath(__file__)))
wizard = {}
wizardcache = {}
cache = {}


def readcache():
    # Reads cache.csv and stores into the dictionary
    # Run at the start of the program and updated when changes are made
    try:
        with open("{}/cache.csv".format(folder), "r") as f:
            read = csv.reader(f, delimiter=",")
            for row in read:
                cache[row[0]] = row[1]
    except FileNotFoundError:
        print("No cache.csv file found. It will be created on the next wizard run.")


def get(user, channel):
    # Checks if a setup process was initiated by "user" in "channel"
    # If it was, it returns the setup ID along with the current setup step
    # Otherwise a (None, None) tuple is returned
    global wizard
    for i in wizard:
        wizuser = wizard[i][0]
        wizchannel = wizard[i][1]
        r_id = wizard[i][2]
        step = wizard[i][3]
        if wizuser == user and wizchannel == channel:
            return step, r_id
    return None, None


def getch(r):
    return wizardcache[r][0][0]


def getcombo(r):
    # Returns the reaction-role combinations
    with open("{}/{}.csv".format(folder, str(r)), "r") as f:
        read = csv.reader(f, delimiter=",")
        return [i for i in read]


def addids(message_id, r):
    # Adds the embed ID and CSV filename to the cache
    with open("{}/cache.csv".format(folder), "a") as f:
        w = csv.writer(f, delimiter=",")
        w.writerow([message_id, r])


def getids(message_id):
    # Returns the CSV filename corresponding to an embed ID
    if message_id in cache:
        return cache[message_id]
    return None


def getreactions(r):
    # Returns a list of the reactions used by a certain embed
    with open("{}/{}.csv".format(folder, str(r)), "r") as f:
        read = csv.reader(f, delimiter=",")
        reactions = {}
        for row in read:
            try:
                reactions[row[0]] = int(row[1])
            except IndexError:
                pass
        return reactions


def listen(user, channel):
    # When the setup process is started a setup ID is assigned to a [user, channel] list
    # The setup ID is also used as the CSV filename that stores the reaction-role combinations
    global wizard
    r = str(randint(0, 100000))
    ids = {}

    try:
        with open("{}/id.csv".format(folder), "r") as f:
            read = csv.reader(f, delimiter=",")
            for i in read:
                ids[i[0]] = i[1:]
        while r in ids:
            r = str(randint(0, 100000))
    except FileNotFoundError:
        print("Creating id.csv")

    ids[r] = [str(user), str(channel)]
    with open("{}/id.csv".format(folder), "w") as f:
        w = csv.writer(f, delimiter=",")
        for i in ids:
            row = [i, ids[i][0], ids[i][1]]
            w.writerow(row)

    wizard[r] = [str(user), str(channel), r, 1]
    print("Created entry in Wizard: " + r)


def step1(r, role_channel):
    # The wizardcache is a dictionary where the key is the setup ID
    # and the value is a list of lists (which will be written to CSV)
    # Here, at the top of the list, the channel ID is added.
    global wizard
    global wizardcache
    wizardcache[r] = [[role_channel]]
    wizard[r][3] += 1  # Set step2 (was 1)


def step2(r, role, emoji, done=False):
    # Adds [emoji, role] combinations to the wizardcache
    # If "done" is passed, the wizardcache is written to CSV
    global wizard
    global wizardcache
    if done:
        wizard[r][3] += 1  # Set step3 (was 2)
        with open("{}/{}.csv".format(folder, str(r)), "a") as f:
            w = csv.writer(f, delimiter=",")
            for i in wizardcache[r]:
                w.writerow(i)
        print("Done adding combos and saved.")
        return
    combo = [emoji, role]
    print("Added " + emoji + " : " + role + " combo.")
    wizardcache[r].append(combo)


def edit(role_channel):
    # Loops through all CSVs to check for embeds that are present in role_channel
    r_ids = {}
    for msg_id in cache:
        r = cache[msg_id]
        with open("{}/{}.csv".format(folder, str(r)), "r") as f:
            read = csv.reader(f, delimiter=",")
            for row in read:
                channel = int(row[0])
                break # The channel is stored only at the first row
            if role_channel == channel:
                r_ids[str(msg_id)] = str(r)
    return r_ids

def end(r):
    # Deletes the setup process and updates the cache
    del wizard[r]
    readcache()


if not path.isfile("{}/activities.csv".format(folder)):
    copy(
        "{}/activities.csv.sample".format(folder), "{}/activities.csv".format(folder),
    )


readcache()
