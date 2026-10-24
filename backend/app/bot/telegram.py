"""Telegram Bot API bilan ishlash uchun kichik sinxron mijoz."""
import logging
from typing import Any, Optional

import httpx

from ..config import settings

log = logging.getLogger(__name__)


class TelegramError(Exception):
    pass


def call(method: str, **params: Any) -> Any:
    if not settings.telegram_bot_token:
        raise TelegramError("TELEGRAM_BOT_TOKEN sozlanmagan")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"
    payload = {k: v for k, v in params.items() if v is not None}
    r = httpx.post(url, json=payload, timeout=25)
    data = r.json()
    if not data.get("ok"):
        raise TelegramError(f"{method}: {data.get('description')}")
    return data.get("result")


def send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None, **kw: Any) -> Any:
    return call(
        "sendMessage",
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup,
        **kw,
    )


def safe_send(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """Foydalanuvchi botni bloklagan bo'lsa ham jarayon to'xtamasin."""
    try:
        send_message(chat_id, text, reply_markup)
        return True
    except Exception as e:
        log.warning("Xabar yuborilmadi %s: %s", chat_id, e)
        return False


def answer_callback(callback_id: str, text: str = "", alert: bool = False) -> None:
    try:
        call("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=alert)
    except Exception as e:
        log.warning("answerCallbackQuery: %s", e)


def edit_markup(chat_id: int, message_id: int, reply_markup: dict) -> None:
    try:
        call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
    except Exception as e:
        log.info("editMessageReplyMarkup: %s", e)


def edit_text(chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None) -> None:
    try:
        call(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.info("editMessageText: %s", e)
