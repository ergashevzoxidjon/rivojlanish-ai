"""Bot orqali dars yuborish: ertalabki yuborish, "Yana dars", takrorlash savollari."""
import logging
import random
import threading
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import ai_writer, bg
from ..clock import utcnow
from ..collector import recent_titles, save_lesson
from ..config import settings
from ..db import session_scope
from ..lessons import (
    due_reviews,
    local_day_start_utc,
    mark_sent,
    next_lessons_for_user,
    now_local,
    quiz_of,
    review_question_index,
    today_local,
    user_stats,
)
from ..models import DailyRun, JobLog, Lesson, User, UserLesson
from . import messages as m
from .telegram import TelegramError, send_message

log = logging.getLogger(__name__)

_generating: set = set()  # hozir AI dars yozayotgan foydalanuvchilar
_lock = threading.Lock()


def _send(user: User, text: str, markup: Optional[dict] = None) -> bool:
    try:
        send_message(user.telegram_id, text, markup)
        return True
    except TelegramError as e:
        if "blocked" in str(e).lower() or "deactivated" in str(e).lower():
            user.bot_blocked = True
        log.warning("Yuborilmadi %s: %s", user.telegram_id, e)
        return False
    except Exception as e:
        log.warning("Yuborilmadi %s: %s", user.telegram_id, e)
        return False


def send_lessons(db: Session, user: User, lessons: List[Lesson]) -> int:
    sent = []
    for i, lesson in enumerate(lessons, 1):
        if _send(user, m.lesson_text(lesson, i if len(lessons) > 1 else None), m.lesson_keyboard(lesson)):
            sent.append(lesson)
    mark_sent(db, user, sent)
    return len(sent)


def review_markup(ul: UserLesson) -> Optional[dict]:
    quiz = quiz_of(ul.lesson)
    if not quiz:
        return None
    qi = review_question_index(ul)
    q = quiz[qi]
    return {
        "inline_keyboard": [
            [{"text": opt, "callback_data": f"rv:{ul.id}:{qi}:{oi}"}] for oi, opt in enumerate(q["options"])
        ]
    }


def send_review(db: Session, user: User, ul: UserLesson) -> bool:
    quiz = quiz_of(ul.lesson)
    if not quiz:
        return False
    q = quiz[review_question_index(ul)]
    text = (
        "🧠 <b>Takrorlash vaqti!</b>\n"
        f"<i>{m.e(ul.lesson.title)}</i> darsidan bitta savol:\n\n"
        f"❓ {m.e(q['q'])}"
    )
    return _send(user, text, review_markup(ul))


# ---------- "Yana dars" ----------

def on_demand_today(db: Session, user: User) -> int:
    start = local_day_start_utc(today_local())
    return db.scalar(
        select(func.count()).select_from(Lesson).where(
            Lesson.requested_by == user.id, Lesson.created_at >= start
        )
    ) or 0


def request_more(db: Session, user: User) -> str:
    """Natija: "sent" | "generating" | "busy" | "limit"."""
    lessons = next_lessons_for_user(db, user, settings.more_lessons_batch)
    if lessons:
        send_lessons(db, user, lessons)
        _send(user, f"Yana kerak bo'lsa — <b>{m.BTN_MORE}</b> 👇", m.more_keyboard())
        return "sent"
    with _lock:
        if user.id in _generating:
            return "busy"
    if on_demand_today(db, user) >= settings.on_demand_daily_limit:
        return "limit"
    with _lock:
        _generating.add(user.id)
    bg.run_bg(_generate_worker, user.id)
    return "generating"


