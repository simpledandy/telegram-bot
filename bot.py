import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.commands import router as commands_router
from handlers.joins import router as joins_router
from handlers.moderation import router as moderation_router


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger().setLevel(logging.INFO)


setup_logging()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required.")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
dp.include_router(joins_router)
dp.include_router(moderation_router)
dp.include_router(commands_router)


if __name__ == "__main__":
    dp.run_polling(bot)
