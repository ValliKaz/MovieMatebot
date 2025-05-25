import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from db import supabase

def edit_list_menu(update: Update, context: CallbackContext):
    """Show the edit menu with all user's movies."""
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    user_ids = [user["id"]]
    if user["partner_id"]:
        user_ids.append(user["partner_id"])
        
    movies = supabase.table("movies").select("*").in_("user_id", user_ids).execute().data
    
    # Prepare the "no movies" message
    no_movies_text = (
        "You don't have any movies in your lists yet.\n\n"
        "Use the Add Movie button (➕) from the main menu to add a movie."
    )
    
    # Handle both callback queries and direct commands
    if not movies:
        if update.callback_query:
            update.callback_query.edit_message_text(
                no_movies_text,
                parse_mode='HTML'
            )
        else:
            update.message.reply_text(
                no_movies_text,
                parse_mode='HTML'
            )
        return
        
    text = "<b>📝 Your Movies</b>\n\n"
    for m in movies:
        cat = '❤️ Loved' if m['category'] == 'watched' else '📅 Planned'
        title = m['title']
        if m.get('release_year'):
            title += f" ({m['release_year']})"
        text += f"• <b>{title}</b> - {cat}\n"
    text += "\nSelect an action from the buttons below:"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Title", callback_data="choose_edit"),
         InlineKeyboardButton("🔄 Change Category", callback_data="choose_editcat")],
        [InlineKeyboardButton("🗑️ Delete Movie", callback_data="choose_delete")],
        [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_main")]
    ]
      # Handle both callback queries and direct commands
    if update.callback_query:
        update.callback_query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        update.callback_query.answer()
    else:
        update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def choose_edit_delete_handler(update: Update, context: CallbackContext):
    """Handle edit menu button callbacks."""
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
          # Create keyboard for movie selection
    keyboard = []
    
    if data == "choose_edit":
        for m in movies:
            keyboard.append([InlineKeyboardButton(
                f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                callback_data=f"edit_{m['id']}"
            )])
        msg = "✏️ Select a movie to edit title:"
    elif data == "choose_editcat":
        for m in movies:
            keyboard.append([InlineKeyboardButton(
                f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                callback_data=f"editcat_{m['id']}"
            )])
        msg = "🔄 Select a movie to change category:"
    elif data == "choose_delete":
        for m in movies:
            keyboard.append([InlineKeyboardButton(
                f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                callback_data=f"delete_{m['id']}"
            )])
        msg = "🗑️ Select a movie to delete:"
    
    # Add back button
    keyboard.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_edit")])
    
    query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    query.answer()

def handle_new_title(update: Update, context: CallbackContext):
    """Handle new title input for movie editing."""
    if context.user_data.get('awaiting_new_title') and context.user_data.get('edit_movie_id'):
        chat_id = str(update.effective_chat.id)
        movie_id = context.user_data['edit_movie_id']
        new_title = update.message.text.strip()
        
        try:
            # Get user and their partner's IDs
            user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
            user_ids = [user["id"]]
            if user["partner_id"]:
                user_ids.append(user["partner_id"])

            # First verify the movie belongs to user or partner
            movie = supabase.table("movies").select("*").eq("id", movie_id).in_("user_id", user_ids).execute().data
            if not movie:
                update.message.reply_text("❌ Movie not found or you don't have permission to edit it.")
                return
            
            # Update the movie title
            result = supabase.table("movies").update({"title": new_title}).eq("id", movie_id).in_("user_id", user_ids).execute()
            
            if result.data:
                update.message.reply_text(
                    f"✅ Movie updated successfully!\n"
                    f"New title: <b>{new_title}</b>",
                    parse_mode='HTML'
                )
            else:
                update.message.reply_text("❌ Error updating movie. Please try again.")
        except Exception as e:
            logging.error(f"Error updating movie title: {e}")
            update.message.reply_text("❌ An error occurred. Please try again.")
        finally:
            # Clean up context
            context.user_data.pop('edit_movie_id', None)
            context.user_data.pop('awaiting_new_title', None)

