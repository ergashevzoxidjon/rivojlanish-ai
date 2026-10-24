"""Admin panel API."""
import json
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import ai_writer, bg
from ..ai_writer import clean_quiz
from ..auth import admin_user
from ..bot import service
from ..clock import utcnow
from ..collector import (
    collect_all,
    process_new_items,
    recent_titles,
    save_lesson,
    seed_sources,
)
from ..db import get_db, session_scope
from ..lessons import local_day_start_utc, slugify, today_local
from ..models import (
    LEVELS,
    TOPICS,
    JobLog,
    Lesson,
    RawItem,
    Source,
    TutorMessage,
    User,
    UserLesson,
)
from .common import iso, lesson_out, user_out

router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_user)])

_running: set = set()


class LessonIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    topic: str
    tool: str = ""
    level: str = "beginner"
    minutes: int = Field(default=7, ge=1, le=120)
    importance: int = Field(default=5, ge=1, le=10)
    summary: str
    body_md: str
    task_md: str
    source_url: str = ""
    quiz: list = []
    status: Optional[str] = None


class SourceIn(BaseModel):
    name: str
    url: str
    kind: str = Field(default="rss", pattern="^(rss|html)$")
    topic: str
    tool: str = ""
    active: bool = True


class GenerateIn(BaseModel):
    topic: str
    level: str = "beginner"


class BroadcastIn(BaseModel):
    text: str = Field(min_length=1, max_length=3500)


class DailyIn(BaseModel):
    force: bool = False


def _validate(body: LessonIn):
    if body.topic not in TOPICS:
        raise HTTPException(400, "Mavzu noto'g'ri")
    if body.level not in LEVELS:
        raise HTTPException(400, "Daraja noto'g'ri")


def _run_bg(name: str, fn):
    """Uzoq ishni fon oqimida bajaradi va natijani jurnalga yozadi."""
    if name in _running:
        raise HTTPException(409, "Bu ish allaqachon bajarilmoqda")
    _running.add(name)

    def work():
        try:
            with session_scope() as db:
                msg = fn(db)
                service.log_job(db, name, True, str(msg))
        except Exception as e:
            with session_scope() as db:
                service.log_job(db, name, False, repr(e))
        finally:
            _running.discard(name)

    bg.run_bg(work)
    return {"started": True}


# ---------- Umumiy ko'rinish ----------

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    week_ago = utcnow() - timedelta(days=7)
    day_ago = utcnow() - timedelta(days=1)

    def count(q):
        return db.scalar(q) or 0

    lessons_by_status = dict(db.execute(select(Lesson.status, func.count()).group_by(Lesson.status)).all())
    raw_by_status = dict(db.execute(select(RawItem.status, func.count()).group_by(RawItem.status)).all())
    daily = []
    today = today_local()
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        start = local_day_start_utc(day)  # Toshkent kuni bo'yicha
        end = local_day_start_utc(day + timedelta(days=1))
        daily.append(
            {
                "day": day.isoformat(),
                "done": count(select(func.count()).select_from(UserLesson).where(
                    UserLesson.done_at >= start, UserLesson.done_at < end)),
                "new_users": count(select(func.count()).select_from(User).where(
                    User.created_at >= start, User.created_at < end)),
            }
        )
    return {
        "users": count(select(func.count()).select_from(User)),
        "registered": count(select(func.count()).select_from(User).where(User.email.is_not(None))),
        "with_telegram": count(select(func.count()).select_from(User).where(User.telegram_id.is_not(None))),
        "active_7d": count(select(func.count()).select_from(User).where(User.last_active_at >= week_ago)),
        "active_1d": count(select(func.count()).select_from(User).where(User.last_active_at >= day_ago)),
        "blocked": count(select(func.count()).select_from(User).where(User.bot_blocked.is_(True))),
        "lessons": lessons_by_status,
        "raw_items": raw_by_status,
        "done_total": count(select(func.count()).select_from(UserLesson).where(UserLesson.done_at.is_not(None))),
        "tutor_questions_7d": count(select(func.count()).select_from(TutorMessage).where(
            TutorMessage.role == "user", TutorMessage.created_at >= week_ago)),
        "daily": daily,
        "running": sorted(_running),
    }


