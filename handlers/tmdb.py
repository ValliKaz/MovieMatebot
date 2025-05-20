import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CallbackContext
from db import supabase  # Import supabase client

# Load environment variables if not already loaded
load_dotenv()

def tmdb_search(update: Update, context: CallbackContext) -> None:
    """Search movies through TMDB and display results with posters and description."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    query = update.message.text.strip()
    if not TMDB_API_KEY:
        update.message.reply_text("TMDB API ключ не найден. Добавьте TMDB_API_KEY в .env.")
        return
    
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("Фильмы не найдены.")
            return
            
        results = r.json()["results"]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show first result
        show_movie_result(update, context)
    except Exception as e:
        logging.error(f"Ошибка при поиске фильма через TMDB: {e}")
        update.message.reply_text("Произошла ошибка при поиске фильма. Попробуйте позже.")

def show_movie_result(update: Update, context: CallbackContext) -> None:
    """Show a single movie result with navigation buttons."""
    results = context.user_data.get('tmdb_results', [])
    current_index = context.user_data.get('current_result_index', 0)
    next_index = current_index + 1
    
    # Get the callback query if this was called from a callback handler
    query = update.callback_query
    
    if not results or current_index >= len(results):
        if query:
            query.edit_message_text("Нет результатов для отображения.")
        else:
            update.message.reply_text("Нет результатов для отображения.")
        return
    
    movie = results[current_index]
    title = movie.get("title", "Название не указано")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Год не указан"
    overview = movie.get("overview", "Описание отсутствует")
    rating = movie.get("vote_average", 0)
    
    # Truncate overview if it's too long
    short_overview = overview[:100] + "..." if len(overview) > 100 else overview
    
    msg = (f"<b>{title}</b> ({year})\n"
           f"⭐ Рейтинг: {rating:.1f}\n\n"
           f"{short_overview}")
    
    keyboard = []
    nav_buttons = []
    
    # Add navigation buttons
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущий фильм", callback_data="tmdb_prev"))
    if next_index < len(results):
        nav_buttons.append(InlineKeyboardButton("➡️ Следующий фильм", callback_data="tmdb_next"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add description control button if needed
    if len(overview) > 100:
        keyboard.append([InlineKeyboardButton("📝 Показать полное описание", 
                                        callback_data=f"show_full_{current_index}")])
    
    # Add "Add to list" button
    keyboard.append([InlineKeyboardButton("➕ Добавить в свой список", 
                                    callback_data=f"tmdb_add_to_list_{current_index}")])
    
    # Add "Back to List" button if we came from a list view
    if context.user_data.get('list_title'):
        keyboard.append([InlineKeyboardButton("⬅️ К списку", callback_data="back_to_list")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or update movie info with poster
    poster = movie.get("poster_path")
    if poster:
        poster_url = f"https://image.tmdb.org/t/p/w500{poster}"
        if query:
            # If this is a callback update, we need to use edit_message_media
            try:
                query.edit_message_media(
                    media=InputMediaPhoto(
                        media=poster_url,
                        caption=msg,
                        parse_mode='HTML'
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"Error updating message with photo: {e}")
                # Fallback to text-only update if media edit fails
                query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
        else:
            update.message.reply_photo(
                photo=poster_url,
                caption=msg,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    else:
        if query:
            query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
        else:
            update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

def handle_tmdb_next(update: Update, context: CallbackContext) -> None:
    """Handle the 'Next' button in TMDB search results."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    # Update the current index and show the next result
    current_index = context.user_data.get('current_result_index', 0)
    results = context.user_data.get('tmdb_results', [])
    
    if not results:
        query.edit_message_text("No movie results available.")
        return
        
    next_index = current_index + 1
    if next_index >= len(results):
        return  # Do nothing if we're already at the end
        
    context.user_data['current_result_index'] = next_index
    show_movie_result(update, context)

