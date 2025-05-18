import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- Keyboard layouts ---
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Add Movie"), KeyboardButton("📋 List Movies")],
        [KeyboardButton("🎲 Random Movie"), KeyboardButton("🤝 Partner Status")],
        [KeyboardButton("🔗 Invite"), KeyboardButton("🔓 Unlink")]
    ], resize_keyboard=True)

def edit_delete_inline_keyboard(movie_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit Title", callback_data=f"edit_{movie_id}"),
            InlineKeyboardButton("🗂️ Edit Category", callback_data=f"editcat_{movie_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_{movie_id}")
        ]
    ])
