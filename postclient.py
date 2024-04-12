from typing import Any

from telethon import TelegramClient, events, errors
from telethon.tl.types import User, Channel
import asyncio
import logging
import re

from database.rules_io import cmd_export_rules, cmd_import_rules
from shared.config import Config
from database.orm_sqlite3 import Database, RulesTable
from shared.filter_by_parameters import check_filter, flt


# logging.basicConfig(level=logging.ERROR)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - [%(levelname)s] -  %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
)
tg_client = TelegramClient(Config.app_name, Config.api_id, Config.api_hash)
db = Database(db_file=Config.database)

current_state: dict[str, Any] = {}

rules_list = []


async def reload_filters():
    rules_list.clear()
    rules = await db.get_rules_table().get_rules()
    for rule in rules:
        rules_list.append(rule)
    res = len(rules_list)

    # await tg_client.get_me()
    if not res:
        await tg_client.send_message(Config.app_channel_id,
                                     "Rules not found. Fill the CSV file and upload it to my bot!\n\n"
                                     "I'm ready to work.")
        return False
    else:

        await tg_client.send_message(Config.app_channel_id, f"**{len(rules_list)} rules data loaded:**\n\n")
        rules_text = ''
        for index, rule in enumerate(rules_list):
            if (index + 1) % 5:
                rules_text += f'**{index + 1}**. {RulesTable.serialize(rule)}\n\n'
            else:
                rules_text += f'**{index + 1}**. {RulesTable.serialize(rule)}\n\n'
                # print each 10 rules
                await tg_client.send_message(Config.app_channel_id, rules_text)
                rules_text = ''

        if len(rules_text):
            # print last group of rules
            await tg_client.send_message(Config.app_channel_id, rules_text)

        rules_text = "**I'm ready to work.**\nSend me a 'help' command for information about control commands."
        await tg_client.send_message(Config.app_channel_id, rules_text)
        return res


async def main():
    await db.create_tables()

    await reload_filters()
    await tg_client.run_until_disconnected()


