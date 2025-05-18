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

# --- Movie-related handlers ---
def add_movie(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logging.info(f"/add command received from chat_id: {chat_id}")
    if not context.args:
        update.message.reply_text(
            "🎬 <b>Let's add a movie!</b>\n\n"
            "Please enter the movie title you want to add:",
            parse_mode='HTML'
        )
        context.user_data['awaiting_movie_title'] = True
        return
    try:
        category, *title = context.args
        title = " ".join(title)
        db_category = 'watched' if category == 'loved' else category
        if db_category not in ["planned", "watched"]:
            logging.warning(f"Invalid category '{category}' provided by chat_id: {chat_id}")
            update.message.reply_text("Category must be 'planned' or 'loved'.")
            return
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        supabase.table("movies").insert({"user_id": user_id, "title": title, "category": db_category}).execute()
        logging.info(f"Movie '{title}' added to category '{category}' by chat_id: {chat_id}")
        update.message.reply_text(f"Added '<b>{title}</b>' to <b>{category}</b>.", parse_mode='HTML')
    except IndexError:
        logging.warning(f"Invalid /add command usage by chat_id: {chat_id}")
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
        db_category = 'watched' if category == 'loved' else category
        if db_category not in ["planned", "watched"]:
            query.answer()
            query.edit_message_text("Invalid category. Please try again.")
            return
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        try:
            supabase.table("movies").insert({"user_id": user_id, "title": title, "category": db_category}).execute()
            logging.info(f"Movie '{title}' added to category '{category}' by chat_id: {chat_id} (via button)")
            query.answer()
            query.edit_message_text(
                f"✅ Added '<b>{title}</b>' to <b>{category}</b>!\n\n"
                "Use /add to add more movies or /list planned|loved to see your lists.",
                parse_mode='HTML'
            )
        except Exception as e:
            logging.error(f"Error adding movie: {e}")
            query.answer()
            query.edit_message_text("❌ Error: Could not add movie. Please use only 'planned' or 'loved' as category.")
        context.user_data.pop('pending_movie_title', None)

def list_movies(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    try:
        category = context.args[0]
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
        cat_text = 'planned and loved' if shown_category == 'all' else shown_category
        update.message.reply_text(f"No movies in <b>{cat_text}</b> list.", parse_mode='HTML')
        return
    movie = random.choice(movies.data)
    display_cat = 'loved' if movie['category'] == 'watched' else movie['category']
    update.message.reply_text(
        f"🎲 <b>Random movie from {display_cat}:</b>\n<b>{movie['title']}</b>",
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
        logging.error(f"Error editing movie: {e}")
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
        logging.error(f"Error deleting movie: {e}")
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
    text += "\n<em>Tip: Tap and hold the <code>ID</code> to copy it for use in commands below.</em>\n"
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
