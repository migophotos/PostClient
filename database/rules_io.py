import csv
import io
import re

from telethon import TelegramClient
from telethon.tl.types import Document

from database.orm_sqlite3 import Database
from shared.config import Config


async def cmd_export_rules(db: Database, tg_client: TelegramClient):
    rules = await db.get_rules_table().get_rules()
    trash_bin_found = False
    rows = [
        ["recip_name", "recip_id", "donor_name", "donor_id",
         "sender_fname", "sender_sname", "sender_uname", "sender_id",
         "filter", "black_list", "and_list", "or_list", "format", "title", "status",
         "user_id", "uid"]
    ]
    for rule in rules:
        row = [
            rule.recip_name, rule.recip_id, rule.donor_name, rule.donor_id,
            rule.sender_fname, rule.sender_lname, rule.sender_uname, rule.sender_id,
            rule.filter, rule.black_list, rule.and_list, rule.or_list,
            rule.format, rule.title, rule.status, rule.user_id, rule.uid
        ]
        if not trash_bin_found and rule.title == '__trash_bin__':
            trash_bin_found = True
        rows.append(row)
    if not trash_bin_found:
        rows.append(['', 0, '', 0, '', '', '', 0, '', '', '', '', '', '__trash_bin__', '', Config.owner_id, len(rules)+1])
    rows.append([
        "Insert filter definitions before this row"
    ])
    try:
        rules_csv_file = "./rules.csv"
        with open(rules_csv_file, "w", encoding="utf8", newline="\n") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(rows)

        await tg_client.send_file(Config.app_channel_id, rules_csv_file, caption="Rules for Google Sheet")

    except Exception as e:
        await tg_client.send_message(Config.app_channel_id,
                                     f"Error: {str(e)}\nContact the author: @MigoPhotos")


async def cmd_import_rules(db: Database, tg_client: TelegramClient, document: Document):
    doc_data = await tg_client.download_file(document)
    file = io.BytesIO(doc_data)
    file.seek(0)
    cat_list_csv = str(file.read(), encoding='utf-8')
    cat_list = re.findall(r'.*\n', cat_list_csv)
    cat_list.pop(0)
    csv_data = csv.reader(cat_list)

    rt = db.get_rules_table()
    await rt.delete_all_rules()

    new_rules_count = 0
    for row in csv_data:
        if len(row) != 17:
            continue

        data = {}
        recip_name, recip_id, donor_name, donor_id, sender_fname, sender_lname, sender_uname, \
            sender_id, rule_filter, black_list, and_list, or_list, rule_format, title, status, user_id, uid = row

        if recip_name != '__trash_bin__':
            if recip_id == '' or donor_id == '':
                await tg_client.send_message(Config.app_channel_id,
                                             f'Recipient ID {recip_id} or Donor ID {donor_id} cannot be empty! Skipped')
                continue

            # Very Important check: the recipient channel link must not be the same as the donor channel link,
            # excluding link to special channel, which can only be created by system administrator!
            if recip_id == donor_id:
                await tg_client.send_message(Config.app_channel_id,
                    f'Skipped rule: {recip_id} == {donor_id} - matching input and output channels are prohibited!')
                continue

        # check and convert str to int
        if recip_id.startswith('100'):
            recip_id = int(f'-{recip_id}') if not recip_id.startswith('-') else int(recip_id)
        else:
            recip_id = int(recip_id)

        if donor_id.startswith('100'):
            donor_id = int(f'-{donor_id}') if not donor_id.startswith('-') else int(donor_id)
        else:
            donor_id = int(donor_id) if donor_id else 0

        sender_id = int(sender_id) if sender_id.isdigit() else 0
        user_id = int(user_id) if user_id.isdigit() else 0

        data["recip_name"] = recip_name
        data["recip_id"] = recip_id
        data["donor_name"] = donor_name
        data["donor_id"] = donor_id
        data["sender_fname"] = sender_fname
        data["sender_lname"] = sender_lname
        data["sender_uname"] = sender_uname
        data["sender_id"] = sender_id
        data["filter"] = rule_filter
        data["black_list"] = black_list
        data["and_list"] = and_list
        data["or_list"] = or_list
        data["format"] = rule_format or 'M'
        data["title"] = title
        data["status"] = status
        data["user_id"] = user_id

        await rt.add_rule(data)
        new_rules_count += 1

    await tg_client.send_message(Config.app_channel_id, f'{new_rules_count} rules was found and stored in database\n')
    return True