# ---------- Darslar ----------

@router.get("/lessons")
def admin_lessons(
    status: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
):
    query = select(Lesson)
    if status:
        query = query.where(Lesson.status == status)
    if q:
        query = query.where(Lesson.title.ilike(f"%{q}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Lesson.created_at.desc()).offset((page - 1) * 20).limit(20))
    return {"total": total, "items": [lesson_out(r) for r in rows]}


@router.get("/lessons/{lesson_id}")
def admin_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404)
    data = lesson_out(lesson, full=True, admin=True)
    stats = db.execute(
        select(
            func.count(UserLesson.sent_at), func.count(UserLesson.read_at), func.count(UserLesson.done_at)
        ).where(UserLesson.lesson_id == lesson.id)
    ).one()
    data["stats"] = {"sent": stats[0], "read": stats[1], "done": stats[2]}
    return data


def _apply(lesson: Lesson, body: LessonIn):
    lesson.title = body.title.strip()
    lesson.topic = body.topic
    lesson.tool = body.tool.strip()
    lesson.level = body.level
    lesson.minutes = body.minutes
    lesson.importance = body.importance
    lesson.summary = body.summary.strip()
    lesson.body_md = body.body_md.strip()
    lesson.task_md = body.task_md.strip()
    lesson.source_url = body.source_url.strip()
    lesson.quiz_json = json.dumps(clean_quiz(body.quiz), ensure_ascii=False)


@router.post("/lessons")
def create_lesson(body: LessonIn, db: Session = Depends(get_db)):
    _validate(body)
    lesson = Lesson(slug=slugify(body.title), origin="manual", status="draft")
    _apply(lesson, body)
    if body.status == "published":
        lesson.status, lesson.published_at = "published", utcnow()
    db.add(lesson)
    db.commit()
    return lesson_out(lesson, full=True, admin=True)


@router.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, body: LessonIn, db: Session = Depends(get_db)):
    _validate(body)
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404)
    _apply(lesson, body)
    db.commit()
    return lesson_out(lesson, full=True, admin=True)


@router.post("/lessons/{lesson_id}/{action}")
def lesson_action(lesson_id: int, action: str, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404)
    if action == "publish":
        lesson.status = "published"
        lesson.published_at = lesson.published_at or utcnow()
    elif action == "reject":
        lesson.status = "rejected"
    elif action == "draft":
        lesson.status = "draft"
    else:
        raise HTTPException(400, "Noma'lum amal")
    db.commit()
    return lesson_out(lesson)


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404)
    for row in db.scalars(select(UserLesson).where(UserLesson.lesson_id == lesson_id)):
        db.delete(row)
    for row in db.scalars(select(TutorMessage).where(TutorMessage.lesson_id == lesson_id)):
        db.delete(row)
    db.delete(lesson)
    db.commit()
    return {"ok": True}


@router.post("/generate")
def generate(body: GenerateIn, db: Session = Depends(get_db)):
    """AI bilan mavzu bo'yicha qoralama dars yozdirish (sinxron, ~30-60 soniya)."""
    if body.topic not in TOPICS:
        raise HTTPException(400, "Mavzu noto'g'ri")
    try:
        data = ai_writer.lesson_on_demand(body.topic, recent_titles(db, 365, body.topic), body.level)
    except Exception as e:
        raise HTTPException(503, f"AI xatosi: {e}")
    if not data:
        raise HTTPException(503, "AI to'liq dars qaytarmadi")
    lesson = save_lesson(db, data, "manual")
    if lesson.status == "published":
        # Admin o'zi ko'rib chiqishi uchun qoralama sifatida qoldiramiz
        lesson.status, lesson.published_at = "draft", None
        db.commit()
    return lesson_out(lesson, full=True, admin=True)


# ---------- Manbalar va xom yangiliklar ----------

