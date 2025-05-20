import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import supabase
from keyboards import main_menu_keyboard

def add_movie(update: Update, context: CallbackContext):
    """Add a movie to user's list."""
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

def list_movies(update: Update, context: CallbackContext):
    """List movies in a specific category."""
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
    """Get a random movie from a category."""
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
    """Edit a movie's title."""
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
    """Delete a movie."""
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
