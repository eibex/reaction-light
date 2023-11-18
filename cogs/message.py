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


import asyncio
from sqlite3 import Error as DatabaseError
import disnake
from disnake.ext import commands
from cogs.utils import database
from cogs.utils.sanitizing import sanitize_emoji
from cogs.utils.i18n import StaticResponse

static_response = StaticResponse()


class Message(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def formatted_channel_list(self, channel):
        # Returns a formatted numbered list of reaction roles message present in a given channel
        try:
            all_messages = self.bot.db.fetch_messages(channel.id)
        except DatabaseError as error:
            await self.bot.report(
                self.bot.response.get("db-error-fetching-messages", guild_id=channel.guild.id).format(exception=error),
                channel.guild.id,
            )
            return

        formatted_list = []
        counter = 1
        for msg_id in all_messages:
            try:
                old_msg = await channel.fetch_message(int(msg_id))

            except disnake.NotFound:
                # Skipping reaction-role messages that might have been deleted without updating CSVs
                continue

            entry = f"`{counter}` {old_msg.embeds[0].title if old_msg.embeds else old_msg.content}"
            formatted_list.append(entry)
            counter += 1

        return formatted_list

    @commands.slash_command(name="message")
    async def message_group(self, inter):
        pass

    @message_group.sub_command(name="new", description=static_response.get("brief-message-new"))
    async def new(self, inter):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.send(self.bot.response.get("new-reactionrole-noadmin", guild_id=inter.guild.id))
            return

        await inter.send(self.bot.response.get("new-reactionrole-init", guild_id=inter.guild.id))
        rl_object = {}
        cancelled = False

        def check(message):
            return message.author.id == inter.author.id and message.content != "" and message.channel.id == inter.channel.id

        if not cancelled:
            error_messages = []
            user_messages = []
            sent_reactions_message = await inter.channel.send(
                self.bot.response.get("new-reactionrole-roles-emojis", guild_id=inter.guild.id)
            )
            rl_object["reactions"] = {}
            try:
                while True:
                    reactions_message = await self.bot.wait_for("message", timeout=120, check=check)
                    user_messages.append(reactions_message)
                    if reactions_message.content.lower() != "done":
                        reaction = (reactions_message.content.split())[0]
                        try:
                            role = reactions_message.role_mentions[0].id
                        except IndexError:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        self.bot.response.get("new-reactionrole-error", guild_id=inter.guild.id)
                                    )
                                )
                            )
                            continue

                        if reaction in rl_object["reactions"]:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        self.bot.response.get("new-reactionrole-already-used", guild_id=inter.guild.id)
                                    )
                                )
                            )
                            continue
                        else:
                            try:
                                await reactions_message.add_reaction(reaction)
                                rl_object["reactions"][reaction] = role
                            except disnake.HTTPException:
                                error_messages.append(
                                    (
                                        await inter.channel.send(
                                            self.bot.response.get("new-reactionrole-emoji-403", guild_id=inter.guild.id)
                                        )
                                    )
                                )
                                continue
                    else:
                        rl_object["reaction_strings"] = [reaction for reaction, _ in (rl_object["reactions"].items())]
                        rl_object["reactions"] = dict(
                            (sanitize_emoji(reaction), role_id) for reaction, role_id in (rl_object["reactions"].items())
                        )
                        break
            except asyncio.TimeoutError:
                await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                cancelled = True
            finally:
                await sent_reactions_message.delete()
                for message in error_messages + user_messages:
                    await message.delete()

        if not cancelled:
            sent_limited_message = await inter.channel.send(
                self.bot.response.get("new-reactionrole-limit", guild_id=inter.guild.id)
            )

            def reaction_check(payload):
                return (
                    payload.member.id == inter.author.id
                    and payload.message_id == sent_limited_message.id
                    and (str(payload.emoji) == "🔒" or str(payload.emoji) == "♾️")
                )

            try:
                await sent_limited_message.add_reaction("🔒")
                await sent_limited_message.add_reaction("♾️")
                limited_message_response_payload = await self.bot.wait_for("raw_reaction_add", timeout=120, check=reaction_check)

                if str(limited_message_response_payload.emoji) == "🔒":
                    rl_object["limit_to_one"] = 1
                else:
                    rl_object["limit_to_one"] = 0
            except asyncio.TimeoutError:
                await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                cancelled = True
            finally:
                await sent_limited_message.delete()

        if not cancelled:
            sent_oldmessagequestion_message = await inter.channel.send(
                self.bot.response.get("new-reactionrole-old-or-new", guild_id=inter.guild.id).format(
                    bot_mention=self.bot.user.mention
                )
            )

            def reaction_check2(payload):
                return (
                    payload.member.id == inter.author.id
                    and payload.message_id == sent_oldmessagequestion_message.id
                    and (str(payload.emoji) == "🗨️" or str(payload.emoji) == "🤖")
                )

            try:
                await sent_oldmessagequestion_message.add_reaction("🗨️")
                await sent_oldmessagequestion_message.add_reaction("🤖")
                oldmessagequestion_response_payload = await self.bot.wait_for(
                    "raw_reaction_add", timeout=120, check=reaction_check2
                )

                if str(oldmessagequestion_response_payload.emoji) == "🗨️":
                    rl_object["old_message"] = True
                else:
                    rl_object["old_message"] = False
            except asyncio.TimeoutError:
                await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                cancelled = True
            finally:
                await sent_oldmessagequestion_message.delete()

        if not cancelled:
            error_messages = []
            user_messages = []
            if rl_object["old_message"]:
                sent_oldmessage_message = await inter.channel.send(
                    self.bot.response.get("new-reactionrole-which-message", guild_id=inter.guild.id)
                )

                def reaction_check3(payload):
                    return payload.user_id == inter.author.id and payload.guild_id == inter.guild.id and str(payload.emoji) == "🔧"

                try:
                    while True:
                        oldmessage_response_payload = await self.bot.wait_for(
                            "raw_reaction_add", timeout=120, check=reaction_check3
                        )
                        try:
                            try:
                                channel = await self.bot.getchannel(oldmessage_response_payload.channel_id)
                            except disnake.InvalidData:
                                channel = None
                            except disnake.HTTPException:
                                channel = None

                            if channel is None:
                                raise disnake.NotFound
                            try:
                                message = await channel.fetch_message(oldmessage_response_payload.message_id)
                            except disnake.HTTPException:
                                raise disnake.NotFound
                            try:
                                await message.add_reaction("👌")
                                await message.remove_reaction("👌", message.guild.me)
                                await message.remove_reaction("🔧", inter.author)
                            except disnake.HTTPException:
                                raise disnake.NotFound

                            try:
                                message_already_exists = self.bot.db.exists(message.id)
                            except DatabaseError as error:
                                await self.bot.report(
                                    self.bot.response.get("db-error-message-exists", guild_id=inter.guild.id).format(
                                        exception=error
                                    ),
                                    inter.guild.id,
                                )
                                return
                            if message_already_exists:
                                raise ValueError
                            rl_object["message"] = dict(
                                message_id=message.id, channel_id=message.channel.id, guild_id=message.guild.id
                            )
                            final_message = message
                            break
                        except disnake.NotFound:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        self.bot.response.get("new-reactionrole-permission-error", guild_id=inter.guild.id)
                                    )
                                )
                            )
                        except ValueError:
                            error_messages.append(
                                (
                                    await inter.channel.send(
                                        self.bot.response.get("new-reactionrole-already-exists", guild_id=inter.guild.id)
                                    )
                                )
                            )
                except asyncio.TimeoutError:
                    await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                    cancelled = True
                finally:
                    await sent_oldmessage_message.delete()
                    for message in error_messages:
                        await message.delete()
            else:
                sent_channel_message = await inter.channel.send(
                    self.bot.response.get("new-reactionrole-target-channel", guild_id=inter.guild.id)
                )
                try:
                    while True:
                        channel_message = await self.bot.wait_for("message", timeout=120, check=check)
                        user_messages.append(channel_message)
                        if channel_message.channel_mentions:
                            rl_object["target_channel"] = channel_message.channel_mentions[0]
                            break
                        else:
                            error_messages.append(
                                (
                                    await message.channel.send(
                                        self.bot.response.get("invalid-target-channel", guild_id=inter.guild.id)
                                    )
                                )
                            )
                except asyncio.TimeoutError:
                    await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                    cancelled = True
                finally:
                    await sent_channel_message.delete()
                    for message in error_messages + user_messages:
                        await message.delete()

        if not cancelled and "target_channel" in rl_object:
            error_messages = []
            user_messages = []
            selector_embed = disnake.Embed(title="Embed_title", description="Embed_content", colour=self.bot.config.botcolour)
            selector_embed.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)

            sent_message_message = await message.channel.send(
                self.bot.response.get("new-reactionrole-message-contents", guild_id=inter.guild.id), embed=selector_embed
            )
            try:
                while True:
                    message_message = await self.bot.wait_for("message", timeout=300, check=check)
                    user_messages.append(message_message)
                    msg_values = message_message.content.split(" // ")
                    # This whole system could also be re-done using wait_for to make the syntax easier for the user
                    # But it would be a breaking change that would be annoying for thoose who have saved their message commands
                    # for editing.
                    selector_msg_body = msg_values[0] if msg_values[0].lower() != "none" else None
                    selector_embed = disnake.Embed(colour=self.bot.config.botcolour)
                    selector_embed.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)

                    if len(msg_values) > 1:
                        if msg_values[1].lower() != "none":
                            selector_embed.title = msg_values[1]
                        if len(msg_values) > 2 and msg_values[2].lower() != "none":
                            selector_embed.description = msg_values[2]

                    # Prevent sending an empty embed instead of removing it
                    selector_embed = selector_embed if selector_embed.title or selector_embed.description else None

                    if selector_msg_body or selector_embed:
                        target_channel = rl_object["target_channel"]
                        sent_final_message = None
                        try:
                            sent_final_message = await target_channel.send(content=selector_msg_body, embed=selector_embed)
                            rl_object["message"] = dict(
                                message_id=sent_final_message.id,
                                channel_id=sent_final_message.channel.id,
                                guild_id=sent_final_message.guild.id,
                            )
                            final_message = sent_final_message
                            break
                        except disnake.Forbidden:
                            error_messages.append(
                                (
                                    await message.channel.send(
                                        self.bot.response.get(
                                            "new-reactionrole-message-send-permission-error", guild_id=inter.guild.id
                                        ).format(channel_mention=target_channel.mention)
                                    )
                                )
                            )
            except asyncio.TimeoutError:
                await inter.author.send(self.bot.response.get("new-reactionrole-timeout", guild_id=inter.guild.id))
                cancelled = True
            finally:
                await sent_message_message.delete()
                for message in error_messages + user_messages:
                    await message.delete()

        if not cancelled:
            # Ait we are (almost) all done, now we just need to insert that into the database and add the reactions 💪
            try:
                self.bot.db.add_reaction_role(rl_object)
            except database.DuplicateInstance:
                await inter.channel.send(self.bot.response.get("new-reactionrole-already-exists", guild_id=inter.guild.id))
                return
            except DatabaseError as error:
                await self.bot.report(
                    self.bot.response.get("db-error-new-reactionrole", guild_id=inter.guild.id).format(exception=error),
                    inter.guild.id,
                )
                return

            for reaction in rl_object["reaction_strings"]:
                await final_message.add_reaction(reaction)

        await inter.delete_original_message()

        if cancelled:
            await inter.channel.send(self.bot.response.get("new-reactionrole-cancelled", guild_id=inter.guild.id))

    @message_group.sub_command(name="edit", description=static_response.get("brief-message-edit"))
    async def edit_selector(
        self,
        inter: disnake.ApplicationCommandInteraction,
        channel: disnake.TextChannel = commands.Param(description=static_response.get("message-edit-option-channel")),
        number: int = commands.Param(description=static_response.get("message-edit-option-number")),
    ):
        await inter.response.defer()
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.edit_original_message(content=self.bot.response.get("not-admin", guild_id=inter.guild.id))
            return

        all_messages = await self.formatted_channel_list(channel)
        if number == 0:
            if len(all_messages) == 1:
                await inter.edit_original_message(content=self.bot.response.get("edit-reactionrole-one", guild_id=inter.guild.id))
            elif len(all_messages) > 1:
                await inter.edit_original_message(
                    content=self.bot.response.get("edit-reactionrole-instructions", guild_id=inter.guild.id).format(
                        num_messages=len(all_messages), message_list="\n".join(all_messages)
                    )
                )
            else:
                await inter.edit_original_message(
                    content=self.bot.response.get("no-reactionrole-messages", guild_id=inter.guild.id)
                )
        else:
            try:
                # Tries to edit the reaction-role message
                # Raises errors if the channel sent was invalid or if the bot cannot edit the message
                try:
                    all_messages = self.bot.db.fetch_messages(channel.id)
                except DatabaseError as error:
                    await self.bot.report(
                        self.bot.response.get("db-error-fetching-messages", guild_id=inter.guild.id).format(message_ids=error),
                        inter.guild.id,
                    )
                    return

                if all_messages:
                    message_to_edit_id = None
                    try:
                        message_to_edit_id = all_messages[number - 1]
                    except IndexError:
                        await inter.edit_original_message(
                            self.bot.response.get("reactionrole-not-exists", guild_id=inter.guild.id)
                        )

                else:
                    await inter.edit_original_message(self.bot.response.get("reactionrole-not-exists", guild_id=inter.guild.id))
                    return

                if message_to_edit_id:
                    old_msg = await channel.fetch_message(int(message_to_edit_id))
                else:
                    await inter.edit_original_message(self.bot.response.get("select-valid-reactionrole", guild_id=inter.guild.id))
                    return
                await old_msg.edit(suppress_embeds=False)

                # Send a message with a button to open a modal
                sent_message_message = await inter.edit_original_message(
                    content=self.bot.response.get("message-edit-button-content", guild_id=inter.guild.id),
                    components=[
                        disnake.ui.Button(
                            label=self.bot.response.get("message-edit-button-label", guild_id=inter.guild.id),
                            emoji="🔧",
                            style=disnake.ButtonStyle.primary,
                            custom_id="message_edit_modal",
                        )
                    ],
                )
                # Wait for the button to be pressed
                try:
                    button_ctx = await self.bot.wait_for(
                        "button_click",
                        check=lambda i: i.component.custom_id == "message_edit_modal"
                        and i.message.id == sent_message_message.id
                        and i.author.id == inter.author.id,
                        timeout=60,
                    )
                except asyncio.TimeoutError:
                    try:
                        await sent_message_message.delete(delay=None)
                    except disnake.HTTPException:
                        pass
                    return
                await button_ctx.response.send_modal(
                    title=self.bot.response.get("modal-edit-title", guild_id=inter.guild.id),
                    custom_id=("edit_reactionrole"),
                    components=[
                        disnake.ui.TextInput(
                            label=self.bot.response.get("message-edit-modal-message", guild_id=inter.guild.id),
                            required=False,
                            custom_id="message",
                            style=disnake.TextInputStyle.paragraph,
                        ),
                        disnake.ui.TextInput(
                            label=self.bot.response.get("message-edit-modal-title", guild_id=inter.guild.id),
                            required=False,
                            custom_id="title",
                            style=disnake.TextInputStyle.paragraph,
                        ),
                        disnake.ui.TextInput(
                            label=self.bot.response.get("message-edit-modal-description", guild_id=inter.guild.id),
                            required=False,
                            custom_id="description",
                            style=disnake.TextInputStyle.paragraph,
                        ),
                        disnake.ui.TextInput(
                            label=self.bot.response.get("message-edit-modal-image", guild_id=inter.guild.id),
                            required=False,
                            custom_id="image",
                            style=disnake.TextInputStyle.short,
                        ),
                        disnake.ui.TextInput(
                            label=self.bot.response.get("message-edit-modal-thumbnail", guild_id=inter.guild.id),
                            required=False,
                            custom_id="thumbnail",
                            style=disnake.TextInputStyle.short,
                        ),
                    ],
                )

                try:
                    selector_modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                        "modal_submit",
                        check=lambda i: i.custom_id == "edit_reactionrole" and i.author.id == inter.author.id,
                        timeout=300,
                    )
                except asyncio.TimeoutError:
                    # The user didn't submit the modal in the specified period of time.
                    # This is done since Discord doesn't dispatch any event for when a modal is closed/dismissed.
                    return

                await selector_modal_inter.response.defer()
                selector_embed = disnake.Embed()
                selector_msg_new_body = None
                for custom_id, value in selector_modal_inter.text_values.items():
                    if custom_id == "title" and value:
                        selector_embed.title = value
                        selector_embed.colour = self.bot.config.botcolour
                        selector_embed.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)

                    elif custom_id == "description" and value:
                        selector_embed.description = value
                        selector_embed.colour = self.bot.config.botcolour
                        selector_embed.set_footer(text=f"{self.bot.config.botname}", icon_url=self.bot.config.logo)

                    elif custom_id == "message" and value:
                        selector_msg_new_body = value

                    elif custom_id == "image" and value:
                        if "https://" not in value:
                            await inter.send(self.bot.response.get("invalid-attachment", guild_id=inter.guild.id))
                        else:
                            selector_embed.set_image(url=value)

                    elif custom_id == "thumbnail" and value:
                        if "https://" not in value:
                            await inter.send(self.bot.response.get("invalid-attachment", guild_id=inter.guild.id))
                        else:
                            selector_embed.set_thumbnail(url=value)

                try:
                    if selector_embed.title or selector_embed.description:
                        await old_msg.edit(content=selector_msg_new_body, embed=selector_embed)
                    else:
                        await old_msg.edit(content=selector_msg_new_body, embed=None)

                    await selector_modal_inter.edit_original_message(
                        content=self.bot.response.get("message-edited", guild_id=inter.guild.id)
                    )
                except disnake.Forbidden:
                    await selector_modal_inter.edit_original_message(
                        content=self.bot.response.get("other-author-error", guild_id=inter.guild.id)
                    )
                    return
                except disnake.HTTPException as e:
                    if e.code == 50006:
                        await selector_modal_inter.edit_original_message(
                            content=self.bot.response.get("empty-message-error", guild_id=inter.guild.id)
                        )
                    else:
                        guild_id = inter.guild.id
                        await self.bot.report(str(e), guild_id)
            except IndexError:
                await inter.send(content=self.bot.response.get("invalid-target-channel", guild_id=inter.guild.id))
            except disnake.Forbidden:
                await inter.send(content=self.bot.response.get("edit-permission-error", guild_id=inter.guild.id))

    @message_group.sub_command(name="reaction", description=static_response.get("brief-message-reaction"))
    async def edit_reaction(
        self,
        inter,
        channel: disnake.TextChannel = commands.Param(description=static_response.get("message-reaction-option-channel")),
        action: str = commands.Param(
            description=static_response.get("message-reaction-option-action"), choices={"add", "remove"}
        ),
        number: int = commands.Param(description=static_response.get("message-reaction-option-number")),
        reaction: str = commands.Param(description=static_response.get("message-reaction-option-reaction"), default=None),
        role: disnake.Role = commands.Param(description=static_response.get("message-reaction-option-role"), default=None),
    ):
        if not self.bot.isadmin(inter.author, inter.guild.id):
            await inter.send(self.bot.response.get("not-admin", guild_id=inter.guild.id))
            return

        await inter.response.defer()
        if number == 0 or not reaction:
            all_messages = await self.formatted_channel_list(channel)
            if len(all_messages) == 1:
                await inter.edit_original_message(content=self.bot.response.get("reaction-edit-one", guild_id=inter.guild.id))
                return
            elif len(all_messages) > 1:
                await inter.edit_original_message(
                    content=self.bot.response.get("reaction-edit-multi", guild_id=inter.guild.id).format(
                        num_messages=len(all_messages), message_list="\n".join(all_messages)
                    )
                )
                return
            else:
                await inter.edit_original_message(
                    content=self.bot.response.get("no-reactionrole-messages", guild_id=inter.guild.id)
                )
                return

        if action == "add":
            if not role:
                await inter.edit_original_message(content=self.bot.response.get("no-role-mentioned", guild_id=inter.guild.id))
                return

        try:
            all_messages = self.bot.db.fetch_messages(channel.id)
        except DatabaseError as error:
            await self.bot.report(
                self.bot.response.get("db-error-fetching-messages", guild_id=inter.guild.id).format(exception=error),
                inter.guild.id,
            )
            return

        counter = 1
        if all_messages:
            message_to_edit_id = None
            for msg_id in all_messages:
                # Loop through all msg_ids and stops when the counter matches the user input
                if counter == number:
                    message_to_edit_id = msg_id
                    break

                counter += 1
        else:
            await inter.edit_original_message(content=self.bot.response.get("reactionrole-not-exists", guild_id=inter.guild.id))
            return

        if message_to_edit_id:
            message_to_edit = await channel.fetch_message(int(message_to_edit_id))
        else:
            await inter.edit_original_message(content=self.bot.response.get("select-valid-reactionrole", guild_id=inter.guild.id))
            return

        if action == "add":
            try:
                # Check that the bot can actually use the emoji
                await message_to_edit.add_reaction(reaction)
            except disnake.HTTPException:
                await inter.edit_original_message(
                    content=self.bot.response.get("new-reactionrole-emoji-403", guild_id=inter.guild.id)
                )
                return

            try:
                react = self.bot.db.add_reaction(message_to_edit.id, role.id, sanitize_emoji(reaction))
            except DatabaseError as error:
                await self.bot.report(
                    self.bot.response.get("db-error-add-reaction", guild_id=inter.guild.id).format(
                        channel_mention=message_to_edit.channel.mention, exception=error
                    ),
                    inter.guild.id,
                )
                return

            if not react:
                await inter.edit_original_message(
                    content=self.bot.response.get("reaction-edit-already-exists", guild_id=inter.guild.id)
                )
                return

            await inter.edit_original_message(content=self.bot.response.get("reaction-edit-add-success", guild_id=inter.guild.id))
        elif action == "remove":
            try:
                await message_to_edit.clear_reaction(reaction)

            except disnake.HTTPException:
                await inter.edit_original_message(
                    content=self.bot.response.get("reaction-edit-invalid-reaction", guild_id=inter.guild.id)
                )
                return

            try:
                react = self.bot.db.remove_reaction(message_to_edit.id, sanitize_emoji(reaction))
            except DatabaseError as error:
                await self.bot.report(
                    self.bot.response.get("db-error-remove-reaction", guild_id=inter.guild.id).format(
                        channel_mention=message_to_edit.channel.mention, exception=error
                    ),
                    inter.guild.id,
                )
                return

            await inter.edit_original_message(
                content=self.bot.response.get("reaction-edit-remove-success", guild_id=inter.guild.id)
            )


def setup(bot):
    bot.add_cog(Message(bot))
