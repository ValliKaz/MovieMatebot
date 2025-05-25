import os
import uuid
import random
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext
from supabase import create_client, Client
from db import supabase

# --- Partner-related handlers ---
def invite(update: Update, context: CallbackContext):
    """Generate and send an invite code."""
    chat_id = str(update.effective_chat.id)
    invite_code = f"INV-{uuid.uuid4().hex[:6]}"
    logging.info(f"Generated invite code {invite_code} for chat_id: {chat_id}")
    supabase.table("users").update({"invite_code": invite_code}).eq("chat_id", chat_id).execute()
    text = (
        f"🎟️ <b>Your invite code:</b> <code>{invite_code}</code>\n\n"
        "1️⃣ Share this code with your friend\n"
        "2️⃣ They should use <code>/join {code}</code>\n"
        "3️⃣ Start sharing movies together!\n\n"
        "<i>Note: This code can only be used once</i>"
    )
    update.message.reply_text(text, parse_mode='HTML')

def join(update: Update, context: CallbackContext):
    """Join a partner using their invite code."""
    chat_id = str(update.effective_chat.id)
    logging.info(f"/join command received from chat_id: {chat_id}")
    try:
        invite_code = context.args[0]
        logging.info(f"Attempting to join with invite code: {invite_code}")
        inviter = supabase.table("users").select("*").eq("invite_code", invite_code).execute()
        if not inviter.data:
            logging.warning(f"Invalid invite code: {invite_code} from chat_id: {chat_id}")
            update.message.reply_text(
                "❌ Invalid invite code!\n\n"
                "🔍 Please check the code and try again\n"
                "💡 Or ask your friend to generate a new one with /invite"
            )
            return
        inviter_id = inviter.data[0]["id"]
        supabase.table("users").update({"partner_id": inviter_id}).eq("chat_id", chat_id).execute()
        supabase.table("users").update({"partner_id": supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]}).eq("id", inviter_id).execute()
        supabase.table("users").update({"invite_code": None}).eq("id", inviter_id).execute()
        logging.info(f"Users paired: chat_id {chat_id} with inviter_id {inviter_id}")
        update.message.reply_text(
            "🎉 <b>Successfully paired!</b>\n\n"
            "Try these commands together:\n"
            "➕ /add - Add movies to your shared lists\n"
            "📋 /list - View your movie lists\n"
            "🎲 /random - Get a movie suggestion\n"
            "✨ Have fun watching together!",
            parse_mode='HTML'
        )
    except IndexError:
        logging.warning(f"No invite code provided by chat_id: {chat_id}")
        update.message.reply_text(
            "ℹ️ How to join:\n"
            "1️⃣ Get the invite code from your friend\n"
            "2️⃣ Use: /join <code>your_code</code>"
        )

def partner_status(update: Update, context: CallbackContext):
    """Check partner status and show relevant information."""
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        # Get partner's Telegram user
        partner_user = context.bot.get_chat(
            supabase.table("users")
            .select("chat_id")
            .eq("id", user["partner_id"])
            .execute()
            .data[0]["chat_id"]
        )
        partner_name = partner_user.first_name or partner_user.full_name or "your friend"
        update.message.reply_text(
            f"👥 <b>You are paired with {partner_name}!</b>\n\n"
            "Together you can:\n"
            "🎬 Share movie lists\n"
            "📝 Add and edit movies\n"
            "🎲 Get movie suggestions\n"
            "❤️ Track favorites",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "🔄 <b>You are not paired yet</b>\n\n"
            "To connect with a friend:\n"
            "1️⃣ Use /invite to generate a code\n"
            "2️⃣ Share the code with your friend\n"
            "3️⃣ They use /join with your code",
            parse_mode='HTML'
        )

def unlink(update: Update, context: CallbackContext):
    """Unlink from current partner."""
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        supabase.table("users").update({"partner_id": None}).eq("id", user["partner_id"]).execute()
        supabase.table("users").update({"partner_id": None}).eq("chat_id", chat_id).execute()
        update.message.reply_text(
            "🔓 <b>Successfully unlinked!</b>\n\n"
            "You can now:\n"
            "🎟️ Generate a new invite code with /invite\n"
            "🤝 Join someone else with /join\n"
            "✨ Start fresh with a new partner!",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "ℹ️ You are not paired with anyone.\n\n"
            "Use /invite to generate a code and start sharing movies!",
            parse_mode='HTML'
        )
