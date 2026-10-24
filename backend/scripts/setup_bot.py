"""Telegram webhook, buyruqlar va menyu tugmasini o'rnatadi (WEB_URL tayyor bo'lgach bir marta):
   python scripts/setup_bot.py
"""
import _bootstrap  # noqa: F401

import json

from app.bot.handlers import setup_bot

print(json.dumps(setup_bot(), indent=2, ensure_ascii=False))
