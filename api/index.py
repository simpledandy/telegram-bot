from fastapi import FastAPI

from config import APP_BASE_URL

app = FastAPI()


@app.get("/")
async def index() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "ladybot",
        "webhook": f"{APP_BASE_URL}/api/webhook" if APP_BASE_URL else "/api/webhook",
    }


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