def handle_edit_request(update: Update, context: CallbackContext, data: str) -> None:
    """Handle request to edit a movie title."""
    query = update.callback_query
    movie_id = data.split("_")[1]  # Movie ID is a UUID string, no need to convert to int
    chat_id = str(query.message.chat_id)
    
    try:
        # Get user and partner IDs
        user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
        user_ids = [user["id"]]
        if user["partner_id"]:
            user_ids.append(user["partner_id"])
            
        # Get movie details
        movie = supabase.table("movies").select("*").eq("id", movie_id).in_("user_id", user_ids).execute().data
        if not movie:
            query.edit_message_text("❌ Movie not found or you don't have permission to edit it.")
            return
            
        # Store movie_id in context
        context.user_data['edit_movie_id'] = movie_id
        context.user_data['awaiting_new_title'] = True
        
        query.edit_message_text(
            f"✏️ Current title: <b>{movie[0]['title']}</b>\n\n"
            "Please send the new title for this movie:",
            parse_mode='HTML'
        )
        query.answer("Send the new title")
    except Exception as e:
        logging.error(f"Error in handle_edit_request: {e}")
        query.edit_message_text("❌ Error editing movie. Please try again.")

def handle_category_edit_request(update: Update, context: CallbackContext, data: str) -> None:
    """Handle request to edit a movie category."""
    query = update.callback_query
    movie_id = data.split("_")[1]  # Movie ID is a UUID string, no need to convert to int
    
    try:
        keyboard = [
            [
                InlineKeyboardButton("📅 Plan to Watch", callback_data=f"setcat_{movie_id}_planned"),
                InlineKeyboardButton("❤️ Watched & Loved", callback_data=f"setcat_{movie_id}_loved")
            ]
        ]
        
        query.edit_message_text(
            "🔄 Choose new category:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        query.answer()
    except Exception as e:
        logging.error(f"Error in handle_category_edit_request: {e}")
        query.edit_message_text("❌ Error changing category. Please try again.")

def handle_category_change(update: Update, context: CallbackContext, data: str) -> None:
    """Handle category change for a movie."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    _, movie_id, category = data.split("_", 2)
    db_category = 'watched' if category == 'loved' else category
    
    try:
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        result = supabase.table("movies").update({"category": db_category}).eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            query.edit_message_text(f"Category updated to: <b>{category}</b>", parse_mode='HTML')
        else:
            query.edit_message_text("Movie not found or you don't have permission to edit it.")
    except Exception as e:
        logging.error(f"Error changing movie category: {e}")
        query.edit_message_text("Error changing category. Please try again.")
    query.answer()

def handle_delete_request(update: Update, context: CallbackContext, data: str) -> None:
    """Handle request to delete a movie."""
    query = update.callback_query
    movie_id = data.split("_")[1]  # Movie ID is already a UUID string
    keyboard = [
        [InlineKeyboardButton("✅ Yes, delete", callback_data=f"confirm_delete_{movie_id}"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")]
    ]
    query.edit_message_text(
        "Are you sure you want to delete this movie?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    query.answer()

def handle_delete_confirmation(update: Update, context: CallbackContext, data: str) -> None:
    """Handle movie deletion confirmation."""
    query = update.callback_query
    chat_id = str(query.message.chat_id)
    movie_id = data.split("_")[2]
    try:
        user_id = supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]
        result = supabase.table("movies").delete().eq("id", movie_id).eq("user_id", user_id).execute()
        if result.data:
            query.edit_message_text("Movie deleted.")
        else:
            query.edit_message_text("Movie not found or you don't have permission to delete it.")
    except Exception as e:
        logging.error(f"Error deleting movie: {e}")
        query.edit_message_text("Error deleting movie. Please try again.")
    query.answer()
