"""O'quv dvigateli: shaxsiy tanlov, progress, XP, darajalar, testlar, takrorlash, yutuqlar."""
import json
import re
import secrets
import unicodedata
from datetime import date, datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .clock import utcnow
from .config import settings
from .models import LEVELS, TOPICS, Lesson, User, UserLesson

TZ = ZoneInfo(settings.timezone)
UTC = ZoneInfo("UTC")
LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
LEVEL_KEYS = list(LEVEL_ORDER)

# XP qoidalari
XP_READ = 5
XP_DONE = 20
XP_QUIZ_CORRECT = 10
XP_REVIEW = 15

RANKS = [
    (0, "Yangi boshlovchi"),
    (100, "Izlanuvchi"),
    (300, "Amaliyotchi"),
    (700, "Mutaxassis"),
    (1500, "Usta"),
    (3000, "AI ustasi"),
]

REVIEW_DAYS = {1: 3, 2: 7}  # bosqich -> necha kundan keyin


# ---------- Vaqt ----------

def now_local() -> datetime:
    return datetime.now(TZ)


def today_local() -> date:
    return now_local().date()


def utc_to_local_date(dt: datetime) -> date:
    """Bazadagi vaqtlar UTC (naive) saqlanadi."""
    return dt.replace(tzinfo=UTC).astimezone(TZ).date()


def local_day_start_utc(day: date) -> datetime:
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    return start.astimezone(UTC).replace(tzinfo=None)