@router.get("/sources")
def sources(db: Session = Depends(get_db)):
    out = []
    for s in db.scalars(select(Source).order_by(Source.topic, Source.name)):
        n = db.scalar(select(func.count()).select_from(RawItem).where(RawItem.source_id == s.id)) or 0
        lessons = db.scalar(
            select(func.count()).select_from(RawItem).where(RawItem.source_id == s.id, RawItem.status == "lesson")
        ) or 0
        out.append({
            "id": s.id, "name": s.name, "url": s.url, "kind": s.kind, "topic": s.topic, "tool": s.tool,
            "active": s.active, "last_checked_at": iso(s.last_checked_at), "last_error": s.last_error,
            "items": n, "lessons": lessons,
        })
    return out


@router.post("/sources")
def add_source(body: SourceIn, db: Session = Depends(get_db)):
    if body.topic not in TOPICS:
        raise HTTPException(400, "Mavzu noto'g'ri")
    if db.scalar(select(Source).where(Source.url == body.url)):
        raise HTTPException(400, "Bu manba allaqachon bor")
    db.add(Source(**body.model_dump()))
    db.commit()
    return {"ok": True}


@router.put("/sources/{source_id}")
def edit_source(source_id: int, body: SourceIn, db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return {"ok": True}


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    s.active = False  # tarix saqlansin
    db.commit()
    return {"ok": True}


@router.post("/sources/seed")
def seed(db: Session = Depends(get_db)):
    return {"added": seed_sources(db)}


@router.get("/raw-items")
def raw_items(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = select(RawItem)
    if status:
        q = q.where(RawItem.status == status)
    rows = db.scalars(q.order_by(RawItem.created_at.desc()).limit(100))
    return [
        {"id": r.id, "title": r.title, "url": r.url, "status": r.status, "note": r.note,
         "source": r.source.name, "published_at": iso(r.published_at), "created_at": iso(r.created_at)}
        for r in rows
    ]


@router.post("/raw-items/{item_id}/retry")
def retry_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(RawItem, item_id)
    if not item:
        raise HTTPException(404)
    item.status, item.note = "new", None
    db.commit()
    return {"ok": True}


# ---------- Ishlar ----------

@router.post("/jobs/collect")
def job_collect():
    def fn(db):
        res = collect_all(db)
        made = process_new_items(db)
        return f"{res['sources']} manba, {res['new_items']} yangi element, {len(made)} dars. Xatolar: {res['errors'] or 'yo`q'}"
    return _run_bg("collect", fn)


@router.post("/jobs/daily")
def job_daily(body: DailyIn):
    return _run_bg("daily", lambda db: service.run_daily(db, force=body.force))


@router.post("/broadcast")
def broadcast(body: BroadcastIn):
    return _run_bg("broadcast", lambda db: service.broadcast(db, body.text))


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    rows = db.scalars(select(JobLog).order_by(JobLog.id.desc()).limit(50))
    return [{"id": r.id, "job": r.job, "ok": r.ok, "message": r.message, "created_at": iso(r.created_at)} for r in rows]


# ---------- Foydalanuvchilar ----------

@router.get("/users")
def users(q: Optional[str] = None, page: int = Query(default=1, ge=1), db: Session = Depends(get_db)):
    query = select(User)
    if q:
        like = f"%{q}%"
        query = query.where((User.name.ilike(like)) | (User.email.ilike(like)) | (User.telegram_username.ilike(like)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(User.id.desc()).offset((page - 1) * 30).limit(30))
    items = []
    for u in rows:
        d = user_out(u)
        d["created_at"] = iso(u.created_at)
        d["last_active_at"] = iso(u.last_active_at)
        d["bot_blocked"] = u.bot_blocked
        d["done"] = db.scalar(select(func.count()).select_from(UserLesson).where(
            UserLesson.user_id == u.id, UserLesson.done_at.is_not(None))) or 0
        items.append(d)
    return {"total": total, "items": items}


class AdminFlag(BaseModel):
    is_admin: bool


@router.patch("/users/{user_id}")
def set_admin(user_id: int, body: AdminFlag, me: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404)
    if u.id == me.id and not body.is_admin:
        raise HTTPException(400, "O'zingizni adminlikdan olib bo'lmaydi")
    u.is_admin = body.is_admin
    db.commit()
    return user_out(u)
