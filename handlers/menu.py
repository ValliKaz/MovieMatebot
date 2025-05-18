import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from supabase import create_client, Client
from db import supabase
from keyboards import main_menu_keyboard

# --- Menu and navigation handlers ---
def start(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logging.info(f"/start command received from chat_id: {chat_id}")
    try:
        user = supabase.table("users").select("*").eq("chat_id", chat_id).execute()
        if not user.data:
            supabase.table("users").insert({"chat_id": chat_id}).execute()
            logging.info(f"New user added with chat_id: {chat_id}")
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
        logging.error(f"Error in /start: {e}")
        update.message.reply_text("An error occurred while processing your request. Please try again later.", reply_markup=main_menu_keyboard())

def menu_handler(update: Update, context: CallbackContext):
    text = update.message.text
    if context.user_data.get('awaiting_new_title') and context.user_data.get('edit_movie_id'):
        from handlers.movies import handle_new_title
        return handle_new_title(update, context)
    if context.user_data.get('awaiting_movie_title'):
        from handlers.movies import handle_movie_title
        return handle_movie_title(update, context)
    normalized = text.strip().replace('✏️', '').replace('📝', '').replace(' ', '').lower()
    if text == "➕ Add Movie":
        from handlers.movies import add_movie
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
        from handlers.movies import edit_list_menu
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
        from handlers.movies import random_movie
        return random_movie(update, context)
    elif text == "Random from Loved":
        context.args = ["loved"]
        from handlers.movies import random_movie
        return random_movie(update, context)
    elif text == "Random from All":
        context.args = ["all"]
        from handlers.movies import random_movie
        return random_movie(update, context)
    elif text == "🤝 Partner Status":
        from handlers.partner import partner_status
        return partner_status(update, context)
    elif text == "🔗 Invite":
        from handlers.partner import invite
        return invite(update, context)
    elif text == "🔓 Unlink":
        from handlers.partner import unlink
        return unlink(update, context)
    elif text == "Planned":
        context.args = ["planned"]
        from handlers.movies import list_movies
        return list_movies(update, context)
    elif text == "Loved":
        context.args = ["loved"]
        from handlers.movies import list_movies
        return list_movies(update, context)
    elif text == "⬅️ Back to Menu":
        update.message.reply_text("Back to main menu.", reply_markup=main_menu_keyboard())
    else:
        update.message.reply_text("Please use the menu buttons below.", reply_markup=main_menu_keyboard())
