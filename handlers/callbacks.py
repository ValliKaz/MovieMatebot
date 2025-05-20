import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import supabase
from handlers.tmdb import (
    show_movie_result, handle_tmdb_next, handle_tmdb_prev,
    handle_view_movie, handle_back_to_list
)

def button_handler(update: Update, context: CallbackContext):
    """Handle all callback buttons."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    data = query.data
    
    # TMDB navigation handlers
    if data == "tmdb_next":
        return handle_tmdb_next(update, context)
    elif data == "tmdb_prev":
        return handle_tmdb_prev(update, context)
    elif data.startswith("view_movie_"):
        from handlers.tmdb import handle_view_movie
        return handle_view_movie(update, context)
    elif data.startswith("back_to_list"):
        from handlers.tmdb import handle_back_to_list
        return handle_back_to_list(update, context)
    
    # Movie management handlers
    elif data.startswith("add_to_list_"):
        handle_add_to_list(update, context, data)
    elif data.startswith('category_'):
        handle_category_selection(update, context, data)
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
    elif data == "cancel_delete":
        query.edit_message_text("Deletion cancelled.")

def handle_add_to_list(update: Update, context: CallbackContext, data: str):
    """Handle adding a movie to the list."""
    query = update.callback_query
    movie_index = int(data.split("_")[3])
    results = context.user_data.get('tmdb_results', [])
    
    if not results or movie_index >= len(results):
        query.answer("Фильм не найден.")
        return
        
    movie = results[movie_index]
    title = movie.get("title", "Название не указано")
    context.user_data['pending_movie_title'] = title
    
    keyboard = [
        [InlineKeyboardButton("Planned 📅", callback_data=f'category_planned')],
        [InlineKeyboardButton("Loved ❤️", callback_data=f'category_loved')]
    ]
    
    query.message.reply_text(
        f"В какую категорию добавить фильм '<b>{title}</b>'?\n\n"
        "<b>Planned</b> — фильмы, которые хотите посмотреть\n"
        "<b>Loved</b> — фильмы, которые уже посмотрели и они понравились",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    query.answer()

def handle_category_selection(update: Update, context: CallbackContext, data: str):
    """Handle category selection for a movie."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    category = data.split("_")[1]
    title = context.user_data.get('pending_movie_title')
    
    if not title:
        query.answer()
        query.edit_message_text("Ошибка: название фильма не найдено. Попробуйте снова.")
        return

    db_category = 'watched' if category == 'loved' else category
    if db_category not in ["planned", "watched"]:
        query.answer()
        query.edit_message_text("Ошибка: неверная категория. Используйте 'planned' или 'loved'.")
        return

    try:
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        supabase.table("movies").insert({
            "user_id": user_id,
            "title": title,
            "category": db_category
        }).execute()
        
        query.answer("Фильм успешно добавлен!")
        query.edit_message_text(
            f"✅ Фильм '<b>{title}</b>' добавлен в категорию <b>{category}</b>!\n\n"
            "Используйте /list planned или /list loved чтобы посмотреть ваши списки.",
            parse_mode='HTML'
        )
        context.user_data.pop('pending_movie_title', None)
    except Exception as e:
        logging.error(f"Error adding movie: {e}")
        query.answer("Произошла ошибка при добавлении фильма.")
        query.edit_message_text("❌ Ошибка: Не удалось добавить фильм. Попробуйте позже.")
