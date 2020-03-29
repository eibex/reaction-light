import os
import csv
import rldb


def migrate():
    directory = os.path.dirname(os.path.realpath(__file__))
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
                tracker = rldb.ReactionRoleCreationTracker(user=None, channel=None)
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
