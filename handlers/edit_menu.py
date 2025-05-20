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
        
    if data == "choose_edit":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                                         callback_data=f"edit_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to edit title:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "choose_editcat":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                                         callback_data=f"editcat_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to change category:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "choose_delete":
        keyboard = [[InlineKeyboardButton(f"{m['title']} ({'loved' if m['category']=='watched' else m['category']})", 
                                         callback_data=f"delete_{m['id']}")] for m in movies]
        query.edit_message_text(
            "Select a movie to delete:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def handle_new_title(update: Update, context: CallbackContext):
    """Handle new title input for movie editing."""
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
