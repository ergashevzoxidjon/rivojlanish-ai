"""API uchun umumiy yordamchilar: serializatsiya."""
from typing import Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..lessons import quiz_of, rank_of
from ..models import LEVELS, TOPICS, Lesson, User, UserLesson


def iso(dt) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "telegram_id": user.telegram_id,
        "telegram_username": user.telegram_username,
        "registered": user.is_registered,
        "topics": user.topic_list,
        "daily_count": user.daily_count,
        "notify": user.notify,
        "level": user.level,
        "level_name": LEVELS.get(user.level, ""),
        "xp": user.xp or 0,
        "rank": rank_of(user.xp or 0),
        "is_admin": user.is_admin,
    }


def progress_out(ul: Optional[UserLesson]) -> dict:
    if not ul:
        return {"sent": False, "read": False, "done": False, "quiz_score": None, "quiz_total": None}
    return {
        "sent": bool(ul.sent_at),
        "read": bool(ul.read_at),
        "done": bool(ul.done_at),
        "quiz_score": ul.quiz_score if ul.quiz_at else None,
        "quiz_total": abs(ul.quiz_total) if ul.quiz_at and ul.quiz_total else None,
    }


def progress_map(db: Session, user: Optional[User], lesson_ids) -> Dict[int, UserLesson]:
    if not user or not lesson_ids:
        return {}
    rows = db.scalars(
        select(UserLesson).where(UserLesson.user_id == user.id, UserLesson.lesson_id.in_(list(lesson_ids)))
    )
    return {r.lesson_id: r for r in rows}


def lesson_out(lesson: Lesson, ul: Optional[UserLesson] = None, full: bool = False, admin: bool = False) -> dict:
    data = {
        "id": lesson.id,
        "slug": lesson.slug,
        "title": lesson.title,
        "topic": lesson.topic,
        "topic_name": TOPICS.get(lesson.topic, lesson.topic),
        "tool": lesson.tool,
        "level": lesson.level,
        "level_name": LEVELS.get(lesson.level, ""),
        "minutes": lesson.minutes,
        "importance": lesson.importance,
        "summary": lesson.summary,
        "source_url": lesson.source_url,
        "origin": lesson.origin,
        "status": lesson.status,
        "published_at": iso(lesson.published_at),
        "created_at": iso(lesson.created_at),
        "quiz_count": len(quiz_of(lesson)),
        "progress": progress_out(ul),
    }
    if full:
        data["body_md"] = lesson.body_md
        data["task_md"] = lesson.task_md
        quiz = quiz_of(lesson)
        if admin:
            data["quiz"] = quiz
        else:
            # Javoblar faqat test topshirilgandan keyin ko'rsatiladi
            data["quiz"] = [{"q": q["q"], "options": q["options"]} for q in quiz]
    return data


def meta() -> dict:
    return {
        "app_name": settings.app_name,
        "topics": [{"key": k, "name": v} for k, v in TOPICS.items()],
        "levels": [{"key": k, "name": v} for k, v in LEVELS.items()],
        "google_client_id": settings.google_client_id,
        "bot_username": settings.bot_username,
        "daily_hour": settings.daily_hour,
        "daily_min": settings.daily_min_lessons,
        "daily_max": settings.daily_max_lessons,
    }
