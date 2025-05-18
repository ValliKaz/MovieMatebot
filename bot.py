import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
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

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Add Movie"), KeyboardButton("📋 List Movies")],
        [KeyboardButton("🎲 Random Movie"), KeyboardButton("🤝 Partner Status")],
        [KeyboardButton("🔗 Invite"), KeyboardButton("🔓 Unlink")]
    ], resize_keyboard=True)

def start(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logger.info(f"/start command received from chat_id: {chat_id}")
    try:
        # Check if user exists
        user = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
        if not user.data:
            supabase.table("users").insert({"chat_id": chat_id}).execute()
            logger.info(f"New user added with chat_id: {chat_id}")
        welcome_text = (
            "👋 <b>Welcome to MovieMateBot!</b>\n\n"
            "This bot helps you and your partner keep a shared list of movies.\n\n"
            "<b>How to get started:</b>\n"
            "1️⃣ Use <b>/invite</b> to generate an invite code and send it to your friend.\n"
            "2️⃣ Your friend should use <b>/join &lt;code&gt;</b> to connect with you.\n\n"
            "<b>What you can do:</b>\n"
            "- Add movies to your shared list with <b>/add</b>\n"
            "- Classify movies as <b>planned</b> or <b>loved</b>\n"
            "- See your lists with <b>/list planned</b> or <b>/list loved</b>\n"
            "- Get a random movie suggestion with <b>/random</b>\n"
            "- Check your partner status with <b>/partner_status</b>\n"
            "- Unlink from your partner with <b>/unlink</b>\n\n"
            "<i>All commands work for both you and your partner. Enjoy watching together! 🎬</i>"
        )
        update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=main_menu_keyboard())
    except Exception as e:
        logger.error(f"Error in /start: {e}")
        update.message.reply_text("An error occurred while processing your request. Please try again later.", reply_markup=main_menu_keyboard())

def invite(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    invite_code = f"INV-{uuid.uuid4().hex[:6]}"
    logger.info(f"Generated invite code {invite_code} for chat_id: {chat_id}")
    supabase.table("users").update({"invite_code": invite_code}).eq("chat_id", chat_id).execute()
    text = (
        f"🔗 <b>Your invite code:</b> <code>{invite_code}</code>\n\n"
        "Send this code to your friend.\n"
        "They should use <b>/join &lt;code&gt;</b> to connect with you.\n\n"
        "<i>Note: The code can only be used once.</i>"
    )
    update.message.reply_text(text, parse_mode='HTML')

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
            update.message.reply_text("❌ Invalid invite code! Please check the code and try again.")
            return
        inviter_id = inviter.data[0]["id"]
        # Update partner_id for both users
        supabase.table("users").update({"partner_id": inviter_id}).eq("chat_id", chat_id).execute()
        supabase.table("users").update({"partner_id": supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]}).eq("id", inviter_id).execute()
        supabase.table("users").update({"invite_code": None}).eq("id", inviter_id).execute()
        logger.info(f"Users paired: chat_id {chat_id} with inviter_id {inviter_id}")
        update.message.reply_text(
            "✅ <b>Successfully paired!</b>\n\n"
            "You can now add movies together and share your lists.\n"
            "Try <b>/add</b> to add your first movie!",
            parse_mode='HTML'
        )
    except IndexError:
        logger.warning(f"No invite code provided by chat_id: {chat_id}")
        update.message.reply_text("Please provide an invite code: /join <code>")

def add_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logger.info(f"/add command received from chat_id: {chat_id}")
    if not context.args:
        update.message.reply_text(
            "🎬 <b>Let's add a movie!</b>\n\n"
            "Please enter the movie title you want to add:",
            parse_mode='HTML'
        )
        context.user_data['awaiting_movie_title'] = True
        return
    # If both category and title are provided in command
    try:
        category, *title = context.args
        title = " ".join(title)
        # Map 'loved' to 'watched' for DB
        db_category = 'watched' if category == 'loved' else category
        if db_category not in ["planned", "watched"]:
            logger.warning(f"Invalid category '{category}' provided by chat_id: {chat_id}")
            update.message.reply_text("Category must be 'planned' or 'loved'.")
            return
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        supabase.table("movies").insert({"user_id": user_id, "title": title, "category": db_category}).execute()
        logger.info(f"Movie '{title}' added to category '{category}' by chat_id: {chat_id}")
        update.message.reply_text(f"Added '<b>{title}</b>' to <b>{category}</b>.", parse_mode='HTML')
    except IndexError:
        logger.warning(f"Invalid /add command usage by chat_id: {chat_id}")
        update.message.reply_text("Usage: /add <category> <movie_title>")

