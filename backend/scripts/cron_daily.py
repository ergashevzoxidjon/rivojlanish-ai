"""Ertalabki darslarni yuboradi. Cron: HAR SOAT (skript o'zi Toshkent vaqti 8:00 dan keyin
kuniga bir marta yuboradi, server vaqt mintaqasidan qat'i nazar).
   5 * * * *  cd ~/rivojlanish-ai/backend && ~/virtualenv/.../bin/python scripts/cron_daily.py
"""
import _bootstrap  # noqa: F401

from app.jobs import run_job

print(run_job("daily"))