def _generate_worker(user_id: int) -> None:
    try:
        with session_scope() as db:
            user = db.get(User, user_id)
            if not user:
                return
            topics = user.topic_list or ["chat", "coding", "automation"]
            random.shuffle(topics)
            count = min(settings.more_lessons_batch, settings.on_demand_daily_limit - on_demand_today(db, user))
            made: List[Lesson] = []
            for i in range(max(1, count)):
                topic = topics[i % len(topics)]
                try:
                    data = ai_writer.lesson_on_demand(topic, recent_titles(db, days=365, topic=topic), user.level)
                except Exception as e:
                    log.warning("On-demand dars xatosi: %s", e)
                    continue
                if data:
                    made.append(save_lesson(db, data, "on_demand", requested_by=user.id))
            if made:
                send_lessons(db, user, made)
                _send(user, f"Yana kerak bo'lsa — <b>{m.BTN_MORE}</b> 👇", m.more_keyboard())
            else:
                _send(user, "😔 Hozir yangi dars tayyorlab bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
    finally:
        with _lock:
            _generating.discard(user_id)


# ---------- Ertalabki yuborish ----------

def run_daily(db: Session, force: bool = False) -> dict:
    """Har soat cron orqali chaqiriladi. Soat DAILY_HOUR dan keyin, kuniga bir marta yuboradi."""
    now = now_local()
    today = now.date()
    if not force:
        if now.hour < settings.daily_hour:
            return {"status": "early", "hour": now.hour}
        if db.scalar(select(DailyRun.id).where(DailyRun.day == today)):
            return {"status": "already"}
    run = db.scalar(select(DailyRun).where(DailyRun.day == today))
    if not run:
        run = DailyRun(day=today, sent_count=0)
        db.add(run)
        db.commit()  # avval yozib qo'yamiz — ikki marta yuborilmasin

    users = db.scalars(
        select(User).where(
            User.telegram_id.is_not(None),
            User.email.is_not(None),
            User.notify.is_(True),
            User.bot_blocked.is_(False),
        )
    ).all()
    total_users = total_lessons = 0
    for user in users:
        count = max(settings.daily_min_lessons, min(settings.daily_max_lessons, user.daily_count or 3))
        lessons = next_lessons_for_user(db, user, count)
        reviews = due_reviews(db, user, limit=1)
        if not lessons and not reviews:
            _send(
                user,
                "☀️ Xayrli tong! Bugun yangi yangilik bo'yicha dars hali yo'q.\n"
                f"Lekin <b>{m.BTN_MORE}</b> tugmasi orqali o'zingizga mos dars olishingiz mumkin 👇",
                m.more_keyboard(),
            )
            continue
        streak = user_stats(db, user)["streak"]
        streak_note = f"\n🔥 Ketma-ket {streak} kun — davom eting!" if streak >= 2 else ""
        header = (
            f"☀️ <b>Xayrli tong, {m.e((user.name or '').split(' ')[0])}!</b>\n"
            f"Bugungi {len(lessons)} ta dars tayyor.{streak_note}"
            if lessons
            else "☀️ <b>Xayrli tong!</b>"
        )
        if not _send(user, header):
            db.commit()
            continue
        total_users += 1
        total_lessons += send_lessons(db, user, lessons)
        for ul in reviews:
            send_review(db, user, ul)
        _send(
            user,
            f"Vaqtingiz ko'p bo'lsa — <b>{m.BTN_MORE}</b> tugmasini bosing, yana darslar olasiz 👇",
            m.more_keyboard(),
        )
    run.sent_count = total_users
    db.add(JobLog(job="daily", ok=True, message=f"{total_users} foydalanuvchiga {total_lessons} ta dars"))
    db.commit()
    return {"status": "sent", "users": total_users, "lessons": total_lessons}


def broadcast(db: Session, text: str) -> int:
    users = db.scalars(
        select(User).where(User.telegram_id.is_not(None), User.bot_blocked.is_(False))
    ).all()
    ok = sum(1 for u in users if _send(u, text))
    db.add(JobLog(job="broadcast", ok=True, message=f"{ok}/{len(users)} ga yuborildi"))
    db.commit()
    return ok


def log_job(db: Session, job: str, ok: bool, message: str) -> None:
    db.add(JobLog(job=job, ok=ok, message=message[:5000], created_at=utcnow()))
    db.commit()
