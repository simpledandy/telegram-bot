import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

_allowed = os.getenv("ALLOWED_CHAT_IDS")
if _allowed:
    ALLOWED_CHAT_IDS = {
        int(chat_id.strip())
        for chat_id in _allowed.split(",")
        if chat_id.strip()
    }
else:
    ALLOWED_CHAT_IDS = None

DB_PATH = os.getenv("DB_PATH", "bot.db")
