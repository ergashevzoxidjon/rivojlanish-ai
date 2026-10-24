"""Bazani yaratadi va standart manbalarni qo'shadi:  python scripts/init_db.py"""
import _bootstrap  # noqa: F401

from app.collector import seed_sources
from app.db import init_db, session_scope

init_db()
with session_scope() as db:
    print("Jadvallar tayyor. Qo'shilgan manbalar:", seed_sources(db))
