import os
import logging
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from handlers.menu import start, menu_handler
from handlers.partner import invite, join, partner_status, unlink
from handlers.movies import add_movie, list_movies, random_movie
from handlers.callbacks import button_handler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Create the Updater
    updater = Updater(os.getenv('TELEGRAM_BOT_TOKEN'))
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("invite", invite))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("add", add_movie))
    dp.add_handler(CommandHandler("list", list_movies))
    dp.add_handler(CommandHandler("random", random_movie))
    dp.add_handler(CommandHandler("partner_status", partner_status))
    dp.add_handler(CommandHandler("unlink", unlink))
    
    # Message & callback handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, menu_handler))
    dp.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()