def handle_movie_title(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    if context.user_data.get('awaiting_movie_title'):
        title = update.message.text.strip()
        context.user_data['pending_movie_title'] = title
        context.user_data['awaiting_movie_title'] = False
        keyboard = [
            [InlineKeyboardButton("Planned 📅", callback_data='category_planned')],
            [InlineKeyboardButton("Loved ❤️", callback_data='category_loved')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"Which category for '<b>{title}</b>'?\n\n"
            "<b>Planned</b> — movies you want to watch.\n"
            "<b>Loved</b> — movies you already watched and liked.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    data = query.data
    if data.startswith('category_'):
        category = data.split('_')[1]
        title = context.user_data.get('pending_movie_title')
        if not title:
            query.answer()
            query.edit_message_text("No movie title found. Please try again with /add.")
            return
        # Map 'loved' to 'watched' for DB
        db_category = 'watched' if category == 'loved' else category
        if db_category not in ["planned", "watched"]:
            query.answer()
            query.edit_message_text("Invalid category. Please try again.")
            return
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        try:
            supabase.table("movies").insert({"user_id": user_id, "title": title, "category": db_category}).execute()
            logger.info(f"Movie '{title}' added to category '{category}' by chat_id: {chat_id} (via button)")
            query.answer()
            query.edit_message_text(
                f"✅ Added '<b>{title}</b>' to <b>{category}</b>!\n\n"
                "Use /add to add more movies or /list planned|loved to see your lists.",
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error adding movie: {e}")
            query.answer()
            query.edit_message_text("❌ Error: Could not add movie. Please use only 'planned' or 'loved' as category.")
        context.user_data.pop('pending_movie_title', None)

def list_movies(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    try:
        category = context.args[0]
        # Map 'loved' to 'watched' for DB
        db_category = 'watched' if category == 'loved' else category
        if db_category not in ["planned", "watched"]:
            update.message.reply_text("Category must be 'planned' or 'loved'.")
            return
        user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
        user_ids = [user["id"]]
        if user["partner_id"]:
            user_ids.append(user["partner_id"])
        movies = supabase.table("movies").select("*").in_("user_id", user_ids).eq("category", db_category).execute()
        if not movies.data:
            update.message.reply_text(f"No movies in <b>{category}</b> list yet. Use /add to add some!", parse_mode='HTML')
            return
        response = f"<b>Movies in {category.title()}:</b>\n" + "\n".join([f"• {movie['title']}" for movie in movies.data])
        update.message.reply_text(response, parse_mode='HTML')
    except IndexError:
        update.message.reply_text(
            "Usage: <code>/list planned</code> or <code>/list loved</code>",
            parse_mode='HTML'
        )

def random_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
    # Default: planned, or user can specify 'loved' or 'all'
    categories = ["planned"]
    shown_category = 'planned'
    if context.args:
        arg = context.args[0].lower()
        if arg == "loved":
            categories = ["watched"]
            shown_category = 'loved'
        elif arg == "all":
            categories = ["planned", "watched"]
            shown_category = 'all'
    movies = supabase.table("movies").select("*").in_("user_id", user_ids).in_("category", categories).execute()
    if not movies.data:
        if shown_category == 'all':
            cat_text = 'planned and loved'
        else:
            cat_text = shown_category
        update.message.reply_text(f"No movies in <b>{cat_text}</b> list.", parse_mode='HTML')
        return
    movie = random.choice(movies.data)
    # Show 'loved' for watched in UI
    display_cat = 'loved' if movie['category'] == 'watched' else movie['category']
    update.message.reply_text(
        f"🎲 <b>Random movie from {display_cat}:</b>\n<b>{movie['title']}</b>",
        parse_mode='HTML'
    )

def partner_status(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        update.message.reply_text(
            "🤝 <b>You are paired with someone!</b>\n\n"
            "You can add and share movies together.",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "🙅 <b>You are not paired yet.</b>\n\n"
            "Use /invite to generate a code or ask your friend for one.",
            parse_mode='HTML'
        )

def unlink(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        supabase.table("users").update({"partner_id": None}).eq("id", user["partner_id"]).execute()
        supabase.table("users").update({"partner_id": None}).eq("chat_id", chat_id).execute()
        update.message.reply_text(
            "🔓 <b>You have been unlinked from your partner.</b>\n\n"
            "You can now use /invite or /join to pair with someone else.",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "You are not paired.",
            parse_mode='HTML'
        )

def menu_handler(update: Update, context: CallbackContext):
    text = update.message.text
    if context.user_data.get('awaiting_movie_title'):
        # If waiting for a movie title, handle it here
        return handle_movie_title(update, context)
    if text == "➕ Add Movie":
        return add_movie(update, context)
    elif text == "📋 List Movies":
        update.message.reply_text(
            "Which list do you want to see?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Planned"), KeyboardButton("Loved")],
                [KeyboardButton("⬅️ Back to Menu")]
            ], resize_keyboard=True)
        )
    elif text == "🎲 Random Movie":
        update.message.reply_text(
            "Choose a list for random movie:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Random from Planned"), KeyboardButton("Random from Loved")],
                [KeyboardButton("Random from All")],
                [KeyboardButton("⬅️ Back to Menu")]
            ], resize_keyboard=True)
        )
    elif text == "Random from Planned":
        context.args = ["planned"]
        return random_movie(update, context)
    elif text == "Random from Loved":
        context.args = ["loved"]
        return random_movie(update, context)
    elif text == "Random from All":
        context.args = ["all"]
        return random_movie(update, context)
    elif text == "🤝 Partner Status":
        return partner_status(update, context)
    elif text == "🔗 Invite":
        return invite(update, context)
    elif text == "🔓 Unlink":
        return unlink(update, context)
    elif text == "Planned":
        context.args = ["planned"]
        return list_movies(update, context)
    elif text == "Loved":
        context.args = ["loved"]
        return list_movies(update, context)
    elif text == "⬅️ Back to Menu":
        update.message.reply_text("Back to main menu.", reply_markup=main_menu_keyboard())
    else:
        update.message.reply_text("Please use the menu buttons below.", reply_markup=main_menu_keyboard())

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
    dp.add_handler(CallbackQueryHandler(button_handler))
    # Only one MessageHandler for text, menu_handler will route to handle_movie_title if needed
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, menu_handler))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()