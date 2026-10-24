"""AI ustoz: dars bo'yicha yoki umumiy savollarga javob. Bot va web uchun umumiy."""
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import ai_writer
from .config import settings
from .lessons import local_day_start_utc, today_local, touch
from .models import Lesson, TutorMessage, User


class TutorLimit(Exception):
    pass


def questions_today(db: Session, user: User) -> int:
    start = local_day_start_utc(today_local())
    return db.scalar(
        select(func.count()).select_from(TutorMessage).where(
            TutorMessage.user_id == user.id,
            TutorMessage.role == "user",
            TutorMessage.created_at >= start,
        )
    ) or 0


def history(db: Session, user: User, lesson_id: Optional[int], limit: int = 20) -> List[TutorMessage]:
    q = select(TutorMessage).where(TutorMessage.user_id == user.id)
    q = q.where(TutorMessage.lesson_id == lesson_id) if lesson_id else q.where(TutorMessage.lesson_id.is_(None))
    rows = list(db.scalars(q.order_by(TutorMessage.id.desc()).limit(limit)))
    return list(reversed(rows))


def clear(db: Session, user: User, lesson_id: Optional[int]) -> None:
    for row in history(db, user, lesson_id, limit=1000):
        db.delete(row)
    db.commit()


def ask(db: Session, user: User, question: str, lesson: Optional[Lesson] = None) -> str:
    question = question.strip()[:2000]
    if not question:
        raise ValueError("Savol bo'sh")
    if questions_today(db, user) >= settings.tutor_daily_limit:
        raise TutorLimit(f"Bugungi limit tugadi ({settings.tutor_daily_limit} ta savol). Ertaga davom etamiz!")
    lesson_id = lesson.id if lesson else None
    past = [{"role": h.role, "content": h.content} for h in history(db, user, lesson_id, limit=8)]
    lesson_ctx = None
    if lesson:
        lesson_ctx = {
            "title": lesson.title,
            "tool": lesson.tool,
            "summary": lesson.summary,
            "body_md": lesson.body_md,
            "task_md": lesson.task_md,
        }
    answer = ai_writer.tutor_answer(question, past, lesson_ctx)
    db.add(TutorMessage(user_id=user.id, lesson_id=lesson_id, role="user", content=question))
    db.add(TutorMessage(user_id=user.id, lesson_id=lesson_id, role="assistant", content=answer))
    touch(user)
    db.commit()
    return answer
