"""Barcha sozlamalar .env faylidan o'qiladi."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


_bot_username_cache = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Rivojlanish AI"
    # Saytning to'liq manzili, masalan https://rivojlanish-ai.uz
    web_url: str = "http://localhost:5173"

    # Ma'lumotlar bazasi. Hostingda: mysql+pymysql://user:parol@localhost/baza_nomi
    database_url: str = "sqlite:///./rivojlanish.db"

    # Xavfsizlik
    secret_key: str = "change-me"
    jwt_days: int = 30

    # Telegram
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    # Webhook so'rovlarini tekshirish uchun maxfiy so'z
    telegram_webhook_secret: str = "change-me-too"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
