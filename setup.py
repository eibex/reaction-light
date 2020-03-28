from os import path
from shutil import copy
import configparser

# Original Repository: https://github.com/eibex/reaction-light
# License: MIT - Copyright 2019-2020 eibex
folder = path.dirname(path.realpath(__file__))
with open(f"{folder}/.version") as f:
    __version__ = f.read().rstrip("\n").rstrip("\r")

print("Original Repository: https://github.com/eibex/reaction-light")
print(f"Version: {__version__}")
print("License: MIT\n")

print("### ### Reaction Light Setup ### ###")
print(
    "If you would like more information about any of the steps, type 'help' as an answer."
)
print(
    "If you would like to abort the configuration close the program. No input will be written to file until the setup is complete."
)
print(
    "Default values are shown inside square brackets [] where applicable. Pressing enter and leaving the field empty will accept the default value."
)

while True:
    token = input(
        "\nPaste the token of your bot user (you can create one at: https://discordapp.com/developers/applications/)  "
    )
    if token.lower() == "help":
        print(
            "\nThe bot token looks like this: NDYzODUwNzM2OTk3MTA1NjY2.XSH7WA.w0WPO4tafLJ9rZoitBq1Q43AgnQ\n"
        )
        continue
    elif token == "":
        continue
    else:
        break


prefix = input("\nInsert the prefix of the bot (help not available for this) [rl!]  ")
if prefix == "":
    prefix = "rl!"

while True:
    name = input("\nInsert the name you wish to give the bot [Reaction Light]  ")
    if name.lower() == "help":
        print("\nThe name will be shown in the embed footers created by the bot.")
    elif name == "":
        name = "Reaction Light"
        break
    else:
        break

while True:
    logo = input(
        "\nPaste the URL to your preferred logo file (should end in *.png, *.jpg, *.webp, ...)  [readme.md logo]  "
    )
    if logo.lower() == "help":
        print("\nThe logo is the picture shown in the footer of the embeds.\n")
        continue
    elif logo == "":
        logo = "https://cdn.discordapp.com/attachments/671738683623473163/693451064904515645/spell_holy_weaponmastery.jpg"
        break
    else:
        break

while True:
    admin_a = input("Paste the role ID of your admin role.\n")
    if admin_a.lower() == "help":
        print(
            "\nYou can find the ID of the role by right clicking it in server settings and clicking on 'Copy ID'. You need to enable Developer Mode on Discord.\n"
        )
        continue
    else:
        admin_b = input(
            "\nPaste the role ID of your second admin role. If none, type 0.\n"
        )
        admin_c = input(
            "\nPaste the role ID of your third admin role. If none, type 0.\n"
        )
        break

while True:
    system_channel = input(
        "Paste the ID of the channel you wish to receive system notifications (e.g. errors, new versions of the bot). This is optional and you can set it up later by using the systemchannel command.\n"
    )
    if system_channel.lower() == "help":
        print(
            "Currently only new versions are going to be fetched. Less than one message per week. Leave blank if no updates or error notifications want to be received."
        )
        continue
    else:
        break

config = configparser.ConfigParser()
config.read("{}/config.ini.sample".format(folder))
config["server"]["token"] = token
config["server"]["prefix"] = prefix
config["server"]["name"] = name
config["server"]["logo"] = logo
config["server"]["system_channel"] = system_channel
config["server_role"]["admin_a"] = admin_a
config["server_role"]["admin_b"] = admin_b
config["server_role"]["admin_c"] = admin_c

with open("config.ini.sample", "w") as f:
    config.write(f)

copy("{}/config.ini.sample".format(folder), "{}/config.ini".format(folder))

input("Done. You can now start the bot.")
