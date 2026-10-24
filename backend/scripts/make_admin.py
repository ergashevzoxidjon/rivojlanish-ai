"""Foydalanuvchini admin qiladi:  python scripts/make_admin.py email@gmail.com"""
import _bootstrap  # noqa: F401

import sys

from sqlalchemy import select

from app.db import init_db, session_scope
from app.models import User

init_db()
email = sys.argv[1].lower()
with session_scope() as db:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        sys.exit("Bunday email topilmadi — avval saytda Google orqali kiring.")
    user.is_admin = True
    print("Admin qilindi:", user.name, user.email)
