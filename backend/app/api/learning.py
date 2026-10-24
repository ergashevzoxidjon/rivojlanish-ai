"""Darslar, progress, testlar, takrorlash va AI ustoz."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import tutor
from ..auth import current_user_optional, registered_user
from ..db import get_db
from ..lessons import (
    answer_review,
    due_reviews,
    grade_quiz,
    local_day_start_utc,
    mark_done,
    mark_read,
    mark_sent,
    next_lessons_for_user,
    quiz_of,
    review_question_index,
    today_local,
)
from ..models import Lesson, User, UserLesson
from .common import iso, lesson_out, progress_map

router = APIRouter(prefix="/api")


class DoneIn(BaseModel):
    done: bool = True


class QuizIn(BaseModel):
    answers: List[int]


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ReviewIn(BaseModel):
    answer: int


def _published(db: Session, lesson_id: int) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or lesson.status != "published":
        raise HTTPException(404, "Dars topilmadi")
    return lesson


@router.get("/lessons")
def list_lessons(
    topic: Optional[str] = None,
    level: Optional[str] = None,
    tool: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100),
    state: Optional[str] = Query(default=None, pattern="^(done|todo|read)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=50),
    user: Optional[User] = Depends(current_user_optional),
    db: Session = Depends(get_db),
):
    query = select(Lesson).where(Lesson.status == "published")
    if topic:
        query = query.where(Lesson.topic == topic)
    if level:
        query = query.where(Lesson.level == level)
    if tool:
        query = query.where(Lesson.tool == tool)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Lesson.title.ilike(like), Lesson.summary.ilike(like), Lesson.tool.ilike(like)))
    if state and user:
        done_ids = select(UserLesson.lesson_id).where(
            UserLesson.user_id == user.id, UserLesson.done_at.is_not(None)
        )
        read_ids = select(UserLesson.lesson_id).where(
            UserLesson.user_id == user.id, UserLesson.read_at.is_not(None)
        )
        if state == "done":
            query = query.where(Lesson.id.in_(done_ids))
        elif state == "read":
            query = query.where(Lesson.id.in_(read_ids))
        else:
            query = query.where(Lesson.id.not_in(done_ids))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        db.scalars(query.order_by(Lesson.published_at.desc()).offset((page - 1) * size).limit(size))
    )
    pm = progress_map(db, user, [r.id for r in rows])
    return {"total": total, "page": page, "size": size, "items": [lesson_out(r, pm.get(r.id)) for r in rows]}


@router.get("/tools")
def list_tools(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Lesson.tool, func.count())
        .where(Lesson.status == "published", Lesson.tool != "")
        .group_by(Lesson.tool)
        .order_by(func.count().desc())
    ).all()
    return [{"tool": t, "count": c} for t, c in rows]


@router.get("/today")
def today(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    """Bugun yuborilgan darslar; agar hali yo'q bo'lsa — siz uchun eng mos darslar."""
    start = local_day_start_utc(today_local())
    sent_today = list(
        db.scalars(
            select(Lesson)
            .join(UserLesson, UserLesson.lesson_id == Lesson.id)
            .where(UserLesson.user_id == user.id, UserLesson.sent_at >= start)
            .order_by(UserLesson.sent_at)
        )
    )
    picks = sent_today or next_lessons_for_user(db, user, user.daily_count or 3)
    pm = progress_map(db, user, [p.id for p in picks])
    reviews = []
    for ul in due_reviews(db, user, limit=3):
        quiz = quiz_of(ul.lesson)
        qi = review_question_index(ul)
        reviews.append(
            {
                "id": ul.id,
                "lesson": {"title": ul.lesson.title, "slug": ul.lesson.slug},
                "question": quiz[qi]["q"],
                "options": quiz[qi]["options"],
            }
        )
    return {
        "lessons": [lesson_out(p, pm.get(p.id)) for p in picks],
        "from_daily": bool(sent_today),
        "reviews": reviews,
    }


@router.get("/lessons/{slug}")
def get_lesson(slug: str, user: Optional[User] = Depends(current_user_optional), db: Session = Depends(get_db)):
    lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
    if not lesson or (lesson.status != "published" and not (user and user.is_admin)):
        raise HTTPException(404, "Dars topilmadi")
    pm = progress_map(db, user, [lesson.id])
    data = lesson_out(lesson, pm.get(lesson.id), full=True)
    ul = pm.get(lesson.id)
    if ul and ul.quiz_at:
        # Test topshirilgan — to'g'ri javoblar va izohlar ochiladi
        data["quiz"] = [
            {"q": q["q"], "options": q["options"], "answer": q["answer"], "explain": q.get("explain", "")}
            for q in quiz_of(lesson)
        ]
    # O'xshash darslar: shu vosita yoki mavzu
    related = db.scalars(
        select(Lesson)
        .where(Lesson.status == "published", Lesson.id != lesson.id, Lesson.topic == lesson.topic)
        .order_by((Lesson.tool == lesson.tool).desc(), Lesson.published_at.desc())
        .limit(3)
    )
    data["related"] = [lesson_out(r) for r in related]
    return data


@router.post("/lessons/{lesson_id}/read")
def read_lesson(lesson_id: int, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    mark_read(db, user, _published(db, lesson_id))
    return {"ok": True, "xp": user.xp}


@router.post("/lessons/{lesson_id}/done")
def done_lesson(lesson_id: int, body: DoneIn, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    mark_done(db, user, _published(db, lesson_id), body.done)
    return {"ok": True, "xp": user.xp}


@router.post("/lessons/{lesson_id}/quiz")
def submit_quiz(lesson_id: int, body: QuizIn, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    result = grade_quiz(db, user, _published(db, lesson_id), body.answers)
    result["user_xp"] = user.xp
    result["user_level"] = user.level
    return result


@router.post("/reviews/{ul_id}")
def submit_review(ul_id: int, body: ReviewIn, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    ul = db.get(UserLesson, ul_id)
    if not ul or ul.user_id != user.id or ul.review_stage not in (1, 2):
        raise HTTPException(404, "Takrorlash topilmadi")
    quiz = quiz_of(ul.lesson)
    q = quiz[review_question_index(ul)]
    correct = body.answer == q["answer"]
    res = answer_review(db, user, ul, correct)
    return {"correct": correct, "answer": q["answer"], "explain": q.get("explain", ""), **res}


# ---------- AI ustoz ----------

def _chat_out(rows):
    return [{"id": r.id, "role": r.role, "content": r.content, "created_at": iso(r.created_at)} for r in rows]


def _ask(db: Session, user: User, question: str, lesson: Optional[Lesson]):
    try:
        answer = tutor.ask(db, user, question, lesson)
    except tutor.TutorLimit as e:
        raise HTTPException(429, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(503, "AI ustoz hozir javob bera olmadi. Birozdan keyin urinib ko'ring.")
    return {"answer": answer, "left": max(0, tutor.settings.tutor_daily_limit - tutor.questions_today(db, user))}


@router.get("/lessons/{lesson_id}/chat")
def lesson_chat(lesson_id: int, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    return _chat_out(tutor.history(db, user, _published(db, lesson_id).id))


@router.post("/lessons/{lesson_id}/ask")
def lesson_ask(lesson_id: int, body: AskIn, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    return _ask(db, user, body.question, _published(db, lesson_id))


@router.delete("/lessons/{lesson_id}/chat")
def lesson_chat_clear(lesson_id: int, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    tutor.clear(db, user, _published(db, lesson_id).id)
    return {"ok": True}


@router.get("/tutor")
def tutor_chat(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    return _chat_out(tutor.history(db, user, None, limit=40))


@router.post("/tutor")
def tutor_ask(body: AskIn, user: User = Depends(registered_user), db: Session = Depends(get_db)):
    return _ask(db, user, body.question, None)


@router.delete("/tutor")
def tutor_clear(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    tutor.clear(db, user, None)
    return {"ok": True}


# ---------- "Yana dars" (web) ----------

@router.post("/more")
def more_lessons(user: User = Depends(registered_user), db: Session = Depends(get_db)):
    """Tayyor darslardan keyingilarini beradi; tugagan bo'lsa AI bilan yangisini yozadi (~30-60 s)."""
    import random

    from .. import ai_writer
    from ..bot.service import on_demand_today
    from ..collector import recent_titles, save_lesson
    from ..config import settings
    from ..models import TOPICS

    ready = next_lessons_for_user(db, user, settings.more_lessons_batch)
    if ready:
        mark_sent(db, user, ready)
        return {"generated": False, "lessons": [lesson_out(r) for r in ready]}
    if on_demand_today(db, user) >= settings.on_demand_daily_limit:
        raise HTTPException(429, f"Bugun {settings.on_demand_daily_limit} ta qo'shimcha dars oldingiz. Ertaga davom etamiz!")
    topic = random.choice(user.topic_list or list(TOPICS))
    try:
        data = ai_writer.lesson_on_demand(topic, recent_titles(db, 365, topic), user.level)
    except Exception:
        data = None
    if not data:
        raise HTTPException(503, "Hozir yangi dars tayyorlab bo'lmadi. Birozdan keyin urinib ko'ring.")
    lesson = save_lesson(db, data, "on_demand", requested_by=user.id)
    mark_sent(db, user, [lesson])
    return {"generated": True, "lessons": [lesson_out(lesson)]}
