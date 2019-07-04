import configparser
from itertools import cycle
import csv
import discord
from discord.ext import commands, tasks
import rlightfm


# Original Repository: https://github.com/eibex/reaction-light
__author__ = "eibex"
__version__ = "0.0.1"


config = configparser.ConfigParser()
config.read("config.ini")

TOKEN = str(config.get("server", "token"))

prefix = str(config.get("server", "prefix"))

Client = discord.Client()
bot = commands.Bot(command_prefix=prefix)
bot.remove_command("help")

# IDs
admin_a = int(config.get("server_role", "admin_a"))
admin_b = int(config.get("server_role", "admin_b"))
admin_c = int(config.get("server_role", "admin_c"))
logo = str(config.get("server", "logo"))
activities = []
with open("activities.csv", "r") as f:
    reader = csv.reader(f, delimiter=",")
    for row in reader:
        activity = row[0]
        activities.append(activity)
activities = cycle(activities)

# Colour palette - changes embeds' sideline colour
botcolor = 0xffff00


def isadmin(ctx, msg=False):
    check = ([role.id for role in ctx.author.roles] if msg
             else [role.id for role in ctx.message.author.roles])
    if admin_a in check or admin_b in check or admin_c in check:
        return True
    else:
        return False


@tasks.loop(seconds=30)
async def maintain_presence():
    activity = next(activities)
    await bot.change_presence(activity=discord.Game(name=activity))


@bot.event
async def on_ready():
    print("Reaction Light ready!")
    maintain_presence.start()


@bot.event
async def on_message(message):
    if isadmin(message, msg=True):
        user = str(message.author.id)
        ch = str(message.channel.id)
        wizard = rlightfm.get(user, ch)
        step = wizard[0]
        r_id = wizard[1]
        msg = message.content.split()
        if step is not None:
            if step == 1:
                rlightfm.step1(r_id, msg[0])
                await message.channel.send("Attach roles and emojis separated "
                                           "by a space (one combination per "
                                           "message). When you are done type "
                                           "`done`. Example:\n:smile: `@Role`")
            elif step == 2:
                if msg[0].lower() != "done":
                    rlightfm.step2(r_id,
                                   str(message.role_mentions[0].id),
                                   msg[0])
                else:
                    rlightfm.step2(r_id, None, msg[0], done=True)
                    em = discord.Embed(title="Title",
                                       description="Message_content",
                                       colour=botcolor)
                    em.set_footer(text="Reaction Light", icon_url=logo)
                    await message.channel.send("What would you like the "
                                               "message to say? Formatting "
                                               "is: `Title // "
                                               "Message_content`",
                                               embed=em)
            elif step == 3:
                msg = message.content.split(" // ")
                if len(msg) != 2:
                    await message.channel.send("Formatting is: `Title // "
                                               "Message_content`")
                else:
                    title = msg[0]
                    content = msg[1]
                    em = discord.Embed(title=title,
                                       description=content,
                                       colour=botcolor)
                    em.set_footer(text="Reaction Light", icon_url=logo)
                    ch = bot.get_channel(int(rlightfm.getch(r_id)))
                    emb = await ch.send(embed=em)
                    combo = rlightfm.getcombo(r_id)
                    for i in range(len(combo)):
                        if i != 0:
                            await emb.add_reaction(combo[i][0])
                    rlightfm.addids(emb.id, r_id)
                    rlightfm.end(r_id)

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    reaction = payload.emoji
    msg_id = payload.message_id
    ch_id = payload.channel_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    r = rlightfm.getids(str(msg_id))
    if r is not None:
        reactions = rlightfm.getreactions(r)
        ch = bot.get_channel(ch_id)
        msg = await ch.fetch_message(msg_id)
        user = bot.get_user(user_id)
        if str(reaction) not in reactions:
            await msg.remove_reaction(reaction, user)
        else:
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=reactions[str(reaction)])
            if user_id != bot.user.id:
                await member.add_roles(role)


@bot.event
async def on_raw_reaction_remove(payload):
    reaction = payload.emoji
    msg_id = payload.message_id
    user_id = payload.user_id
    guild_id = payload.guild_id
    r = rlightfm.getids(str(msg_id))
    if r is not None:
        reactions = rlightfm.getreactions(r)
        if str(reaction) in reactions:
            server = bot.get_guild(guild_id)
            member = server.get_member(user_id)
            role = discord.utils.get(server.roles, id=reactions[str(reaction)])
            await member.remove_roles(role)


@bot.command(name="new")
async def new(ctx):
    if isadmin(ctx):
        rlightfm.listen(ctx.message.author.id, ctx.message.channel.id)
        await ctx.send("Please paste the channel ID where to "
                       "send the auto-role message.")


@bot.command(name="help")
async def hlp(ctx):
    if isadmin(ctx):
        await ctx.send("Use `rl!new` to start creating a reaction message.\n"
                       "Visit <https://github.com/eibex/reaction-light/"
                       "blob/master/README.md#example> for a "
                       "setup walkthrough.")
    else:
        await ctx.send("You do not have an admin role.")


@bot.command(name="reload")
async def reload_config(ctx):
    if isadmin(ctx):
        global activities
        global admin_a
        global admin_b
        global admin_c
        global logo
        admin_a = int(config.get("server_role", "admin_a"))
        admin_b = int(config.get("server_role", "admin_b"))
        admin_c = int(config.get("server_role", "admin_c"))
        logo = str(config.get("server", "logo"))
        activities = []
        with open("activities.csv", "r") as f:
            reader = csv.reader(f, delimiter=",")
            for row in reader:
                activity = row[0]
                activities.append(activity)
        activities = cycle(activities)
        await ctx.send("Configuration reloaded.")


@bot.command(name="kill")
async def kill(ctx):
    if isadmin(ctx):
        await ctx.send("Shutting down...")
        exit()


bot.run(TOKEN)