def check_black_list(text: str, black_list: str):
    """
    Check each word in text (case-insensitive) and if one found in black list return boolean result
    :param text: text for checking
    :param black_list: forbidden list
    :return: True means that All words in the message have been verified, False - was found
    """
    if len(black_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        bl_list = black_list.lower().split('|')
        res = flt(strings, bl_list)
        if len(res):
            return False
    return True


def check_or_list(text: str, or_list: str):
    """
    (case-insensitive)
    :param text: text for checking
    :param or_list: a list of words, at least one of which must be found in the text
    :return: Returns True if at least one word from the list is found in the text
    """
    if len(or_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        ors = or_list.lower().split('|')
        res = flt(strings, ors)
        return len(res)
    return True


def check_for_and(text: str, and_list: str):
    """
    (case-insensitive)
    :param text: text for checking
    :param and_list: List of words that must be in the text
    :return: Returns True if all words from the list are found in the text
    """
    if len(and_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        and_words_list = and_list.lower().split('+')
        for and_word in and_words_list:
            if len(flt(strings, [and_word])) == 0:
                return False
    return True


@tg_client.on(events.NewMessage())
async def normal_handler(event):
    # check the commands sent to Config.app_channel
    if event.chat_id == Config.app_channel_id:
        text: str = event.message.text.lower().replace(' ', '')
        if text == 'help':
            help_text = f"**Hello {Config.owner_name}!**\n" \
                        f"You can use the following commands to control:\n\n"\
                        f"cmd:my dialogs - show all the dialogs/conversations that you are part of;\n\n" \
                        f"cmd:export rules - export rules definition into CSV file;\n\n" \
                        f"cmd:import rules - import rules CSV file into database;\n\n" \
                        f"cmd:restart reload - reload rules from database;\n\n"
            await tg_client.send_message(Config.app_channel_id, help_text)
            return True
        if text == 'cmd:mydialogs':
            # export all the dialogs/conversations that you are part of:
            channels = []
            groups = []
            users = []
            my_dialogs = ""
            async for dialog in tg_client.iter_dialogs():
                if dialog.is_group:
                    groups.append(f"**{len(groups)+1}**. gr: {dialog.name}\t id: **{dialog.id}**\n")
                elif dialog.is_channel:
                    channels.append(f"**{len(channels)+1}**. ch: {dialog.name}\t id: **{dialog.id}**\n")
                elif dialog.is_user:
                    users.append(f"**{len(users)+1}**. user: {dialog.name}\t id: **{dialog.id}**\n")

            # print dialogs list
            # await tg_client.send_message(Config.app_channel_id, f"+++ **Channels** +++\n")
            my_dialogs = ''
            for index, item in enumerate(channels):
                my_dialogs += item
                if (index+1) % 10 == 0:
                    await tg_client.send_message(Config.app_channel_id, my_dialogs)
                    my_dialogs = ''
            if len(my_dialogs):
                await tg_client.send_message(Config.app_channel_id, my_dialogs)

            # await tg_client.send_message(Config.app_channel_id, f"\n+++ **Groups** +++\n")
            my_dialogs = ''
            for index, item in enumerate(groups):
                my_dialogs += item
                if (index+1) % 10 == 0:
                    await tg_client.send_message(Config.app_channel_id, my_dialogs)
                    my_dialogs = ''
            if len(my_dialogs):
                await tg_client.send_message(Config.app_channel_id, my_dialogs)

            # await tg_client.send_message(Config.app_channel_id, f"\n+++ **Users** +++\n")
            my_dialogs = ''
            for index, item in enumerate(users):
                my_dialogs += item
                if (index+1) % 10 == 0:
                    await tg_client.send_message(Config.app_channel_id, my_dialogs)
                    my_dialogs = ''
            if len(my_dialogs):
                await tg_client.send_message(Config.app_channel_id, my_dialogs)
            return True
        if text == 'cmd:exportrules':
            await cmd_export_rules(db, tg_client)
            return True
        if text == 'cmd:importrules':
            current_state["wait_for_rules_csv"] = True
            await tg_client.send_message(Config.app_channel_id, f"**Hello {Config.owner_name}!**\nUpload CSV file with "
                                                                f"new rules here and I'll import it into the database.")
            return True

        if event.message.document and (event.message.document.mime_type == 'text/comma-separated-values'
                                       or event.message.document.mime_type == 'text/csv'):
            if current_state.get("wait_for_rules_csv"):
                doc = event.message.document
                await cmd_import_rules(db, tg_client, doc)
                await reload_filters()
                current_state["wait_for_rules_csv"] = False
                return True
            else:
                await tg_client.send_message(Config.app_channel_id, "Unwanted operation detected. "
                                                                    "If you want to send me a CSV file with new rules, "
                                                                    "then you must use the command: cmd:import rules")
                return False

        if event.message.text == 'cmd:restart reload':
            # in any case reload filters from database
            return await reload_filters()

        return False
    # now, lets filter all other messages
    for rule in rules_list:
        # print(f'{event.chat_id=}')
        if rule.status != 'active':
            continue
        # print(f'{event.chat_id=} - is active')
        if rule.donor_id == event.chat_id:
            if event.is_group:
                username = ''
                firstname = ''
                lastname = ''
                sender_id = 0
                is_found = False
                if event.message and event.message.sender and type(event.message.sender) == User:
                    username = event.message.sender.username if event.message.sender.username else ''
                    firstname = event.message.sender.first_name if event.message.sender.first_name else ''
                    lastname = event.message.sender.last_name if event.message.sender.last_name else ''
                    sender_id = event.message.sender_id or 0
                    is_found = False
                else:
                    # print("WARNING: event.message.sender not found")
                    is_found = True
                    # continue

                if rule.sender_id == 0 and rule.sender_uname == '' and \
                   rule.sender_fname == '' and rule.sender_lname == '':
                    is_found = True  # just for exclude sender checking
                    # print("no sender properties, lets check the filter now")
                if not is_found:
                    # print("lets check sender properties")
                    if event.message.sender_id == rule.sender_id:
                        is_found = True
                    else:
                        if username and username == rule.sender_uname:
                            is_found = True
                        if firstname and firstname == rule.sender_fname:
                            is_found = True
                        if lastname and lastname == rule.sender_lname:
                            is_found = True
                if is_found:
                    # check black_list, and_list and or_list
                    if not check_black_list(event.message.text, rule.black_list):
                        continue
                    if not check_or_list(event.message.text, rule.or_list):
                        continue
                    if not check_for_and(event.message.text, rule.and_list):
                        continue

                    # check filter now
                    is_found = check_filter(event.message.text, rule.filter)
                try:
                    if is_found:
                        if len(username) > 0:
                            username = username if username.startswith("@") else f"@{username}"

                        format_string = "m" if len(rule.format) == 0 else rule.format.lower()
                        title_info = ''
                        donor_info = ''
                        sender_info = ''
                        message_body = ''

                        if 't' in format_string:
                            title_info = f'**{rule.title}**\n' if len(rule.title) else f'**flt: {rule.filter}**\n'
                        if 'd' in format_string:
                            donor_info = f'**{rule.donor_name}** id:{rule.donor_id}\n'
                        if 's' in format_string:
                            sender_info = f'**{firstname} {lastname}** {username} id:{sender_id}\n'

                        if title_info or donor_info or sender_info:
                            message_body += f'{title_info}{donor_info}{sender_info}' + \
                                            f'@t.me/c/{event.message.peer_id.channel_id}/{event.message.id}\n' \
                                            f'----------\n'

                        if 'm' not in format_string:
                            await tg_client.send_message(rule.recip_id, message_body)
                        else:
                            if not Config.enable_forbidden_content:
                                if event.message.chat and event.message.chat.noforwards:
                                    message_body += f"Forwards restricted saving content from chat " \
                                                    f"{event.chat_id} is forbidden."
                                    await tg_client.send_message(rule.recip_id, message_body)
                                    continue
                            message_body += event.message.text
                            event.message.text = message_body
                            await tg_client.send_message(rule.recip_id, event.message)

                # Это просто пример как обрабатывать ошибки telethon
                # except (errors.SessionExpiredError, errors.SessionRevokedError):
                #         self._logger.critical(
                #             "The user's session has expired, "
                #             "try to get a new session key (run login.py)"
                #         )
                except Exception as e:
                    await tg_client.send_message(Config.app_channel_id,
                                                 f"{'Error!'} \n{str(e)}\n"
                                                 f"{rule.title}\n"
                                                 f"R: {rule.recip_id}\n"
                                                 f"D: {rule.donor_id}")
                finally:
                    continue
            else:
                try:
                    if not check_black_list(event.message.text, rule.black_list):
                        continue
                    if not check_or_list(event.message.text, rule.or_list):
                        continue
                    if not check_for_and(event.message.text, rule.and_list):
                        continue

                    # check filter
                    if check_filter(event.message.text, rule.filter):
                        # format_parts = sender["repost_format"].lower().split(" ")
                        title_info = ''
                        donor_info = ''
                        message_body = ''

                        format_string = "m" if len(rule.format) == 0 else rule.format.lower()
                        if 't' in format_string:
                            title_info = f'**{rule.title}**\n' if len(rule.title) else f'**flt: {rule.filter}**\n'
                        if 'd' in format_string:
                            donor_info = f'**{rule.donor_name}** id:{rule.donor_id}\n'

                        if title_info or donor_info:
                            message_body += f'{title_info}{donor_info}'
                            if event.is_private:
                                message_body += f'@t.me/c/{event.message.peer_id.user_id}/{event.message.id}\n'
                            else:
                                message_body += f'@t.me/c/{event.message.peer_id.channel_id}/{event.message.id}\n'
                            message_body += f'----------\n'

                        if 'm' not in format_string:
                            await tg_client.send_message(rule.recip_id, message_body)
                        else:
                            if not Config.enable_forbidden_content:
                                if event.message.chat and event.message.chat.noforwards:
                                    message_body += f"Forwards restricted saving content from chat " \
                                                    f"{event.chat_id} is forbidden."
                                    await tg_client.send_message(rule.recip_id, message_body)
                                    continue
                            message_body += event.message.text
                            event.message.text = message_body
                            await tg_client.send_message(rule.recip_id, event.message)

                except Exception as e:
                    await tg_client.send_message(Config.app_channel_id,
                                                 f"{'Error!'} \n{str(e)}\n{rule.recip_id}")
                finally:
                    continue

if __name__ == '__main__':
    with tg_client:
        tg_client.start()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
