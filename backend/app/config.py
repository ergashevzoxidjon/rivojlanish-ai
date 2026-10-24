"""Barcha sozlamalar .env faylidan o'qiladi."""
import hashlib
import hmac
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_bot_username_cache = None

# backend/ papkasi — .env, baza va maxfiy kalit shu yerda (joriy papkaga bog'liq emas)
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Rivojlanish AI"
    # Saytning to'liq manzili, masalan https://rivojlanish-ai.uz
    web_url: str = "http://localhost:5173"

    # Ma'lumotlar bazasi. Hostingda: mysql+pymysql://user:parol@localhost/baza_nomi
    # Bo'sh bo'lsa: backend/data/rivojlanish.db (SQLite)
    database_url: str = ""

    # Xavfsizlik
    # Bo'sh bo'lsa avtomatik yaratiladi va backend/data/secret.key da saqlanadi
    secret_key: str = ""
    jwt_days: int = 30

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    # Webhook so'rovlarini tekshirish uchun maxfiy so'z
    # Bo'sh bo'lsa SECRET_KEY dan hosil qilinadi
    telegram_webhook_secret: str = ""

    # Google
    google_client_id: str = ""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5-5"

    # Adminlar (vergul bilan ajratilgan email yoki telegram id lar)
    admin_emails: str = ""
    admin_telegram_ids: str = ""

    # Darslar
    timezone: str = "Asia/Tashkent"
    daily_hour: int = 8
    daily_min_lessons: int = 1
    daily_max_lessons: int = 3
    more_lessons_batch: int = 3
    # True bo'lsa AI yozgan dars darhol nashr qilinadi, False bo'lsa admin tasdiqlaydi
    auto_publish: bool = True
    # Bir yig'ishda AI eng ko'pi bilan nechta yangilikni darsga aylantiradi
    collect_max_items: int = 6

    # AI ustoz: bir foydalanuvchi kuniga nechta savol bera oladi
    tutor_daily_limit: int = 30
    # "Yana dars" bosilganda kuniga nechta yangi dars AI bilan yozilishi mumkin (har foydalanuvchiga)
    on_demand_daily_limit: int = 10

    # Cron skriptlarini HTTP orqali chaqirish uchun kalit (ixtiyoriy)
    cron_key: str = ""

    def model_post_init(self, __context) -> None:
        if not self.database_url:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite:///{DATA_DIR / 'rivojlanish.db'}"
        if not self.secret_key or self.secret_key == "change-me":
            self.secret_key = _load_or_create_secret()
        if not self.telegram_webhook_secret or self.telegram_webhook_secret == "change-me-too":
            self.telegram_webhook_secret = hmac.new(
                self.secret_key.encode(), b"telegram-webhook", hashlib.sha256
            ).hexdigest()[:48]

    def _split(self, value: str) -> List[str]:
        return [v.strip().lower() for v in value.split(",") if v.strip()]

    @property
    def bot_username(self) -> str:
        """TELEGRAM_BOT_USERNAME bo'sh bo'lsa, Telegram'dan bir marta so'raladi."""
        global _bot_username_cache
        if self.telegram_bot_username:
            return self.telegram_bot_username.lstrip("@")
        if _bot_username_cache is None and self.telegram_bot_token:
            try:
                import httpx

                r = httpx.get(f"https://api.telegram.org/bot{self.telegram_bot_token}/getMe", timeout=10)
                _bot_username_cache = r.json()["result"]["username"]
            except Exception:
                return ""
        return _bot_username_cache or ""

    @property
    def admin_email_list(self) -> List[str]:
        return self._split(self.admin_emails)

    @property
    def admin_telegram_list(self) -> List[str]:
        return self._split(self.admin_telegram_ids)


def _load_or_create_secret() -> str:
    """Server o'zi yaratgan, hech kimga ko'rsatilmaydigan maxfiy kalit."""
    path = DATA_DIR / "secret.key"
    try:
        if path.exists():
            value = path.read_text().strip()
            if len(value) >= 32:
                return value
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        value = secrets.token_hex(32)
        path.write_text(value)
        os.chmod(path, 0o600)
        return value
    except OSError:
        # Yozib bo'lmasa ham ishlasin (faqat test/vaqtinchalik muhit)
        return secrets.token_hex(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
