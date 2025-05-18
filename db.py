import os
import uuid
import random
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# --- Supabase DB helpers ---
load_dotenv(override=True)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user_by_chat_id(chat_id):
    return supabase.table("users").select("*").eq("chat_id", str(chat_id)).execute()

def insert_user(chat_id):
    return supabase.table("users").insert({"chat_id": str(chat_id)}).execute()
