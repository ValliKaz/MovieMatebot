import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from supabase import create_client, Client

# Load environment variables
load_dotenv(override=True)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logger.info(f"/start command received from chat_id: {chat_id}")
    try:
        # Check if user exists
        user = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
        if not user.data:
            supabase.table("users").insert({"chat_id": chat_id}).execute()
            logger.info(f"New user added with chat_id: {chat_id}")
        update.message.reply_text("Welcome to MovieMateBot! Use /invite to pair or /join <code> to connect.")
    except Exception as e:
        logger.error(f"Error in /start: {e}")
        update.message.reply_text("An error occurred while processing your request. Please try again later.")

def invite(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    invite_code = f"INV-{uuid.uuid4().hex[:6]}"
    logger.info(f"Generated invite code {invite_code} for chat_id: {chat_id}")
    supabase.table("users").update({"invite_code": invite_code}).eq("chat_id", chat_id).execute()
    update.message.reply_text(f"Your invite code: {invite_code}")

def join(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logger.info(f"/join command received from chat_id: {chat_id}")
    try:
        invite_code = context.args[0]
        logger.info(f"Attempting to join with invite code: {invite_code}")
        # Find inviter
        inviter = supabase.table("users").select("*").eq("invite_code", invite_code).execute()
        if not inviter.data:
            logger.warning(f"Invalid invite code: {invite_code} from chat_id: {chat_id}")
            update.message.reply_text("Invalid invite code!")
            return
        inviter_id = inviter.data[0]["id"]
        # Update partner_id for both users
        supabase.table("users").update({"partner_id": inviter_id}).eq("chat_id", chat_id).execute()
        supabase.table("users").update({"partner_id": supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]}).eq("id", inviter_id).execute()
        supabase.table("users").update({"invite_code": None}).eq("id", inviter_id).execute()
        logger.info(f"Users paired: chat_id {chat_id} with inviter_id {inviter_id}")
        update.message.reply_text("Successfully paired!")
    except IndexError:
        logger.warning(f"No invite code provided by chat_id: {chat_id}")
        update.message.reply_text("Please provide an invite code: /join <code>")

def add_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logger.info(f"/add command received from chat_id: {chat_id}")
    try:
        category, *title = context.args
        title = " ".join(title)
        if category not in ["planned", "watched"]:
            logger.warning(f"Invalid category '{category}' provided by chat_id: {chat_id}")
            update.message.reply_text("Category must be 'planned' or 'watched'.")
            return
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        supabase.table("movies").insert({"user_id": user_id, "title": title, "category": category}).execute()
        logger.info(f"Movie '{title}' added to category '{category}' by chat_id: {chat_id}")
        update.message.reply_text(f"Added '{title}' to {category}.")
    except IndexError:
        logger.warning(f"Invalid /add command usage by chat_id: {chat_id}")
        update.message.reply_text("Usage: /add <category> <movie_title>")

def list_movies(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    try:
        category = context.args[0]
        if category not in ["planned", "watched"]:
            update.message.reply_text("Category must be 'planned' or 'watched'.")
            return
        user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
        user_ids = [user["id"]]
        if user["partner_id"]:
            user_ids.append(user["partner_id"])
        movies = supabase.table("movies").select("*").in_("user_id", user_ids).eq("category", category).execute()
        if not movies.data:
            update.message.reply_text(f"No movies in {category}.")
            return
        response = f"Movies in {category}:\n" + "\n".join([movie["title"] for movie in movies.data])
        update.message.reply_text(response)
    except IndexError:
        update.message.reply_text("Usage: /list <category>")

def random_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
    movies = supabase.table("movies").select("*").in_("user_id", user_ids).eq("category", "planned").execute()
    if not movies.data:
        update.message.reply_text("No movies in 'planned' list.")
        return
    movie = random.choice(movies.data)
    update.message.reply_text(f"Random movie: {movie['title']}")

def partner_status(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        update.message.reply_text("You are paired with someone.")
    else:
        update.message.reply_text("You are not paired.")

def unlink(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        supabase.table("users").update({"partner_id": None}).eq("id", user["partner_id"]).execute()
        supabase.table("users").update({"partner_id": None}).eq("chat_id", chat_id).execute()
        update.message.reply_text("Unlinked from partner.")
    else:
        update.message.reply_text("You are not paired.")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("invite", invite))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("add", add_movie))
    dp.add_handler(CommandHandler("list", list_movies))
    dp.add_handler(CommandHandler("random", random_movie))
    dp.add_handler(CommandHandler("partner_status", partner_status))
    dp.add_handler(CommandHandler("unlink", unlink))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()