import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from supabase import create_client, Client
from db import supabase
from keyboards import main_menu_keyboard
from .callbacks import handle_add_to_list, handle_category_selection
from .tmdb import tmdb_search, tmdb_popular, tmdb_top_rated
from .movies import handle_movie_title, add_movie, list_movies, random_movie
from .edit_menu import handle_new_title, edit_list_menu
from .partner import partner_status, invite, unlink

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
    """Handle all menu interactions."""
    text = update.message.text

    # Handle special states first
    if context.user_data.get('awaiting_new_title') and context.user_data.get('edit_movie_id'):
        return handle_new_title(update, context)
    
    if context.user_data.get('awaiting_movie_title'):
        return handle_movie_title(update, context)

    # Handle TMDB search state
    if context.user_data.get('awaiting_tmdb_search'):
        context.user_data.pop('awaiting_tmdb_search', None)
        return tmdb_search(update, context)

    # Clean text for menu comparison
    normalized = text.strip().replace('✏️', '').replace('📝', '').replace(' ', '').lower()

    # Main menu options
    if text == "🎬 Add Movie":
        return add_movie(update, context)
    
    elif text == "📋 My Lists":
        update.message.reply_text(
            "📋 Which list do you want to see?",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("📅 Planned"), KeyboardButton("❤️ Loved")],
                [KeyboardButton("✏️ Edit Movies")],
                [KeyboardButton("⬅️ Back to Menu")]
            ], resize_keyboard=True)
        )
    
    elif text == "🌟 Browse TMDB":
        tmdb_menu = ReplyKeyboardMarkup([
            [KeyboardButton("🔍 Search Movie")],
            [KeyboardButton("🎬 Popular Movies")],
            [KeyboardButton("⭐ Top Rated")],
            [KeyboardButton("⬅️ Back to Menu")]
        ], resize_keyboard=True)
        update.message.reply_text("🎬 TMDB Menu: Choose an action", reply_markup=tmdb_menu)
    
    elif text == "🔍 Search Movie":
        update.message.reply_text("🔍 Enter a movie title to search in TMDB:")
        context.user_data['awaiting_tmdb_search'] = True
    
    elif text == "🎬 Popular Movies":
        return tmdb_popular(update, context)
    
    elif text == "⭐ Top Rated":
        return tmdb_top_rated(update, context)
    
    elif text == "✏️ Edit Movies":
        return edit_list_menu(update, context)
    
    elif text == "🎲 Random Pick":
        update.message.reply_text(
            "🎲 Choose a list for random movie:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🎲 From Planned"), KeyboardButton("🎲 From Loved")],
                [KeyboardButton("🎲 From All Lists")],
                [KeyboardButton("⬅️ Back to Menu")]
            ], resize_keyboard=True)
        )
    
    elif text == "🎲 From Planned":
        context.args = ["planned"]
        return random_movie(update, context)
    
    elif text == "🎲 From Loved":
        context.args = ["loved"]
        return random_movie(update, context)
    
    elif text == "🎲 From All Lists":
        context.args = ["all"]
        return random_movie(update, context)
    
    elif text == "👥 Partner Status":
        return partner_status(update, context)
    
    elif text == "🔗 Invite Friend":
        return invite(update, context)
    
    elif text == "🔓 Unlink Partner":
        return unlink(update, context)
    
    elif text == "📅 Planned":
        context.args = ["planned"]
        return list_movies(update, context)
    
    elif text == "❤️ Loved":
        context.args = ["loved"]
        return list_movies(update, context)
    
    elif text == "⬅️ Back to Menu":
        update.message.reply_text("📱 Back to main menu", reply_markup=main_menu_keyboard())
    
    else:
        update.message.reply_text(
            "Please use the menu buttons below 👇",
            reply_markup=main_menu_keyboard()
        )
