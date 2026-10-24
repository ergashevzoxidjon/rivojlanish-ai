"""Kirish: Google (email), Telegram Web App initData va JWT."""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .clock import utcnow
from .config import settings
from .db import get_db
from .models import LinkToken, TutorMessage, User, UserLesson

ALGO = "HS256"


# ---------- JWT ----------

def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.jwt_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def decode_token(token: str) -> Optional[int]:
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
        return int(data["sub"])
    except Exception:
        return None


def current_user_optional(
    authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = decode_token(authorization.split(" ", 1)[1])
    if not user_id:
        return None
    return db.get(User, user_id)


def current_user(user: Optional[User] = Depends(current_user_optional)) -> User:
    if not user:
        raise HTTPException(status_code=401, detail="Kirish talab qilinadi")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Faqat admin uchun")
    return user


# ---------- Google ----------

def verify_google_credential(credential: str) -> dict:
    """Google Sign-In ID tokenini tekshiradi va foydalanuvchi ma'lumotini qaytaradi."""
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID sozlanmagan")
    try:
        info = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Google tokeni noto'g'ri")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email tasdiqlanmagan")
    return info


# ---------- Telegram Web App ----------

def verify_telegram_init_data(init_data: str, max_age: int = 86400) -> dict:
    """Telegram Web App initData imzosini tekshiradi.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="initData noto'g'ri")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256).digest()
    calc = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc, received_hash):
        raise HTTPException(status_code=401, detail="initData imzosi noto'g'ri")
    if max_age and time.time() - int(pairs.get("auth_date", "0")) > max_age:
        raise HTTPException(status_code=401, detail="initData eskirgan")
    return json.loads(pairs.get("user", "{}"))


# ---------- Foydalanuvchilarni topish / birlashtirish ----------

def apply_admin_flag(user: User) -> None:
    if user.email and user.email.lower() in settings.admin_email_list:
        user.is_admin = True
    if user.telegram_id and str(user.telegram_id) in settings.admin_telegram_list:
        user.is_admin = True


def get_or_create_telegram_user(db: Session, tg: dict) -> User:
    user = db.scalar(select(User).where(User.telegram_id == tg["id"]))
    if not user:
        name = " ".join(filter(None, [tg.get("first_name"), tg.get("last_name")])) or "Foydalanuvchi"
        user = User(telegram_id=tg["id"], name=name)
        db.add(user)
    if tg.get("username"):
        user.telegram_username = tg["username"]
    apply_admin_flag(user)
    db.commit()
    db.refresh(user)
    return user


def merge_users(db: Session, keep: User, other: User) -> None:
    """`other` dagi Telegram va progressni `keep` ga ko'chiradi, `other` ni o'chiradi."""
    if keep.id == other.id:
        return
    tg_id, tg_username = other.telegram_id, other.telegram_username
    existing = {
        ul.lesson_id: ul
        for ul in db.scalars(select(UserLesson).where(UserLesson.user_id == keep.id))
    }
    for ul in db.scalars(select(UserLesson).where(UserLesson.user_id == other.id)).all():
        mine = existing.get(ul.lesson_id)
        if mine:
            mine.sent_at = mine.sent_at or ul.sent_at
            mine.read_at = mine.read_at or ul.read_at
            mine.done_at = mine.done_at or ul.done_at
            db.execute(delete(UserLesson).where(UserLesson.id == ul.id))
        else:
            db.execute(update(UserLesson).where(UserLesson.id == ul.id).values(user_id=keep.id))
    db.execute(update(TutorMessage).where(TutorMessage.user_id == other.id).values(user_id=keep.id))
    keep.xp = (keep.xp or 0) + (other.xp or 0)
    db.flush()
    db.expire(other)
    db.expire(keep)
    db.delete(other)
    db.flush()
    if tg_id and not keep.telegram_id:
        keep.telegram_id = tg_id
        keep.telegram_username = tg_username


def login_with_google(db: Session, info: dict, link_token: Optional[str] = None) -> User:
    email = info["email"].lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email)
        db.add(user)
    user.google_sub = info.get("sub")
    user.name = info.get("name") or user.name or email.split("@")[0]
    user.avatar_url = info.get("picture") or user.avatar_url
    db.flush()

    if link_token:
        link = db.scalar(select(LinkToken).where(LinkToken.token == link_token))
        if link and not link.used and link.expires_at > utcnow() and link.telegram_id:
            tg_user = db.scalar(select(User).where(User.telegram_id == link.telegram_id))
            if tg_user and tg_user.id != user.id:
                merge_users(db, user, tg_user)
            elif not tg_user and not user.telegram_id:
                user.telegram_id = link.telegram_id
            link.used = True

    apply_admin_flag(user)
    db.commit()
    db.refresh(user)
    return user


def registered_user(user: User = Depends(current_user)) -> User:
    """Google (email) orqali ro'yxatdan o'tgan foydalanuvchi."""
    if not user.is_registered:
        raise HTTPException(status_code=403, detail="not_registered")
    return user
