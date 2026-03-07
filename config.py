import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "")

DATABASE_URL = os.getenv("DATABASE_URL")