def handle_tmdb_prev(update: Update, context: CallbackContext) -> None:
    """Handle the 'Previous' button in TMDB search results."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    # Update the current index and show the previous result
    current_index = context.user_data.get('current_result_index', 0)
    results = context.user_data.get('tmdb_results', [])
    
    if not results:
        query.edit_message_text("No movie results available.")
        return
        
    prev_index = current_index - 1
    if prev_index < 0:
        return  # Do nothing if we're already at the beginning
        
    context.user_data['current_result_index'] = prev_index
    show_movie_result(update, context)

def handle_show_full_description(update: Update, context: CallbackContext) -> None:
    """Handle the 'Show full description' button in TMDB search results."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    results = context.user_data.get('tmdb_results', [])
    if not results:
        query.edit_message_text("No movie results available.")
        return
        
    # Get the index from the callback data
    try:
        index = int(query.data.split('_')[2])
        movie = results[index]
    except (IndexError, ValueError):
        query.edit_message_text("Invalid movie selection.")
        return
    
    title = movie.get("title", "Название не указано")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Год не указан"
    overview = movie.get("overview", "Описание отсутствует")
    rating = movie.get("vote_average", 0)
    
    msg = (f"<b>{title}</b> ({year})\n"
           f"⭐ Рейтинг: {rating:.1f}\n\n"
           f"{overview}")
    
    keyboard = []
    # Add "Back" button
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_movie_{index}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If the message has a photo, update both photo and caption
    if movie.get("poster_path"):
        poster_url = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}"
        try:
            query.edit_message_media(
                media=InputMediaPhoto(
                    media=poster_url,
                    caption=msg,
                    parse_mode='HTML'
                ),
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error updating message with photo: {e}")
            # Fallback to text-only update if media edit fails
            query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
    else:
        query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)

def handle_add_to_list(update: Update, context: CallbackContext) -> None:
    """Handle adding a TMDB movie to the user's list."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    results = context.user_data.get('tmdb_results', [])
    if not results:
        query.edit_message_text("Нет данных о фильме. Пожалуйста, попробуйте выполнить поиск заново.")
        return
    
    # Get the movie index from the callback data
    try:
        index = int(query.data.split('_')[3])
        movie = results[index]
    except (IndexError, ValueError):
        query.edit_message_text("Ошибка выбора фильма. Пожалуйста, попробуйте снова.")
        return
    
    # Ask user to choose category
    title = movie.get("title", "Название не указано")
    keyboard = []
    
    # Add category buttons
    keyboard.append([
        InlineKeyboardButton("📅 В планах", callback_data=f"tmdb_category_planned_{index}"),
        InlineKeyboardButton("❤️ Любимые", callback_data=f"tmdb_category_loved_{index}")
    ])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_movie_{index}")])
    
    msg = (f"В какую категорию добавить фильм '<b>{title}</b>'?\n\n"
           "📅 <b>В планах</b> — фильмы, которые хотите посмотреть\n"
           "❤️ <b>Любимые</b> — фильмы, которые уже посмотрели и понравились")
    
    try:
        if movie.get("poster_path"):
            poster_url = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}"
            query.edit_message_media(
                media=InputMediaPhoto(
                    media=poster_url,
                    caption=msg,
                    parse_mode='HTML'
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Error updating add to list message: {e}")
        query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

def handle_tmdb_category_selection(update: Update, context: CallbackContext) -> None:
    """Handle category selection for a TMDB movie."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    try:
        chat_id = str(query.message.chat_id)
        data_parts = query.data.split('_')
        category = data_parts[2]
        index = int(data_parts[3])
        
        results = context.user_data.get('tmdb_results', [])
        if not results:
            query.edit_message_text("No movie results available.")
            return
            
        movie = results[index]
        db_category = 'watched' if category == 'loved' else category
        
        # Get user ID from Supabase
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        
        # Insert movie with TMDB data
        movie_data = {
            "user_id": user_id,
            "title": movie.get("title"),
            "category": db_category,
            "tmdb_id": movie.get("id"),
            "release_year": movie.get("release_date", "")[:4] if movie.get("release_date") else None,
            "overview": movie.get("overview"),
            "poster_path": movie.get("poster_path")
        }
        
        # Add to database
        supabase.table("movies").insert(movie_data).execute()
        
        # Update message to confirm
        query.edit_message_text(
            f"✅ Added '<b>{movie.get('title')}</b>' to <b>{category}</b>!\n\n"
            "Use /add to add more movies or /list planned|loved to see your lists.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Error adding TMDB movie: {e}")
        query.edit_message_text("Error adding movie. Please try again.")