def slugify(text: str) -> str:
    text = re.sub(r"[ʻʼ'‘’`]", "", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return (text[:80].strip("-") or "dars") + "-" + secrets.token_hex(3)


def quiz_of(lesson: Lesson) -> list:
    try:
        data = json.loads(lesson.quiz_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


# ---------- Darslarni tanlash ----------

def published_query():
    return select(Lesson).where(Lesson.status == "published")


def score_lesson(lesson: Lesson, user: User, now: Optional[datetime] = None) -> float:
    """Kunlik tanlov uchun ball: muhimlik + darajaga moslik + yangilik."""
    now = now or utcnow()
    score = float(lesson.importance or 5)
    diff = LEVEL_ORDER.get(lesson.level, 0) - LEVEL_ORDER.get(user.level, 0)
    score += {0: 2, 1: 1, -1: 0, 2: -3, -2: -1}.get(diff, 0)
    if lesson.published_at:
        age = (now - lesson.published_at).total_seconds() / 86400
        score += 3 if age <= 1 else 2 if age <= 3 else 1 if age <= 7 else 0
    return score


def next_lessons_for_user(db: Session, user: User, limit: int) -> List[Lesson]:
    """Foydalanuvchiga hali yuborilmagan, uning mavzularidagi eng mos darslar.
    Mavzular aralash bo'lishi uchun bir mavzudagi har keyingi darsga jarima beriladi."""
    topics = user.topic_list or list(TOPICS)
    sent = select(UserLesson.lesson_id).where(
        and_(UserLesson.user_id == user.id, UserLesson.sent_at.is_not(None))
    )
    candidates = list(
        db.scalars(
            published_query()
            .where(Lesson.topic.in_(topics))
            .where(Lesson.id.not_in(sent))
            .order_by(Lesson.published_at.desc())
            .limit(200)
        )
    )
    now = utcnow()
    scored = {c.id: score_lesson(c, user, now) for c in candidates}
    chosen: List[Lesson] = []
    per_topic: dict = {}
    while candidates and len(chosen) < limit:
        best = max(candidates, key=lambda c: scored[c.id] - 2 * per_topic.get(c.topic, 0))
        chosen.append(best)
        candidates.remove(best)
        per_topic[best.topic] = per_topic.get(best.topic, 0) + 1
    return chosen


def get_user_lesson(db: Session, user: User, lesson: Lesson) -> UserLesson:
    ul = db.scalar(
        select(UserLesson).where(UserLesson.user_id == user.id, UserLesson.lesson_id == lesson.id)
    )
    if not ul:
        ul = UserLesson(user_id=user.id, lesson_id=lesson.id, review_stage=0)
        db.add(ul)
        db.flush()
    return ul


def mark_sent(db: Session, user: User, lessons: List[Lesson]) -> None:
    for lesson in lessons:
        ul = get_user_lesson(db, user, lesson)
        ul.sent_at = ul.sent_at or utcnow()
    db.commit()


# ---------- Progress va XP ----------

def touch(user: User) -> None:
    user.last_active_at = utcnow()


def mark_read(db: Session, user: User, lesson: Lesson) -> UserLesson:
    ul = get_user_lesson(db, user, lesson)
    if not ul.read_at:
        ul.read_at = utcnow()
        user.xp = (user.xp or 0) + XP_READ
    touch(user)
    db.commit()
    return ul


def mark_done(db: Session, user: User, lesson: Lesson, done: bool = True) -> UserLesson:
    ul = get_user_lesson(db, user, lesson)
    if done and not ul.done_at:
        if not ul.read_at:
            ul.read_at = utcnow()
            user.xp = (user.xp or 0) + XP_READ
        ul.done_at = utcnow()
        user.xp = (user.xp or 0) + XP_DONE
        if (ul.review_stage or 0) == 0 and quiz_of(lesson):
            ul.review_stage = 1
            ul.review_due_at = utcnow() + timedelta(days=REVIEW_DAYS[1])
    elif not done and ul.done_at:
        ul.done_at = None
        user.xp = max(0, (user.xp or 0) - XP_DONE)
    touch(user)
    db.commit()
    return ul


def rank_of(xp: int) -> dict:
    current = RANKS[0]
    nxt = None
    for i, (need, name) in enumerate(RANKS):
        if xp >= need:
            current = (need, name)
            nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    return {
        "name": current[1],
        "xp": xp,
        "floor": current[0],
        "next_name": nxt[1] if nxt else None,
        "next_xp": nxt[0] if nxt else None,
    }


# ---------- Test va moslashuvchan daraja ----------

def adapt_level(db: Session, user: User) -> Optional[str]:
    """So'nggi 5 test natijasiga qarab darajani o'zgartiradi. O'zgarsa yangi darajani qaytaradi."""
    rows = list(
        db.scalars(
            select(UserLesson)
            .where(UserLesson.user_id == user.id, UserLesson.quiz_total > 0)
            .order_by(UserLesson.quiz_at.desc())
            .limit(5)
        )
    )
    if len(rows) < 3:
        return None
    ratio = sum(r.quiz_score / r.quiz_total for r in rows) / len(rows)
    idx = LEVEL_ORDER.get(user.level, 0)
    new_idx = idx
    if ratio >= 0.8 and idx < 2:
        new_idx = idx + 1
    elif ratio < 0.4 and idx > 0:
        new_idx = idx - 1
    if new_idx == idx:
        return None
    # Yangi darajada qaytadan statistika yig'ilishi uchun eski natijalar hisobga olinmasin
    user.level = LEVEL_KEYS[new_idx]
    for r in rows:
        r.quiz_total = -abs(r.quiz_total)  # manfiy = arxiv (tarix uchun saqlanadi)
    return user.level


def grade_quiz(db: Session, user: User, lesson: Lesson, answers: List[int]) -> dict:
    quiz = quiz_of(lesson)
    if not quiz:
        return {"score": 0, "total": 0, "results": [], "xp": 0, "level_changed": None}
    results = []
    score = 0
    for i, q in enumerate(quiz):
        given = answers[i] if i < len(answers) else -1
        ok = given == q["answer"]
        score += int(ok)
        results.append({"correct": ok, "answer": q["answer"], "given": given, "explain": q.get("explain", "")})
    ul = get_user_lesson(db, user, lesson)
    xp = 0
    level_changed = None
    if not ul.quiz_at:  # XP faqat birinchi urinish uchun
        xp = score * XP_QUIZ_CORRECT
        user.xp = (user.xp or 0) + xp
        ul.quiz_score, ul.quiz_total, ul.quiz_at = score, len(quiz), utcnow()
        ul.read_at = ul.read_at or utcnow()
        db.flush()
        level_changed = adapt_level(db, user)
    touch(user)
    db.commit()
    return {"score": score, "total": len(quiz), "results": results, "xp": xp, "level_changed": level_changed}


# ---------- Takrorlash (spaced repetition) ----------

def due_reviews(db: Session, user: User, limit: int = 1) -> List[UserLesson]:
    rows = db.scalars(
        select(UserLesson)
        .where(
            UserLesson.user_id == user.id,
            UserLesson.review_stage.in_([1, 2]),
            UserLesson.review_due_at <= utcnow(),
        )
        .order_by(UserLesson.review_due_at)
        .limit(limit)
    )
    return [r for r in rows if quiz_of(r.lesson)]


def review_question_index(ul: UserLesson) -> int:
    """Har bosqichda boshqa savol so'raladi."""
    quiz = quiz_of(ul.lesson)
    return (ul.review_stage or 1) % len(quiz) if quiz else 0


def answer_review(db: Session, user: User, ul: UserLesson, correct: bool) -> dict:
    xp = 0
    if correct:
        xp = XP_REVIEW
        user.xp = (user.xp or 0) + xp
        nxt = (ul.review_stage or 1) + 1
        if nxt in REVIEW_DAYS:
            ul.review_stage = nxt
            ul.review_due_at = utcnow() + timedelta(days=REVIEW_DAYS[nxt])
        else:
            ul.review_stage = 3
            ul.review_due_at = None
    else:
        ul.review_due_at = utcnow() + timedelta(days=1)
    touch(user)
    db.commit()
    return {"xp": xp, "finished": ul.review_stage == 3}


# ---------- Statistika va yutuqlar ----------

def compute_streak(days: set, today: Optional[date] = None) -> int:
    """Ketma-ket faol kunlar. Bugun hali faol bo'lmasa, kechagidan sanaladi."""
    today = today or today_local()
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def best_streak(days: set) -> int:
    best = cur = 0
    prev = None
    for d in sorted(days):
        cur = cur + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, cur)
        prev = d
    return best


def achievements(stats: dict) -> List[dict]:
    perfect = stats.get("perfect_quizzes", 0)
    topics_done = sum(1 for t in stats["by_topic"] if t["done"] > 0)
    defs = [
        ("first", "🌱", "Birinchi qadam", "Birinchi topshiriqni bajaring", stats["done"] >= 1),
        ("ten", "📚", "O'nta dars", "10 ta topshiriqni bajaring", stats["done"] >= 10),
        ("fifty", "🏆", "Ellik dars", "50 ta topshiriqni bajaring", stats["done"] >= 50),
        ("week", "🔥", "Bir hafta", "7 kun ketma-ket o'qing", stats["best_streak"] >= 7),
        ("month", "⚡", "Bir oy", "30 kun ketma-ket o'qing", stats["best_streak"] >= 30),
        ("quiz5", "🎯", "Mergan", "5 ta testni xatosiz yeching", perfect >= 5),
        ("all", "🧭", "Har tomonlama", "Uchala mavzuda topshiriq bajaring", topics_done >= len(TOPICS)),
        ("review", "🧠", "Mustahkam xotira", "10 ta takrorlash savoliga to'g'ri javob bering",
         stats.get("reviews_done", 0) >= 10),
    ]
    return [
        {"key": k, "icon": i, "name": n, "desc": d, "earned": bool(ok)} for k, i, n, d, ok in defs
    ]


def user_stats(db: Session, user: User) -> dict:
    rows = list(db.scalars(select(UserLesson).where(UserLesson.user_id == user.id)))
    ids = [r.lesson_id for r in rows] or [0]
    lesson_topics = dict(db.execute(select(Lesson.id, Lesson.topic).where(Lesson.id.in_(ids))).all())
    active_days = {utc_to_local_date(r.done_at or r.read_at) for r in rows if (r.done_at or r.read_at)}
    totals = dict(
        db.execute(
            select(Lesson.topic, func.count()).where(Lesson.status == "published").group_by(Lesson.topic)
        ).all()
    )
    by_topic = []
    for key, name in TOPICS.items():
        done = sum(1 for r in rows if r.done_at and lesson_topics.get(r.lesson_id) == key)
        by_topic.append({"key": key, "name": name, "done": done, "total": totals.get(key, 0)})

    today = today_local()
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cnt = sum(1 for r in rows if r.done_at and utc_to_local_date(r.done_at) == d)
        rd = sum(1 for r in rows if r.read_at and utc_to_local_date(r.read_at) == d)
        week.append({"day": d.isoformat(), "done": cnt, "read": rd})

    quizzes = [r for r in rows if r.quiz_total]
    stats = {
        "read": sum(1 for r in rows if r.read_at),
        "done": sum(1 for r in rows if r.done_at),
        "received": sum(1 for r in rows if r.sent_at),
        "streak": compute_streak(active_days),
        "best_streak": best_streak(active_days),
        "quizzes": len(quizzes),
        "quiz_accuracy": round(
            100 * sum(r.quiz_score or 0 for r in quizzes) / max(1, sum(abs(r.quiz_total) for r in quizzes))
        ),
        "perfect_quizzes": sum(1 for r in quizzes if r.quiz_score == abs(r.quiz_total)),
        "reviews_done": sum(max(0, (r.review_stage or 0) - 1) for r in rows),
        "reviews_due": sum(
            1 for r in rows if r.review_stage in (1, 2) and r.review_due_at and r.review_due_at <= utcnow()
        ),
        "by_topic": by_topic,
        "week": week,
        "level": user.level,
        "level_name": LEVELS.get(user.level, ""),
        "rank": rank_of(user.xp or 0),
    }
    stats["achievements"] = achievements(stats)
    return stats


def leaderboard(db: Session, limit: int = 10) -> List[dict]:
    users = db.scalars(
        select(User).where(User.email.is_not(None), User.xp > 0).order_by(User.xp.desc()).limit(limit)
    )
    out = []
    for i, u in enumerate(users, 1):
        first = (u.name or "Foydalanuvchi").split()[0]
        out.append({"place": i, "name": first, "xp": u.xp, "rank": rank_of(u.xp)["name"], "id": u.id})
    return out
