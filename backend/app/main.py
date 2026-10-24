"""FastAPI ilovasi: API, Telegram webhook, cron va React frontend (static)."""
import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import bg
from .api import admin, learning, users
from .bot.handlers import handle_update
from .config import settings
from .db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rivojlanish")



def check_config() -> None:
    if settings.web_url.startswith("https://") and settings.secret_key in ("", "change-me"):
        raise RuntimeError("SECRET_KEY sozlanmagan — .env faylida uzun tasodifiy qiymat bering")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    check_config()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name, docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(learning.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"ok": True, "app": settings.app_name}


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    request: Request, x_telegram_bot_api_secret_token: Optional[str] = Header(default=None)
):
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret):
        raise HTTPException(403, "forbidden")
    update = await request.json()
    # Telegram tez javob kutadi — qayta ishlashni alohida oqimda bajaramiz
    bg.run_bg(handle_update, update)
    return {"ok": True}


@app.get("/api/cron/{job}")
def cron(job: str, key: str = ""):
    """Hosting cron'i skript o'rniga URL chaqira olsa: /api/cron/collect?key=..."""
    if not settings.cron_key or not hmac.compare_digest(key, settings.cron_key):
        raise HTTPException(403, "forbidden")
    from .jobs import run_job

    if job not in ("collect", "daily"):
        raise HTTPException(404)
    bg.run_bg(run_job, job)
    return {"started": job}


# ---------- Frontend (React build) ----------

STATIC_DIR = Path(__file__).parent / "static"

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.exception_handler(404)
async def spa_fallback(request: Request, exc):
    path = request.url.path
    if path.startswith("/api/"):
        detail = getattr(exc, "detail", "Topilmadi")
        return JSONResponse({"detail": detail}, status_code=404)
    candidate = STATIC_DIR / path.lstrip("/")
    if path != "/" and candidate.is_file() and STATIC_DIR in candidate.resolve().parents:
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Frontend hali build qilinmagan"}, status_code=404)
