import logging

from fastapi import FastAPI, Header, HTTPException, Request
from aiogram.types import Update

from bot import bot, dp
from config import APP_BASE_URL, WEBHOOK_SECRET

logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
) -> dict[str, bool]:
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning(
            "Webhook rejected due to invalid secret token for path %s",
            request.url.path,
        )
        raise HTTPException(status_code=403, detail="Invalid webhook token")

    payload = await request.json()
    update = Update.model_validate(payload)
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.get("/health")
@app.get("/")
async def health_api_webhook() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "ladybot-webhook",
        "webhook": f"{APP_BASE_URL}/api/webhook" if APP_BASE_URL else "/api/webhook",
    }
