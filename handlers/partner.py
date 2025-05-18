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
    chat_id = str(update.effective_chat.id)
    invite_code = f"INV-{uuid.uuid4().hex[:6]}"
    logging.info(f"Generated invite code {invite_code} for chat_id: {chat_id}")
    supabase.table("users").update({"invite_code": invite_code}).eq("chat_id", chat_id).execute()
    text = (
        f"🔗 <b>Your invite code:</b> <code>{invite_code}</code>\n\n"
        "Send this code to your friend.\n"
        "They should use <b>/join &lt;code&gt;</b> to connect with you.\n\n"
        "<i>Note: The code can only be used once.</i>"
    )
    update.message.reply_text(text, parse_mode='HTML')

def join(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    logging.info(f"/join command received from chat_id: {chat_id}")
    try:
        invite_code = context.args[0]
        logging.info(f"Attempting to join with invite code: {invite_code}")
        inviter = supabase.table("users").select("*").eq("invite_code", invite_code).execute()
        if not inviter.data:
            logging.warning(f"Invalid invite code: {invite_code} from chat_id: {chat_id}")
            update.message.reply_text("❌ Invalid invite code! Please check the code and try again.")
            return
        inviter_id = inviter.data[0]["id"]
        supabase.table("users").update({"partner_id": inviter_id}).eq("chat_id", chat_id).execute()
        supabase.table("users").update({"partner_id": supabase.table("users").select("id").eq("chat_id", chat_id).execute().data[0]["id"]}).eq("id", inviter_id).execute()
        supabase.table("users").update({"invite_code": None}).eq("id", inviter_id).execute()
        logging.info(f"Users paired: chat_id {chat_id} with inviter_id {inviter_id}")
        update.message.reply_text(
            "✅ <b>Successfully paired!</b>\n\n"
            "You can now add movies together and share your lists.\n"
            "Try <b>/add</b> to add your first movie!",
            parse_mode='HTML'
        )
    except IndexError:
        logging.warning(f"No invite code provided by chat_id: {chat_id}")
        update.message.reply_text("Please provide an invite code: /join <code>")

def partner_status(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        update.message.reply_text(
            "🤝 <b>You are paired with someone!</b>\n\n"
            "You can add and share movies together.",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "🙅 <b>You are not paired yet.</b>\n\n"
            "Use /invite to generate a code or ask your friend for one.",
            parse_mode='HTML'
        )

def unlink(update: Update, context: CallbackContext):
    chat_id = str(update.effective_chat.id)
    user = supabase.table("users").select("id, partner_id").eq("chat_id", chat_id).execute().data[0]
    if user["partner_id"]:
        supabase.table("users").update({"partner_id": None}).eq("id", user["partner_id"]).execute()
        supabase.table("users").update({"partner_id": None}).eq("chat_id", chat_id).execute()
        update.message.reply_text(
            "🔓 <b>You have been unlinked from your partner.</b>\n\n"
            "You can now use /invite or /join to pair with someone else.",
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "You are not paired.",
            parse_mode='HTML'
        )
