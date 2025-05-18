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

def edit_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
    try:
        movie_id = context.args[0]
        new_title = " ".join(context.args[1:])
        if not new_title:
            update.message.reply_text("Usage: /edit <code>movie_id</code> <code>new_title</code>")
            return
        result = supabase.table("movies").update({"title": new_title}).eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            update.message.reply_text(f"Movie updated to: <b>{new_title}</b>", parse_mode='HTML')
        else:
            update.message.reply_text("Movie not found or you don't have permission to edit it.")
    except Exception as e:
        logger.error(f"Error editing movie: {e}")
        update.message.reply_text("Error editing movie. Usage: /edit <code>movie_id</code> <code>new_title</code>")

def delete_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
    try:
        movie_id = context.args[0]
        result = supabase.table("movies").delete().eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            update.message.reply_text("Movie deleted.")
        else:
            update.message.reply_text("Movie not found or you don't have permission to delete it.")
    except Exception as e:
        logger.error(f"Error deleting movie: {e}")
        update.message.reply_text("Error deleting movie. Usage: /delete <movie_id>")

def edit_list_menu(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
    movies = supabase.table("movies").select("id, title, category").in_("user_id", user_ids).execute().data
    if not movies:
        update.message.reply_text("No movies to edit or delete.")
        return
    text = "<b>Your movies:</b>\n"
    for m in movies:
        cat = 'loved' if m['category'] == 'watched' else m['category']
        text += f"ID: <code>{m['id']}</code> | {m['title']} ({cat})\n"
    text += "\n<em>Note: You can tap and copy the <code>ID</code> for use in commands below.</em>\n"
    text += "Choose an action below or use commands:\nTo edit: /edit <code>movie_id</code> <code>new_title</code>\nTo delete: /delete <code>movie_id</code>\nTo change category: /setcat <code>movie_id</code> <code>planned|loved</code>"
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Title", callback_data="choose_edit"),
         InlineKeyboardButton("🗂️ Edit Category", callback_data="choose_editcat")],
        [InlineKeyboardButton("🗑️ Delete", callback_data="choose_delete")]
    ]
    update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def edit_delete_menu(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
    movies = supabase.table("movies").select("id, title, category").in_("user_id", user_ids).execute().data
    if not movies:
        update.message.reply_text("No movies to edit or delete.")
        return
    keyboard = [
        [InlineKeyboardButton("✏️ Edit", callback_data="choose_edit"), InlineKeyboardButton("🗑️ Delete", callback_data="choose_delete")]
    ]
    update.message.reply_text(
        "What do you want to do?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def choose_edit_delete_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    data = query.data
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
    movies = supabase.table("movies").select("id, title, category").in_("user_id", user_ids).execute().data
    if not movies:
        query.answer()
        query.edit_message_text("No movies to edit or delete.")
        return
    if data == "choose_edit":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", callback_data=f"edit_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to edit title:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "choose_editcat":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", callback_data=f"editcat_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to change category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "choose_delete":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", callback_data=f"delete_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to delete:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("delete_"):
        movie_id = data.split("_")[1]
        # Ask for confirmation
        keyboard = [
            [InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_delete_{movie_id}"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
        ]
        query.edit_message_text(
            f"Are you sure you want to delete this movie?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("confirm_delete_"):
        movie_id = data.split("_")[2]
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        result = supabase.table("movies").delete().eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            query.edit_message_text("Movie deleted.")
        else:
            query.edit_message_text("Movie not found or you don't have permission to delete it.")
    elif data == "cancel_delete":
        query.edit_message_text("Deletion cancelled.")
    elif data.startswith("edit_"):
        movie_id = data.split("_")[1]
        context.user_data['edit_movie_id'] = movie_id
        query.edit_message_text("Send the new title for this movie:")
        context.user_data['awaiting_new_title'] = True
    elif data.startswith("editcat_"):
        movie_id = data.split("_")[1]
        # Показываем выбор категории
        keyboard = [
            [InlineKeyboardButton("Planned 📅", callback_data=f"setcat_{movie_id}_planned"),
             InlineKeyboardButton("Loved ❤️", callback_data=f"setcat_{movie_id}_loved")]
        ]
        query.edit_message_text(
            "Choose new category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("setcat_"):
        _, movie_id, cat = data.split("_", 2)
        db_category = 'watched' if cat == 'loved' else cat
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        result = supabase.table("movies").update({"category": db_category}).eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            query.edit_message_text(f"Category updated to: <b>{cat}</b>", parse_mode='HTML')
        else:
            query.edit_message_text("Movie not found or you don't have permission to edit it.")

def handle_new_title(update: Update, context: CallbackContext):
    if context.user_data.get('awaiting_new_title') and context.user_data.get('edit_movie_id'):
        chat_id = str(update.effective_chat.id)
        movie_id = context.user_data['edit_movie_id']
        new_title = update.message.text.strip()
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        result = supabase.table("movies").update({"title": new_title}).eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            update.message.reply_text(f"Movie updated to: <b>{new_title}</b>", parse_mode='HTML')
        else:
            update.message.reply_text("Movie not found or you don't have permission to edit it.")
        context.user_data.pop('edit_movie_id', None)
        context.user_data.pop('awaiting_new_title', None)

def menu_handler(update: Update, context: CallbackContext):
    text = update.message.text
    if context.user_data.get('awaiting_new_title') and context.user_data.get('edit_movie_id'):
        return handle_new_title(update, context)
    if context.user_data.get('awaiting_movie_title'):
        return handle_movie_title(update, context)
    # Normalize text for edit movies button (strip spaces, ignore emoji)
    normalized = text.strip().replace('✏️', '').replace('📝', '').replace(' ', '').lower()
    if text == "➕ Add Movie":
        return add_movie(update, context)
    elif text == "📋 List Movies":
        update.message.reply_text(
            "Which list do you want to see?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("Planned"), KeyboardButton("Loved")],
                [KeyboardButton("✏️ Edit Movies")],
                [KeyboardButton("⬅️ Back to Menu")]
            ], resize_keyboard=True)
        )
    elif "editmovies" in normalized:
        return edit_list_menu(update, context)
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
    dp.add_handler(CommandHandler("edit", edit_movie))
    dp.add_handler(CommandHandler("delete", delete_movie))
    dp.add_handler(CommandHandler("editdeletemenu", edit_delete_menu))
    dp.add_handler(CallbackQueryHandler(choose_edit_delete_handler, pattern=r'^(choose_edit|choose_delete|edit_.*|delete_.*|confirm_delete_.*|cancel_delete|choose_editcat|editcat_.*|setcat_.*)$'))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, menu_handler))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()