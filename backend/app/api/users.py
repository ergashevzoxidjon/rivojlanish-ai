"""Kirish, profil, statistika, reyting."""
import secrets
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import (
    create_token,
    current_user,
    get_or_create_telegram_user,
    login_with_google,
    registered_user,
    verify_google_credential,
    verify_telegram_init_data,
)
from ..clock import utcnow
from ..config import settings
from ..db import get_db
from ..lessons import leaderboard, user_stats
from ..models import TOPICS, LinkToken, User
from .common import meta, user_out

router = APIRouter(prefix="/api")


class GoogleIn(BaseModel):
    credential: str
    link_token: Optional[str] = None


class TelegramIn(BaseModel):
    init_data: str


class MeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    topics: Optional[List[str]] = None
    daily_count: Optional[int] = None
    notify: Optional[bool] = None


@router.get("/meta")
def get_meta():
    return meta()


@router.post("/auth/google")
def auth_google(body: GoogleIn, db: Session = Depends(get_db)):
    info = verify_google_credential(body.credential)
    user = login_with_google(db, info, body.link_token)
    return {"token": create_token(user), "user": user_out(user)}


@router.post("/auth/telegram")
def auth_telegram(body: TelegramIn, db: Session = Depends(get_db)):
    tg = verify_telegram_init_data(body.init_data)
    if not tg.get("id"):
        raise HTTPException(400, "Telegram foydalanuvchisi topilmadi")
    user = get_or_create_telegram_user(db, tg)
    return {"token": create_token(user), "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.patch("/me")
def update_me(body: MeUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.name is not None and body.name.strip():
        user.name = body.name.strip()
    if body.topics is not None:
        topics = [t for t in TOPICS if t in body.topics]
        if not topics:
            raise HTTPException(400, "Kamida bitta mavzu tanlang")
        user.topics = ",".join(topics)
    if body.daily_count is not None:
        if not settings.daily_min_lessons <= body.daily_count <= settings.daily_max_lessons:
            raise HTTPException(400, "Darslar soni noto'g'ri")
        user.daily_count = body.daily_count
    if body.notify is not None:
        user.notify = body.notify
    db.commit()
    return user_out(user)


@router.post("/me/telegram-link")
def telegram_link(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Web'da ro'yxatdan o'tgan foydalanuvchi Telegram botni ulashi uchun havola."""
    token = secrets.token_urlsafe(16)
    db.add(LinkToken(token=token, user_id=user.id, expires_at=utcnow() + timedelta(days=2)))
    db.commit()
    return {"url": f"https://t.me/{settings.bot_username}?start=k_{token}"}


@router.post("/me/register-link")
def register_link(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Telegram Web App ichidagi (hali ro'yxatdan o'tmagan) foydalanuvchi uchun Google ro'yxat havolasi."""
    if not user.telegram_id:
        raise HTTPException(400, "Telegram akkaunt topilmadi")
    token = secrets.token_urlsafe(24)
    db.add(LinkToken(token=token, telegram_id=user.telegram_id, expires_at=utcnow() + timedelta(days=2)))
    db.commit()
    return {"url": settings.web_url.rstrip("/") + f"/register?t={token}"}


@router.get("/me/stats")
def my_stats(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    return user_stats(db, user)


@router.get("/leaderboard")
def get_leaderboard(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    rows = leaderboard(db, 20)
    for r in rows:
        r["me"] = r.pop("id") == user.id
    return rows
