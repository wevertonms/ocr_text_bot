import json
import os
import tempfile
from pathlib import Path

import pytesseract

import telegram
from telegram.ext import CommandHandler, Dispatcher, Filters, MessageHandler

try:
    from PIL import Image
except ImportError:
    import Image

OK_RESPONSE = {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json"},
    "body": json.dumps("ok"),
}
ERROR_RESPONSE = {"statusCode": 400, "body": json.dumps("Oops, something went wrong!")}
CURDIR = Path(__file__).parent
IMAGES_DIR = CURDIR / Path("photos")
# IMAGES_DIR.mkdir(exist_ok=True)

# DEFAULT_MESSAGE = "Sorry, human! I'm under maintenance. Try again later..."
DEFAULT_MESSAGE = "Please, send me an image with text in it..."


def configure_telegram():
    """
    Configures the bot with a Telegram Token.

    Returns a bot instance.
    """

    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        print("The TELEGRAM_TOKEN must be set")
        raise NotImplementedError

    return telegram.Bot(TELEGRAM_TOKEN)


def default_message(update, _):
    print("Message: %s" % update.message.text)
    update.message.reply_text(DEFAULT_MESSAGE)


def start_command(update, _):
    user_first_name = update.effective_user.first_name
    update.message.reply_text(f"Hello, {user_first_name}!")
    default_message(update, _)


def help_command(update, _):
    text = """Available commands:
- /start to show start message.
- /help to show this list of commands.
"""
    update.message.reply_text(text)


def photo_callback(update, _):
    update.message.reply_text("Hold tight while I process the image...")
    text = DEFAULT_MESSAGE
    photo = update.message.photo[-1].get_file()
    photo_name = photo.file_path.split("/")[-1]
    username = update.effective_user.name
    with tempfile.NamedTemporaryFile(prefix=photo_name) as f:
        file_path = f.name
        # file_path = str((IMAGES_DIR / f"{username}_{photo_name}").absolute())
        print("Downloading file '%s' from %s" % (f, username))
        photo.download(custom_path=file_path)
        image = Image.open(file_path)
    custom_config = "--oem 3 --psm 3"
    text = pytesseract.image_to_string(image, config=custom_config)
    # text = DEFAULT_MESSAGE
    print("Extracted '%s'" % text)
    update.message.reply_text(text)


def webhook(event, _):
    """
    Runs the Telegram webhook.
    """
    print("Event: %s" % event)
    if event.get("httpMethod") == "POST" and event.get("body"):
        bot = configure_telegram()
        update = telegram.Update.de_json(json.loads(event.get("body")), bot)
        main(update, bot)
        print("Message sent")
        return OK_RESPONSE
    return ERROR_RESPONSE


def main(update, bot):
    print("User: %s" % update.effective_user.name)
    dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.photo, photo_callback))
    dispatcher.add_handler(MessageHandler(Filters.text, default_message))
    dispatcher.process_update(update)


def set_webhook(event, _):
    """
    Sets the Telegram bot webhook.
    """

    print("Event: %s", event)
    bot = configure_telegram()
    url = "https://{}/{}/".format(
        event.get("headers").get("Host"),
        event.get("requestContext").get("stage"),
    )
    webhook = bot.set_webhook(url)

    if webhook:
        return OK_RESPONSE

    return ERROR_RESPONSE
