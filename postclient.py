from typing import Any

from telethon import TelegramClient, events, errors
import asyncio
import logging
import re

from database.rules_io import cmd_export_rules, cmd_import_rules
from shared.config import Config
from database.orm_sqlite3 import Database
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
    # rules = await db.get_rules_table().get_rules()
    # # check for special rule where rule.recip_id equals to rule.donor_id and equals to Config.app_channel_id
    # # and rule.filter contains text 'cmd:restart*'
    # special_rule = {
    #     "recip_id": Config.app_channel_id,
    #     "donor_id": Config.app_channel_id,
    #     "filter": 'cmd:restart*',
    #     "is_found": False
    # }
    # for rule in rules:
    #     if rule.recip_id == special_rule["recip_id"] \
    #             and rule.donor_id == special_rule["donor_id"] \
    #             and rule.filter == special_rule["filter"]:
    #         special_rule["is_found"] = True
    #     rules_list.append(rule)
    # # if special rule isn't found, append it!
    # if not special_rule["is_found"]:
    #     special_row: list = [
    #         Config.app_channel_name, Config.app_channel_id,
    #         Config.app_channel_name, Config.app_channel_id,
    #         '', '', '', 0,
    #         special_rule["filter"],
    #         '', '', '', 'M', 'Special channel',
    #         'active', Config.owner_id
    #     ]
    #     rule = db.get_rules_table().convert_to_model_obj(special_row)
    #     rules_list.append(rule)
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
        rules_text = f"**{len(rules_list)} rules data loaded:**\n\n"
        for rule in rules_list:
            rules_text += f'{rule}\n\n'
        rules_text += "**I'm ready to work.**\nSend me a 'help' command for information about control commands."
        await tg_client.send_message(Config.app_channel_id, rules_text)
        return res


async def main():
    await db.create_tables()

    await reload_filters()
    await tg_client.run_until_disconnected()


def check_black_list(text: str, black_list: str):
    """
    Check each word in text and if one found in black list return boolean result
    :param text: text for checking
    :param black_list: forbidden list
    :return: True means that All words in the message have been verified, No - was found
    """
    if len(black_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        bl_list = black_list.split('|')
        res = flt(strings, bl_list)
        if len(res):
            return False
    return True


def check_or_list(text: str, or_list: str):
    """
    :param text: text for checking
    :param or_list: a list of words, at least one of which must be found in the text
    :return: Returns True if at least one word from the list is found in the text
    """
    if len(or_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        ors = or_list.split('|')
        res = flt(strings, ors)
        return len(res)
    return True


def check_for_and(text: str, and_list: str):
    """
    :param text: text for checking
    :param and_list: List of words that must be in the text
    :return: Returns true if all words from the list are found in the text
    """
    if len(and_list):
        opt = re.sub(r'[^\w\s]', '', text)  # remove all punctuations from string
        strings = opt.lower().split()
        and_words_list = and_list.split('+')
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
                    groups.append(f"{dialog.name} has ID **{dialog.id}**\n")
                elif dialog.is_channel:
                    channels.append(f"{dialog.name} has ID **{dialog.id}**\n")
                elif dialog.is_user:
                    users.append(f"{dialog.name} has ID **{dialog.id}**\n")

            my_dialogs += f"+++ **Channels** +++\n"
            for item in channels:
                my_dialogs += item
            my_dialogs += f"\n+++ **Groups** +++\n"
            for item in groups:
                my_dialogs += item
            my_dialogs += f"\n+++ **Users** +++\n"
            for item in users:
                my_dialogs += item

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
        if rule.status != 'active':
            continue
        if rule.donor_id == event.chat_id:
            if event.is_group:
                username = ''
                firstname = ''
                lastname = ''
                sender_id = 0
                is_found = False
                if event.message and event.message.sender:
                    username = event.message.sender.username or ''
                    firstname = event.message.sender.first_name or ''
                    lastname = event.message.sender.last_name or ''
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
                        channel_info = ''

                        if 't' in format_string:
                            title_info = f'**{rule.title}**\n'
                        if 'd' in format_string:
                            donor_info = f'**{rule.donor_name}\n{rule.donor_id}\n**'
                        if 's' in format_string:
                            sender_info = f'**{firstname} {lastname}** {username} id:{sender_id}\n----------\n'

                        if len(title_info) or len(donor_info) or len(sender_info):
                            # await tg_client.send_message(rule.recip_id, f'{title_info}{donor_info}{sender_info}')
                            channel_info += f'**{event.chat_id}**\n\n'

                        if 'm' in format_string:
                            if not Config.enable_forbidden_content:
                                if event.message.chat and event.message.chat.noforwards:
                                    await tg_client.send_message(rule.recip_id, f"Forwards restricted saving content "
                                                                                f"from chat {event.chat_id} is not "
                                                                                f"supported.")
                                    return False
                            message_body = event.message.text
                            # await tg_client.send_message(rule.recip_id, event.message)
                        event.message.text = f'{title_info}{donor_info}{sender_info}{channel_info}{message_body}'
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
                        channel_info = ''
                        message_body = ''

                        format_string = "m" if len(rule.format) == 0 else rule.format.lower()
                        if 't' in format_string:
                            title_info = f'**{rule.title}**\n'
                        if 'd' in format_string:
                            donor_info = f'**{rule.donor_name}\n{rule.donor_id}\n**'

                        if len(title_info) or len(donor_info):
                            channel_info += f'{event.chat_id}\n'
                            # await tg_client.send_message(rule.recip_id, f'{title_info}{donor_info}')
                        if 'm' in format_string:
                            if not Config.enable_forbidden_content:
                                if event.message.chat and event.message.chat.noforwards:
                                    await tg_client.send_message(rule.recip_id, f"Forwards restricted saving content "
                                                                                f"from chat {event.chat_id} is not "
                                                                                f"supported.")
                                    return False
                            message_body += event.message.text
                        event.message.text = f'{title_info}{donor_info}{channel_info}{message_body}'
                        # await tg_client.send_message(rule.recip_id, event.message)
                        await tg_client.send_message(rule.recip_id, event.message)

                except Exception as e:
                    await tg_client.send_message(Config.app_channel_id,
                                                 f"{'Error!'} \n{str(e)}\n{rule.recip_id}")

if __name__ == '__main__':
    with tg_client:
        tg_client.start()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
