import logging
import requests
import shutil
import zipfile

import os
import re
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from PIL import Image


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)
    emo = 0x1f601;
    a = chr(emo).encode('utf-16')
    print(a)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def download(update, context):
    response = requests.get(
        "http://dl.stickershop.line.naver.jp/products/0/0/1/1349688/iphone/stickers@2x.zip", stream=True)
    with open("img.zip", 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response

    path = './imgs'
    with zipfile.ZipFile('./img.zip', 'r') as zip_ref:
        zip_ref.extractall(path)
    imglist = os.listdir('./imgs')
    for img in imglist:
        if re.match('^\d+@2x.png', img):
            im = Image.open(f'./imgs/{img}')
            im_resize = im.resize((512, 512))
            im_resize.save(f'./imgs/{img}')


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(
        "", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("download", download))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
