import logging
import requests
import shutil
import zipfile
import struct
import os
import re
import traceback
import uuid
import subprocess
import configparser
import glob
import json
import base64
import pickle
from io import BytesIO, TextIOWrapper
from urllib.request import urlopen
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import Sticker
from PIL import Image
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      InlineKeyboardButton, InlineKeyboardMarkup)       

# Language Setting
lang = {}
with open('lang.json', 'r', encoding='utf-8') as l:
    lang = json.load(l)
current_lang = lang["en"]

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

SET_STICKER_TITLE, MENU, LINE_STICKER_TRANSFER, SET_LANG = range(4)

LINE, CANCEL, LANG, BACK = range(4)

start_markup = {}


def set_start_keyboard():
    global start_markup
    start_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                current_lang["line_sticker_transfer_btn"], callback_data=str(LINE)),
                InlineKeyboardButton(
                current_lang["language_setting"], callback_data=str(LANG)),
             ]
        ])


def start(update, context):
    user = update.message.from_user
    global current_lang
    if update.effective_user.language_code in lang:
        current_lang = lang[update.effective_user.language_code]

    set_start_keyboard()
    update.message.reply_text(
        current_lang["start_msg"],
        reply_markup=start_markup
    )
    return MENU


def lang_choose(update, context):
    keyboard = [
        [InlineKeyboardButton(
            current_lang["english"], callback_data="en"),
         InlineKeyboardButton(
            current_lang["chinese"], callback_data="zh-hant"),
         InlineKeyboardButton(
            current_lang["back"], callback_data=str(BACK))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    lang_select = context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["choose_lang"],
        reply_markup=reply_markup
    )
    return SET_LANG


def set_lang(update, context):
    lang_val = update.callback_query.data
    global current_lang
    current_lang = lang[lang_val]

    set_start_keyboard()

    context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["start_msg"],
        reply_markup=start_markup
    )
    return MENU


def back_to_start(update, context):

    context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["start_msg"],
        reply_markup=start_markup
    )

    return MENU


def line_sticker_transfer(update, context):
    try:
        lid = re.search('\d+', update.message.text).group(0)
        if not lid:
            return LINE_STICKER_TRANSFER

        sticker_url = config["Default"]["LineStickerUrl"]
        resp = requests.get(
            sticker_url.format(lid), stream=True)
        
        files = []
        process_count = 0
        update.message.reply_text(
            current_lang["start_transfering"])

        with zipfile.ZipFile(BytesIO(resp.content)) as archive:
            file_list = [file for file in archive.infolist() if re.match('^\d+@2x.png', file.filename)]
            total_process_count = len(file_list)
            transfer_processing_start = update.message.reply_text(
                current_lang["transfer_processing_start"])
            for entry in file_list:
                with archive.open(entry) as file:
                        img = Image.open(file)
                        img_resize = img.resize((512, 512))
                        buff = BytesIO()
                        img_resize.save(buff,"png")
                        buff.seek(0)
                        file = context.bot.upload_sticker_file(
                            user_id=update.message.chat_id,
                            png_sticker=buff)
                        files.append(file)
                        process_count += 1
                        context.bot.edit_message_text(
                            chat_id=transfer_processing_start.chat_id,
                            message_id=transfer_processing_start.message_id,
                            text=current_lang["transfer_processing"].format('%.2f' % ((process_count/total_process_count)*100))
                        )
        update.message.reply_text(
            current_lang["transfer_finish"])
        emoji = 0x1f601
        emostr = struct.pack('<I', emoji).decode('utf-32le')
        botname = config["Default"]["BotName"]
        tempName = f"bot{str(uuid.uuid4()).replace('-', '')}_by_{botname}"
        user_data = context.user_data
        context.bot.create_new_sticker_set(
            user_id=update.message.chat_id,
            name=tempName,
            title=user_data['line_sticker_title'],
            png_sticker=files[0].file_id,
            emojis=emostr,
        )
        del user_data['line_sticker_title']
        start_upload_msg = update.message.reply_text(
            current_lang["start_uploading"])

        upload_process_count = 0
        upload_process_total = len(files)
        for file in files:
            emostr = struct.pack('<I', emoji+upload_process_count).decode('utf-32le')
            context.bot.add_sticker_to_set(
                user_id=update.message.chat_id,
                name=tempName,
                png_sticker=files[upload_process_count].file_id,
                emojis=emostr
            )
            upload_process_count += 1
            context.bot.edit_message_text(
                            chat_id=start_upload_msg.chat_id,
                            message_id=start_upload_msg.message_id,
                            text=current_lang["upload_processing"].format('%.2f' % ((upload_process_count/upload_process_total)*100)
                            ))
        update.message.reply_text(
            current_lang["finish_uploading"])

        stickerSet = context.bot.get_sticker_set(
            name=tempName
        )

        sticker = stickerSet.stickers[0]

        update.message.reply_text(
            current_lang["finish_msg"])

        context.bot.send_sticker(
            chat_id=update.message.chat_id,
            sticker=sticker.file_id
        )
        return MENU
    except:
        traceback.print_exc()
        return MENU


def ask_set_line_sticker_title(update, context):

    back_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                current_lang["back"], callback_data=str(BACK))]
        ])
    context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["ask_set_line_sticker_title"],
        reply_markup=back_markup
    )
    return SET_STICKER_TITLE


def set_line_sticker_title(update, context):
    
    user_data = context.user_data
    user_data['line_sticker_title'] = update.message.text

    back_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                current_lang["back"], callback_data=str(BACK))]
        ])
    context.bot.send_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id,
        text=current_lang["send_me_line_sticker_url"],
        reply_markup=back_markup
    )

    return LINE_STICKER_TRANSFER


def set_line_sticker_title_error(update, context):
    back_markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(
                current_lang["back"], callback_data=str(BACK))]
        ])
    context.bot.send_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id,
        text=current_lang["set_line_sticker_title_error"],
        reply_markup=back_markup
    )
    return SET_STICKER_TITLE


def line_sticker(update, context):
    query = update.callback_query
    bot = context.bot
    bot.send_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=current_lang["send_me_line_sticker_msg"],
    )

    return LINE_STICKER_TRANSFER


def line_sticker_error(update, context):
    update.message.reply_text(
        current_lang["give_me_correct_line_link"]
    )
    return LINE_STICKER_TRANSFER


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():

    updater = Updater(
        config["Default"]["BotApiKey"], use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                CallbackQueryHandler(
                    ask_set_line_sticker_title, pattern='^' + str(LINE) + '$'),
                CallbackQueryHandler(
                    lang_choose, pattern='^' + str(LANG) + '$'),
            ],
            LINE_STICKER_TRANSFER: [
                MessageHandler(
                    Filters.regex('^https://store.line.me/stickershop/product/\d+/.*'), line_sticker_transfer),
                MessageHandler(
                    Filters.regex('^https://store.line.me/officialaccount/event/sticker/\d+/.*'), line_sticker_transfer),
                CallbackQueryHandler(
                    back_to_start, pattern='^' + str(BACK) + '$'),
                MessageHandler(Filters.regex('.*'), line_sticker_error)],
            SET_LANG: [
                CallbackQueryHandler(
                    back_to_start, pattern='^' + str(BACK) + '$'),
                CallbackQueryHandler(set_lang, pattern='.*'),
            ],
            SET_STICKER_TITLE: [
                MessageHandler(Filters.regex(
                    '^.{1,64}$'), set_line_sticker_title),
                MessageHandler(Filters.text, set_line_sticker_title_error),
                CallbackQueryHandler(
                    back_to_start, pattern='^' + str(BACK) + '$')
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
