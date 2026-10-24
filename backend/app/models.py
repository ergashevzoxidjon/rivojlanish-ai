from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# Mavzular: kalit -> nomi
TOPICS = {
    "chat": "Claude / ChatGPT / Gemini",
    "coding": "Kod yozish AI'lari",
    "automation": "Avtomatlashtirish va agentlar",
}
LEVELS = {"beginner": "Boshlang'ich", "intermediate": "O'rta", "advanced": "Ilg'or"}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    google_sub: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(64))
    # Vergul bilan: "chat,coding,automation"
    topics: Mapped[str] = mapped_column(String(100), default="chat,coding,automation")
    daily_count: Mapped[int] = mapped_column(Integer, default=3)
    notify: Mapped[bool] = mapped_column(Boolean, default=True)
    # Test natijalariga qarab avtomatik o'zgaradi: beginner | intermediate | advanced
    level: Mapped[str] = mapped_column(String(20), default="beginner")
    xp: Mapped[int] = mapped_column(Integer, default=0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Foydalanuvchi botni bloklagan bo'lsa xabar yuborilmaydi
    bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Botda "Savol berish" bosilganda qaysi dars haqida so'ralayotgani
    tutor_lesson_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lessons: Mapped[list["UserLesson"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def topic_list(self) -> list:
        return [t for t in self.topics.split(",") if t in TOPICS]

    @property
    def is_registered(self) -> bool:
        return bool(self.email)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    # rss (RSS/Atom, GitHub releases.atom ham) | html (sahifa o'zgarishi)
    kind: Mapped[str] = mapped_column(String(20), default="rss")
    topic: Mapped[str] = mapped_column(String(20), default="chat")
    tool: Mapped[str] = mapped_column(String(40), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    # html turidagi manbalar uchun oxirgi ko'rilgan matn
    snapshot: Mapped[Optional[str]] = mapped_column(Text)


class RawItem(Base):
    __tablename__ = "raw_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    uid: Mapped[str] = mapped_column(String(255), unique=True)  # url yoki guid
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # new | skipped | lesson | error
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source: Mapped[Source] = relationship()


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    topic: Mapped[str] = mapped_column(String(20), default="chat", index=True)
    tool: Mapped[str] = mapped_column(String(40), default="")
    level: Mapped[str] = mapped_column(String(20), default="beginner")
    minutes: Mapped[int] = mapped_column(Integer, default=5)
    summary: Mapped[str] = mapped_column(Text, default="")
    body_md: Mapped[str] = mapped_column(Text, default="")
    task_md: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    # AI bahosi: 1 (ahamiyatsiz) .. 10 (juda muhim). Kunlik tanlovda ishlatiladi
    importance: Mapped[int] = mapped_column(Integer, default=5, index=True)
    # JSON: [{"q": "...", "options": ["..", ".."], "answer": 0, "explain": "..."}]
    quiz_json: Mapped[str] = mapped_column(Text, default="[]")
    # news | on_demand | manual
    origin: Mapped[str] = mapped_column(String(20), default="news")
    # draft | published | rejected
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    raw_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("raw_items.id"))
    # on_demand darslar: kim so'ragan (kunlik limit uchun)
    requested_by: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserLesson(Base):
    """Foydalanuvchi va dars: yuborildi / o'qidi / bajardi."""

    __tablename__ = "user_lessons"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    done_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    quiz_score: Mapped[Optional[int]] = mapped_column(Integer)
    quiz_total: Mapped[Optional[int]] = mapped_column(Integer)
    quiz_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Takrorlash: 0 = hali yo'q, 1 = 3 kunlik, 2 = 7 kunlik, 3 = tugadi
    review_stage: Mapped[int] = mapped_column(Integer, default=0)
    review_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

    user: Mapped[User] = relationship(back_populates="lessons")
    lesson: Mapped[Lesson] = relationship()


class DailyRun(Base):
    """Har kuni ertalabki yuborish bir marta bajarilishi uchun."""

    __tablename__ = "daily_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LinkToken(Base):
    """Telegram akkauntini Google akkaunt bilan bog'lash uchun bir martalik kod."""

    __tablename__ = "link_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    user_id: Mapped[Optional[int]] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class TutorMessage(Base):
    """AI ustoz bilan suhbat (dars bo'yicha savol-javob)."""

    __tablename__ = "tutor_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    # user | assistant
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class JobLog(Base):
    """Cron ishlari jurnali (admin panelda ko'rinadi)."""

    __tablename__ = "job_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job: Mapped[str] = mapped_column(String(40), index=True)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
