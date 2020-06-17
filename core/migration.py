"""
MIT License

Copyright (c) 2019-2020 eibex

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


import os
import csv
import configparser
from . import database


def migrate():
    directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    folder = f"{directory}/files"
    files = os.listdir(folder)
    if "id.csv" not in files:
        print("No files to migrate.")
        return False
    else:
        for file in os.listdir(folder):
            if (
                file.endswith(".csv")
                and file != "activities.csv"
                and file != "cache.csv"
                and file != "id.csv"
            ):
                print(f"Migrating {file}")
                filepath = os.path.join(folder, file)
                with open(filepath, "r") as f:
                    reader = csv.reader(f, delimiter=",")
                    counter = 0
                    reaction_role = {}
                    for row in reader:
                        if counter == 0:
                            # if first iteration
                            # get channel id at top of csv file
                            channel_id = row[0]
                            counter += 1
                        else:
                            reaction = row[0]
                            role_id = row[1]
                            reaction_role[reaction] = int(role_id)

                with open(f"{folder}/cache.csv", "r") as f:
                    reader = csv.reader(f, delimiter=",")
                    for row in reader:
                        embed_id = row[1]
                        if embed_id == file.rstrip(".csv"):
                            # reverse lookup of message_id via CSV embed_id
                            message_id = int(row[0])
                            break
                tracker = database.ReactionRoleCreationTracker(
                    user=None, channel=None, database=f"{folder}/reactionlight.db"
                )
                print(f"Getting target channel: {channel_id}")
                tracker.target_channel = channel_id
                print(f"Getting reaction-roles:\n{reaction_role}")
                tracker.combos = reaction_role
                print(f"Getting message: {message_id}")
                tracker.message_id = message_id
                print("Committing to database")
                tracker.commit()
                print(f"Removing: {file}")
                os.remove(filepath)
                print(f"Removed: {file}\n\n")

        print("Removing id.csv and cache.csv")
        os.remove(f"{folder}/cache.csv")
        os.remove(f"{folder}/id.csv")

        print("\nMigration completed.")
        return True


def migrateconfig():
    directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    configfile = f"{directory}/config.ini"
    config = configparser.ConfigParser()
    config.read(configfile)
    try:
        config.get("server", "colour")
    except configparser.NoOptionError:
        config["server"]["colour"] = "0xffff00"
        with open(configfile, "w") as f:
            config.write(f)
        print("Migrated bot colour to config.ini")
    try:
        admins = [
            int(config.get("server_role", "admin_a")),
            int(config.get("server_role", "admin_b")),
            int(config.get("server_role", "admin_c")),
        ]
        for admin in admins:
            if admin != 0:
                database.add_admin(admin)
        print("\nAdmin migration completed.")
        config.remove_option("server_role", "admin_a")
        config.remove_option("server_role", "admin_b")
        config.remove_option("server_role", "admin_c")
        config.remove_section("server_role")
        with open(configfile, "w") as f:
            config.write(f)
        return True
    except configparser.NoSectionError:
        print("No admins to migrate in config.ini.")
        return False