def tmdb_popular(update: Update, context: CallbackContext) -> None:
    """Show popular movies from TMDB."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        update.message.reply_text("TMDB API ключ не найден. Добавьте TMDB_API_KEY в .env.")
        return
    
    try:
        url = "https://api.themoviedb.org/3/movie/popular"
        params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("Не удалось получить популярные фильмы.")
            return
        
        results = r.json()["results"][:10]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show popular movies list
        show_movie_list(update, context, "🎬 Популярные фильмы")
    except Exception as e:
        logging.error(f"Error getting popular movies: {e}")
        update.message.reply_text("Произошла ошибка при получении популярных фильмов.")

def tmdb_top_rated(update: Update, context: CallbackContext) -> None:
    """Show top rated movies from TMDB."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        update.message.reply_text("TMDB API ключ не найден. Добавьте TMDB_API_KEY в .env.")
        return
    
    try:
        url = "https://api.themoviedb.org/3/movie/top_rated"
        params = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("Не удалось получить топ рейтинга.")
            return
        
        results = r.json()["results"][:10]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show top rated movies list
        show_movie_list(update, context, "⭐ Топ рейтинга фильмов")
    except Exception as e:
        logging.error(f"Error getting top rated movies: {e}")
        update.message.reply_text("Произошла ошибка при получении топ рейтинга.")

def show_movie_list(update: Update, context: CallbackContext, title: str) -> None:
    """Helper function to show a list of movies with buttons."""
    results = context.user_data.get('tmdb_results', [])
    if not results:
        if update.callback_query:
            update.callback_query.edit_message_text("Нет результатов для отображения.")
        else:
            update.message.reply_text("Нет результатов для отображения.")
        return

    context.user_data['list_title'] = title
    
    msg = f"<b>{title}:</b>\n\nНажмите на номер фильма, чтобы увидеть подробную информацию:\n\n"
    keyboard = []
    row = []
    
    for i, movie in enumerate(results, 1):
        title = movie.get("title", "Название не указано")
        year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Год не указан"
        rating = movie.get("vote_average", 0)
        
        msg += f"<b>{i}</b>. {title} ({year}) - ⭐ {rating:.1f}\n"
        
        row.append(InlineKeyboardButton(str(i), callback_data=f"view_movie_{i-1}"))
        
        if len(row) == 5 or i == len(results):
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get callback query if this was called from a callback
    query = update.callback_query
    if query:
        try:
            # Delete the current message and send a new one
            query.message.delete()
            query.message.reply_text(
                msg,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error deleting message, falling back to edit: {e}")
            # If deletion fails, fall back to editing the message
            try:
                query.edit_message_text(
                    msg,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"Error updating movie list message: {e}")
    else:
        # Initial message send
        update.message.reply_text(
            msg, 
            parse_mode='HTML',
            reply_markup=reply_markup
        )

def handle_back_to_movie(update: Update, context: CallbackContext) -> None:
    """Handle the 'Back' button when viewing full description."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    try:
        # Get the index from the callback data
        index = int(query.data.split('_')[3])
        # Set the current index to show the correct movie
        context.user_data['current_result_index'] = index
        # Show the movie result again
        show_movie_result(update, context)
    except (IndexError, ValueError) as e:
        logging.error(f"Error handling back button: {e}")
        query.edit_message_text("Error returning to movie. Please try your search again.")

def handle_back_to_list(update: Update, context: CallbackContext) -> None:
    """Handle the 'Back to list' button press."""
    query = update.callback_query
    query.answer()  # Answer first to acknowledge the button press
    list_title = context.user_data.get('list_title', '')
    if not list_title:
        query.edit_message_text("Unable to return to list. Please try your search again.")
        return
    show_movie_list(update, context, list_title)

def handle_view_movie(update: Update, context: CallbackContext) -> None:
    """Handle viewing a specific movie from the list."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press
    
    try:
        # Get movie index from callback data
        movie_index = int(query.data.split('_')[2])
        # Keep the list_title in context when viewing individual movies
        context.user_data['current_result_index'] = movie_index
        
        # Show the selected movie
        show_movie_result(update, context)
    except (IndexError, ValueError) as e:
        logging.error(f"Error handling view_movie callback: {e}")
        query.edit_message_text("Error displaying movie details. Please try again.")


