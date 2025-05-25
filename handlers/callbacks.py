import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import supabase
from handlers.tmdb import (
    show_movie_result, handle_tmdb_next, handle_tmdb_prev,
    handle_view_movie, handle_back_to_list, handle_show_full_description,
    handle_back_to_movie, handle_tmdb_category_selection, handle_add_to_list
)
from handlers.edit_menu import (
    handle_edit_request, handle_category_edit_request,
    handle_category_change, handle_delete_request, handle_delete_confirmation,
    choose_edit_delete_handler, edit_list_menu
)

def button_handler(update: Update, context: CallbackContext):
    """Handle all callback buttons."""
    query = update.callback_query
    data = query.data
    
    # TMDB handlers
    if data == "tmdb_next":
        handle_tmdb_next(update, context)
    elif data == "tmdb_prev":
        handle_tmdb_prev(update, context)
    elif data.startswith("view_movie_"):
        handle_view_movie(update, context)
    elif data.startswith("back_to_list"):
        handle_back_to_list(update, context)
    elif data.startswith("show_full_"):
        handle_show_full_description(update, context)
    elif data.startswith("back_to_movie_"):
        handle_back_to_movie(update, context)
    elif data.startswith("tmdb_add_to_list_"):
        handle_add_to_list(update, context, data)
    elif data.startswith("tmdb_category_"):
        handle_tmdb_category_selection(update, context, data)
      # Movie management handlers
    elif data.startswith("choose_"):
        choose_edit_delete_handler(update, context)
    elif data.startswith("edit_"):
        handle_edit_request(update, context, data)
    elif data.startswith("editcat_"):
        handle_category_edit_request(update, context, data)
    elif data.startswith("setcat_"):
        handle_category_change(update, context, data)
    elif data.startswith("delete_"):
        handle_delete_request(update, context, data)
    elif data.startswith("confirm_delete_"):
        handle_delete_confirmation(update, context, data)
    elif data == "back_to_edit":
        edit_list_menu(update, context)
    elif data == "cancel_delete":
        query.edit_message_text("❌ Deletion cancelled.")
        query.answer()
    elif data == "back_to_main":
        from keyboards import main_menu_keyboard
        query.edit_message_text(
            "📱 Main Menu",
            reply_markup=main_menu_keyboard()
        )
        query.answer()
    else:
        query.answer("⚠️ Unknown button")


def handle_category_selection(update: Update, context: CallbackContext, data: str):
    """Handle category selection for a movie."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    category = data.split("_")[1]
    title = context.user_data.get('pending_movie_title')
    
    if not title:
        query.answer()
        query.edit_message_text("❌ Error: movie title not found. Please try again.")
        return

    db_category = 'watched' if category == 'loved' else category
    if db_category not in ["planned", "watched"]:
        query.answer()
        query.edit_message_text("❌ Error: invalid category. Please use 'planned' or 'loved'.")
        return

    try:
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        supabase.table("movies").insert({
            "user_id": user_id,
            "title": title,
            "category": db_category
        }).execute()
        
        query.answer("✅ Movie successfully added!")
        query.edit_message_text(
            f"✅ Movie '<b>{title}</b>' has been added to <b>{category}</b>!\n\n"
            "Use /list planned or /list loved to see your lists.",
            parse_mode='HTML'
        )
        context.user_data.pop('pending_movie_title', None)
    except Exception as e:
        logging.error(f"Error adding movie: {e}")
        query.answer("❌ Error occurred while adding the movie.")
        query.edit_message_text("❌ Error: Failed to add movie. Please try again later.")
