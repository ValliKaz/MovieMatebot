import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import CallbackContext
from db import supabase  # Import supabase client

# Load environment variables if not already loaded
load_dotenv()

def handle_add_to_list(update: Update, context: CallbackContext, data: str):
    """Handle adding a movie to the list."""
    query = update.callback_query
    try:
        # Parse the movie index from the callback data (tmdb_add_to_list_X)
        movie_index = int(data.split("_")[-1])  # Use last part of callback data
        results = context.user_data.get('tmdb_results', [])
        
        if not results or movie_index >= len(results):
            query.answer("Movie not found.")
            return
            
        movie = results[movie_index]
        if not movie:
            query.answer("Error: Movie data not found")
            return
            
        title = movie.get("title", "Title not specified")
        context.user_data['pending_movie_title'] = title
        context.user_data['pending_movie_tmdb_data'] = movie
        
        keyboard = [
            [InlineKeyboardButton("📅 Planned", callback_data=f'tmdb_category_planned_{movie_index}')],
            [InlineKeyboardButton("❤️ Loved", callback_data=f'tmdb_category_loved_{movie_index}')]
        ]
        
        query.message.reply_text(
            f"Which category to add '<b>{title}</b>'?\n\n"
            "<b>📅 Planned</b> — movies you want to watch\n"
            "<b>❤️ Loved</b> — movies you've watched and enjoyed",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        query.answer()

    except (ValueError, IndexError) as e:
        logging.error(f"Error parsing movie index: {e}")
        query.answer("Error adding movie. Please try again.")

def tmdb_search(update: Update, context: CallbackContext) -> None:
    """Search movies through TMDB and display results with posters and description."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    query = update.message.text.strip()
    if not TMDB_API_KEY:
        update.message.reply_text("🔑 TMDB API key not found. Please add TMDB_API_KEY to .env")
        return
    
    try:
        url = "https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": query, "language": "en-US"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("🔍 No movies found.")
            return
            
        results = r.json()["results"]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show first result
        show_movie_result(update, context)
    except Exception as e:
        logging.error(f"Error searching movie through TMDB: {e}")
        update.message.reply_text("❌ Error occurred while searching for the movie. Please try again later.")

def show_movie_result(update: Update, context: CallbackContext) -> None:
    """Show a single movie result with navigation buttons."""
    results = context.user_data.get('tmdb_results', [])
    current_index = context.user_data.get('current_result_index', 0)
    next_index = current_index + 1
    
    query = update.callback_query
    
    if not results or current_index >= len(results):
        if query:
            query.edit_message_text("🔍 No results to display.")
        else:
            update.message.reply_text("🔍 No results to display.")
        return
    
    movie = results[current_index]
    title = movie.get("title", "Title not specified")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Year unknown"
    overview = movie.get("overview", "No description available")
    rating = movie.get("vote_average", 0)
    
    # Truncate overview if it's too long
    short_overview = overview[:100] + "..." if len(overview) > 100 else overview
    
    msg = (f"🎬 <b>{title}</b> ({year})\n"
           f"⭐ Rating: {rating:.1f}\n\n"
           f"📝 {short_overview}")
    
    keyboard = []
    nav_buttons = []
    
    # Add navigation buttons
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous movie", callback_data="tmdb_prev"))
    if next_index < len(results):
        nav_buttons.append(InlineKeyboardButton("➡️ Next movie", callback_data="tmdb_next"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add description control button if needed
    if len(overview) > 100:
        keyboard.append([InlineKeyboardButton("📝 Show full description", 
                                        callback_data=f"show_full_{current_index}")])
    
    # Add "Add to list" button
    keyboard.append([InlineKeyboardButton("➕ Add to my list", 
                                    callback_data=f"tmdb_add_to_list_{current_index}")])
    
    # Add "Back to List" button if we came from a list view
    if context.user_data.get('list_title'):
        keyboard.append([InlineKeyboardButton("⬅️ Back to list", callback_data="back_to_list")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or update movie info with poster
    poster = movie.get("poster_path")
    if poster:
        poster_url = f"https://image.tmdb.org/t/p/w500{poster}"
        if query:
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
    """Handle next movie button in TMDB results."""
    query = update.callback_query
    query.answer()
    
    results = context.user_data.get('tmdb_results', [])
    current_index = context.user_data.get('current_result_index', 0)
    
    if current_index + 1 < len(results):
        context.user_data['current_result_index'] = current_index + 1
        show_movie_result(update, context)

def handle_tmdb_prev(update: Update, context: CallbackContext) -> None:
    """Handle previous movie button in TMDB results."""
    query = update.callback_query
    query.answer()
    
    current_index = context.user_data.get('current_result_index', 0)
    
    if current_index > 0:
        context.user_data['current_result_index'] = current_index - 1
        show_movie_result(update, context)

def handle_show_full_description(update: Update, context: CallbackContext) -> None:
    """Show full movie description."""
    query = update.callback_query
    query.answer()
    
    results = context.user_data.get('tmdb_results', [])
    current_index = context.user_data.get('current_result_index', 0)
    
    if not results or current_index >= len(results):
        query.edit_message_text("Movie not found.")
        return
    
    movie = results[current_index]
    title = movie.get("title", "Title not specified")
    year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Year unknown"
    overview = movie.get("overview", "No description available")
    rating = movie.get("vote_average", 0)
    
    msg = (f"🎬 <b>{title}</b> ({year})\n"
           f"⭐ Rating: {rating:.1f}\n\n"
           f"📝 {overview}")
    
    keyboard = [[
        InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_movie_{current_index}"),
        InlineKeyboardButton("➕ Add to list", callback_data=f"tmdb_add_to_list_{current_index}")
    ]]
    
    if movie.get("poster_path"):
        query.edit_message_media(
            media=InputMediaPhoto(
                media=f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}",
                caption=msg,
                parse_mode='HTML'
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query.edit_message_text(
            text=msg,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def handle_back_to_movie(update: Update, context: CallbackContext) -> None:
    """Return to movie details from full description."""
    query = update.callback_query
    query.answer()
    show_movie_result(update, context)

def handle_tmdb_category_selection(update: Update, context: CallbackContext, data: str) -> None:
    """Handle category selection for TMDB movie."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    
    try:
        # Parse callback data (format: tmdb_category_TYPE_INDEX)
        _, _, category, index = data.split("_")
        movie_index = int(index)
        db_category = 'watched' if category == 'loved' else category

        # Get movie details from context - this was saved during handle_add_to_list
        movie = context.user_data.get('pending_movie_tmdb_data')
        if not movie:
            query.answer("❌ Error: Movie data not found")
            return
            
        title = movie.get("title", "Title not specified")
        release_year = movie.get("release_date", "")[:4] if movie.get("release_date") else None
        poster_path = movie.get("poster_path")
        overview = movie.get("overview")
        tmdb_id = movie.get("id")
          # Add to database with basic data (only columns that exist in the table)
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        movie_data = {
            "user_id": user_id,
            "title": title,
            "category": db_category
        }
        # Try to add TMDB ID if the column exists
        try:
            supabase.table("movies").select("tmdb_id").limit(1).execute()
            movie_data["tmdb_id"] = tmdb_id
        except:
            pass
            
        supabase.table("movies").insert(movie_data).execute()
        
        # Clear pending data
        context.user_data.pop('pending_movie_tmdb_data', None)
        context.user_data.pop('pending_movie_title', None)
        
        # Send success message with movie details
        query.answer("✅ Movie added!")
        query.edit_message_text(
            f"✅ Added '<b>{title}</b>' to your <b>{category}</b> list!\n\n"
            "Use /list or the menu to see your movies",
            parse_mode='HTML'
        )
    except (ValueError, IndexError) as e:
        logging.error(f"Error adding TMDB movie: {e}")
        query.answer("❌ Error adding movie")
        query.edit_message_text(
            "❌ Failed to add movie. Please try again.",
            parse_mode='HTML'
        )

def tmdb_popular(update: Update, context: CallbackContext) -> None:
    """Show popular movies from TMDB."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        update.message.reply_text("🔑 TMDB API key not found. Please add TMDB_API_KEY to .env")
        return
    
    try:
        url = "https://api.themoviedb.org/3/movie/popular"
        params = {"api_key": TMDB_API_KEY, "language": "en-US"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("Failed to get popular movies.")
            return
        
        results = r.json()["results"][:10]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show popular movies list
        show_movie_list(update, context, "🎬 Popular Movies")
    except Exception as e:
        logging.error(f"Error getting popular movies: {e}")
        update.message.reply_text("Error occurred while getting popular movies.")

def tmdb_top_rated(update: Update, context: CallbackContext) -> None:
    """Show top rated movies from TMDB."""
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    if not TMDB_API_KEY:
        update.message.reply_text("🔑 TMDB API key not found. Please add TMDB_API_KEY to .env")
        return
    
    try:
        url = "https://api.themoviedb.org/3/movie/top_rated"
        params = {"api_key": TMDB_API_KEY, "language": "en-US"}
        r = requests.get(url, params=params)
        
        if r.status_code != 200 or not r.json().get("results"):
            update.message.reply_text("Failed to get top rated movies.")
            return
        
        results = r.json()["results"][:10]
        context.user_data['tmdb_results'] = results
        context.user_data['current_result_index'] = 0
        
        # Show top rated movies list
        show_movie_list(update, context, "⭐ Top Rated Movies")
    except Exception as e:
        logging.error(f"Error getting top rated movies: {e}")
        update.message.reply_text("Error occurred while getting top rated movies.")

def show_movie_list(update: Update, context: CallbackContext, title: str) -> None:
    """Helper function to show a list of movies with buttons."""
    results = context.user_data.get('tmdb_results', [])
    if not results:
        if update.callback_query:
            update.callback_query.edit_message_text("No results to display.")
        else:
            update.message.reply_text("No results to display.")
        return

    context.user_data['list_title'] = title
    
    msg = f"<b>{title}:</b>\n\nClick on a movie number to see detailed information:\n\n"
    keyboard = []
    row = []
    
    for i, movie in enumerate(results, 1):
        title = movie.get("title", "Title not specified")
        year = movie.get("release_date", "")[:4] if movie.get("release_date") else "Year unknown"
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
                query.edit_message_text(msg, parse_mode='HTML', reply_markup=reply_markup)
            except Exception as e:
                logging.error(f"Error updating movie list message: {e}")
    else:
        # Initial message send
        update.message.reply_text(
            msg, 
            parse_mode='HTML',
            reply_markup=reply_markup
        )

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


