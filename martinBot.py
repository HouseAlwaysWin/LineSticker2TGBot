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
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
from telegram import Sticker
from PIL import Image
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      InlineKeyboardButton, InlineKeyboardMarkup)


lang = {}
with open('lang.json', 'r', encoding='utf-8') as l:
    lang = json.load(l)
current_lang = lang["en"]

temp_sticker_title = ''

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

SETSTICKER_NAME, FIRST, SECOND, SETLANG = range(4)

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
                InlineKeyboardButton(
                current_lang["cancel"], callback_data=str(CANCEL))]
        ])


def start(update, context):
    user = update.message.from_user

    set_start_keyboard()
    update.message.reply_text(
        current_lang["start_msg"],
        reply_markup=start_markup
    )
    return FIRST


def lang_choose(update, context):
    keyboard = [
        [InlineKeyboardButton(
            current_lang["english"], callback_data="en"),
         InlineKeyboardButton(
            current_lang["chinese"], callback_data="zh-tw"),
         InlineKeyboardButton(
            current_lang["back"], callback_data="^"+str(BACK)+"$")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    lang_select = context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["choose_lang"],
        reply_markup=reply_markup
    )
    return SETLANG


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
    return FIRST


def back_to_start(update, context):

    context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["start_msg"],
        reply_markup=start_markup
    )

    return FIRST


def line_sticker_transfer(update, context):
    try:
        lid = re.search('\d+', update.message.text).group(0)
        if not lid:
            return SECOND

        sticker_url = config["Default"]["LineStickerUrl"]

        response = requests.get(
            sticker_url.format(lid), stream=True)
        with open("img.zip", 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

        tmp_path = f'./imgs/{str(uuid.uuid4()).replace("-","")}'
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        with zipfile.ZipFile('img.zip', 'r') as zip_ref:
            zip_ref.extractall(tmp_path)
        os.remove('img.zip')
        imglist = [img for img in os.listdir(
            tmp_path) if re.match('^\d+@2x.png', img)]

        update.message.reply_text(
            current_lang["start_transfering"]
        )
        files = []
        total_img = len(imglist)
        img_count = 0

        update_msg = update.message.reply_text(
            current_lang["transfer_processing_start"]
        )
        for img in imglist:

            im = Image.open(f'{tmp_path}/{img}')
            im_resize = im.resize((512, 512))
            im_resize.save(f'{tmp_path}/{img}')

            with open(f'{tmp_path}/{img}', 'rb') as png_sticker:
                file = context.bot.upload_sticker_file(
                    user_id=update.message.chat_id,
                    png_sticker=png_sticker)
                files.append(file)
                img_count += 1
                context.bot.edit_message_text(
                    chat_id=update_msg.chat_id,
                    message_id=update_msg.message_id,
                    # text=f"Transfer processing...{'%.2f' % ((img_count/total_img)*100)}%\n轉換中...{'%.2f' % ((img_count/total_img)*100)}%"
                    text=current_lang["transfer_proecssing"].format('%.2f' % ((img_count/total_img)*100)
                                                                    ))

        shutil.rmtree(tmp_path)

        emoji = 0x1f601
        emostr = struct.pack('<I', emoji).decode('utf-32le')
        tempName = f"bot{str(uuid.uuid4()).replace('-', '')}_by_martinwangBot"
        context.bot.create_new_sticker_set(
            user_id=update.message.chat_id,
            name=tempName,
            title=temp_sticker_title,
            png_sticker=files[0].file_id,
            emojis=emostr,
        )

        count = 0
        for file in files:
            emostr = struct.pack('<I', emoji+count).decode('utf-32le')
            context.bot.add_sticker_to_set(
                user_id=update.message.chat_id,
                name=tempName,
                png_sticker=files[count].file_id,
                emojis=emostr
            )
            count += 1

        stickerSet = context.bot.get_sticker_set(
            name=tempName
        )

        sticker = stickerSet.stickers[0]

        context.bot.edit_message_text(
            chat_id=update_msg.chat_id,
            message_id=update_msg.message_id,
            text=current_lang["finish_transfer"])

        context.bot.send_sticker(
            chat_id=update.message.chat_id,
            sticker=sticker.file_id
        )

    except:
        traceback.print_exc()
        return SECOND


def ask_set_line_sticker_title(update, context):
    context.bot.edit_message_text(
        chat_id=update.callback_query.message.chat_id,
        message_id=update.callback_query.message.message_id,
        text=current_lang["send_me_line_sticker_title"],
    )
    return SETSTICKER_NAME


def set_line_sticker_title(update, context):
    global temp_sticker_title
    temp_sticker_title = update.message.text
    context.bot.send_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id,
        text=current_lang["send_me_line_sticker_msg"],
    )

    return SECOND


def set_line_sticker_title_error(update, context):
    context.bot.send_message(
        chat_id=update.message.chat_id,
        message_id=update.message.message_id,
        text=current_lang["send_me_line_sticker_title_error"],
    )
    return SETSTICKER_NAME


def line_sticker(update, context):
    query = update.callback_query
    bot = context.bot
    bot.send_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id,
        text=current_lang["send_me_line_sticker_msg"],
    )

    return SECOND


def line_sticker_error(update, context):
    update.message.reply_text(
        current_lang["give_me_correct_line_link"]
    )
    return SECOND


def cancel(update, context):
    return ConversationHandler.END


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
            FIRST: [
                CallbackQueryHandler(
                    ask_set_line_sticker_title, pattern='^' + str(LINE) + '$'),
                CallbackQueryHandler(
                    lang_choose, pattern='^' + str(LANG) + '$'),
                CallbackQueryHandler(cancel, pattern='^' + str(CANCEL) + '$'),
            ],
            SECOND: [
                MessageHandler(
                    Filters.regex('^https://store.line.me/stickershop/product/\d+/.*'), line_sticker_transfer),
                MessageHandler(Filters.regex('^' + str(CANCEL) + '$'), cancel),
                MessageHandler(Filters.regex('.*'), line_sticker_error)],
            SETLANG: [
                CallbackQueryHandler(back_to_start, pattern='^'+str(BACK)+'$'),
                CallbackQueryHandler(set_lang, pattern='.*'),
            ],
            SETSTICKER_NAME: [
                MessageHandler(Filters.regex(
                    '^.{1,20}$'), set_line_sticker_title),
                MessageHandler(Filters.text, set_line_sticker_title_error),
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
