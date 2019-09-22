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
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from telegram import Sticker
from PIL import Image
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

CHOOSING, LINE, LINEREPLY = range(3)

reply_keyboard = [
    ['Line Sticker Transfer', 'Cancel']
]

markup = ReplyKeyboardMarkup(reply_keyboard)


def start(update, context):
    update.message.reply_text(
        "Welcome to use my bot,please choose function to use"
        "Please,Choose functions you want to use...",
        reply_markup=markup
    )
    return CHOOSING


def line_sticker_transfer(update, context):
    try:
        lid = re.search('\d+', update.message.text).group(0)
        if not lid:
            return LINEREPLY

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
            "Start tranfer...")
        files = []
        total_img = len(imglist)
        img_count = 0
        for img in imglist:

            # if re.match('^\d+@2x.png', img):
            update.message.reply_text(
                f"proecssing...{'%.2f' % ((img_count/total_img)*100)}")

            im = Image.open(f'{tmp_path}/{img}')
            im_resize = im.resize((512, 512))
            im_resize.save(f'{tmp_path}/{img}')

            with open(f'{tmp_path}/{img}', 'rb') as png_sticker:
                file = context.bot.upload_sticker_file(
                    user_id=update.message.chat_id,
                    png_sticker=png_sticker)
                files.append(file)
                img_count += 1
        shutil.rmtree(tmp_path)

        emoji = 0x1f601
        emostr = struct.pack('<I', emoji).decode('utf-32le')
        tempName = f"bot{str(uuid.uuid4()).replace('-', '')}_by_martinwangBot"
        context.bot.create_new_sticker_set(
            user_id=update.message.chat_id,
            name=tempName,
            title='test',
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
        context.bot.send_sticker(
            chat_id=update.message.chat_id,
            sticker=sticker.file_id
        )
    except:
        traceback.print_exc()
        return LINE


def line_sticker_transfer_default(update, context):
    update.message.reply_text(
        "Please give me a line sticker link",
        reply_markup=markup
    )
    return LINE


def line_sticker_transfer_failed(update, context):
    update.message.reply_text(
        "Please give a correct link !!",
        reply_markup=markup
    )
    return LINE


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
        entry_points=[CommandHandler('start', start), MessageHandler(Filters.text, start)
                      ],
        states={
            CHOOSING: [
                MessageHandler(Filters.regex('^(Line Sticker Transfer)$'),
                               line_sticker_transfer_default),
                MessageHandler(Filters.regex('^Cancel$'), cancel),
                MessageHandler(Filters.text, start)
            ],
            LINE: [
                MessageHandler(Filters.regex('^https://store.line.me/stickershop/product/\d+/.*'),
                               line_sticker_transfer),
                MessageHandler(Filters.regex('^Cancel$'), cancel),
                MessageHandler(Filters.text, line_sticker_transfer_default)
            ],
            LINEREPLY: [
                MessageHandler(Filters.regex('^(Failed)$'),
                               line_sticker_transfer_failed)
            ]
        },
        fallbacks=[
            MessageHandler(Filters.regex('^Cancel$'), cancel)
        ]
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
