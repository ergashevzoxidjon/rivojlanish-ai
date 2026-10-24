"""Platformaning asosiy oqimlari uchun testlar (AI va Telegram soxtalashtirilgan)."""
import hashlib
import hmac
import json
import time
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

import pytest
from sqlalchemy import select

from app import ai_writer, auth, collector, lessons
from app.bot import handlers, service
from app.clock import utcnow
from app.db import session_scope
from app.models import (
    DailyRun,
    Lesson,
    LinkToken,
    RawItem,
    Source,
    TutorMessage,
    User,
    UserLesson,
)

QUIZ = [
    {"q": "1-savol", "options": ["a", "b", "c"], "answer": 1, "explain": "chunki b"},
    {"q": "2-savol", "options": ["a", "b"], "answer": 0, "explain": ""},
    {"q": "3-savol", "options": ["a", "b", "c", "d"], "answer": 3, "explain": ""},
]


def fake_lesson(title="Claude Projects bilan ishlash", topic="chat", **kw):
    data = {
        "title": title,
        "tool": "Claude",
        "level": "beginner",
        "minutes": 7,
        "importance": 7,
        "summary": "Qisqacha.",
        "body_md": "## Qadam-baqadam\n1. Bir\n2. Ikki",
        "task_md": "Bitta loyiha yarating.",
        "quiz": QUIZ,
        "topic": topic,
    }
    data.update(kw)
    return data


def make_lesson(db, title="Dars", topic="chat", level="beginner", importance=5, days_ago=0, quiz=True):
    lesson = Lesson(
        slug=lessons.slugify(title),
        title=title,
        topic=topic,
        tool="Claude",
        level=level,
        importance=importance,
        summary="s",
        body_md="b",
        task_md="t",
        quiz_json=json.dumps(QUIZ if quiz else []),
        status="published",
        published_at=utcnow() - timedelta(days=days_ago),
    )
    db.add(lesson)
    db.commit()
    return lesson


def make_user(db, email="u@example.com", tg=1001, name="Ali Valiyev"):
    user = User(email=email, telegram_id=tg, name=name)
    db.add(user)
    db.commit()
    return user


def texts(calls):
    return [p.get("text", "") for m, p in calls if m in ("sendMessage", "editMessageText")]


def tg_update(text, tg_id=1001, first_name="Ali"):
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": tg_id, "type": "private"},
            "from": {"id": tg_id, "first_name": first_name, "username": "ali"},
            "text": text,
        },
    }


def tg_callback(data, tg_id=1001):
    return {
        "update_id": 2,
        "callback_query": {
            "id": "cb1",
            "from": {"id": tg_id, "first_name": "Ali"},
            "data": data,
            "message": {"message_id": 55, "chat": {"id": tg_id, "type": "private"}},
        },
    }


def auth_header(user):
    return {"Authorization": f"Bearer {auth.create_token(user)}"}


# ---------- Telegram Web App initData ----------

def signed_init_data(user: dict, token="123456:TEST-TOKEN", auth_date=None):
    pairs = {"auth_date": str(auth_date or int(time.time())), "query_id": "AAA", "user": json.dumps(user)}
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


def test_telegram_init_data_valid_and_tampered():
    data = signed_init_data({"id": 42, "first_name": "Ali"})
    assert auth.verify_telegram_init_data(data)["id"] == 42
    with pytest.raises(Exception):
        auth.verify_telegram_init_data(data.replace("Ali", "Vali"))
    with pytest.raises(Exception):
        auth.verify_telegram_init_data(signed_init_data({"id": 1}, token="boshqa:token"))
    with pytest.raises(Exception):
        auth.verify_telegram_init_data(signed_init_data({"id": 1}, auth_date=int(time.time()) - 200000))


def test_webapp_login_api(client):
    r = client.post("/api/auth/telegram", json={"init_data": signed_init_data({"id": 77, "first_name": "Ali"})})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["telegram_id"] == 77 and body["user"]["registered"] is False
    # Ro'yxatdan o'tmagan foydalanuvchi darslar bilan ishlay olmaydi
    r2 = client.get("/api/today", headers={"Authorization": f"Bearer {body['token']}"})
    assert r2.status_code == 403 and r2.json()["detail"] == "not_registered"


# ---------- Ro'yxatdan o'tish oqimi ----------

def test_bot_registration_flow(sent, client, monkeypatch):
    handlers.handle_update(tg_update("/start"))
    assert "ro'yxatdan" in texts(sent)[-1]
    markup = sent[-1][1]["reply_markup"]
    url = markup["inline_keyboard"][0][0]["url"]
    token = url.split("t=")[1]

    # Ro'yxatdan o'tmasdan dars so'rasa — yana ro'yxatga yuboradi
    handlers.handle_update(tg_update("📚 Yana dars yuborish"))
    assert "ro'yxatdan" in texts(sent)[-1]

    monkeypatch.setattr(
        auth, "verify_google_credential",
        lambda c: {"email": "Ali@Example.com", "sub": "g1", "name": "Ali V", "email_verified": True},
    )
    from app.api import users as users_api
    monkeypatch.setattr(users_api, "verify_google_credential", auth.verify_google_credential)
    r = client.post("/api/auth/google", json={"credential": "x", "link_token": token})
    assert r.status_code == 200
    u = r.json()["user"]
    assert u["email"] == "ali@example.com" and u["telegram_id"] == 1001 and u["registered"]

    with session_scope() as db:
        assert db.scalar(select(LinkToken).where(LinkToken.token == token)).used
        assert len(db.scalars(select(User)).all()) == 1

    handlers.handle_update(tg_update("/start"))
    assert "Xush kelibsiz" in texts(sent)[-1]


def test_merge_keeps_progress():
    with session_scope() as db:
        l1 = make_lesson(db, "A")
        l2 = make_lesson(db, "B")
        web = User(email="w@example.com", name="W", xp=10)
        tg = User(telegram_id=5, name="T", xp=25)
        db.add_all([web, tg])
        db.flush()
        db.add_all([
            UserLesson(user_id=web.id, lesson_id=l1.id, read_at=utcnow()),
            UserLesson(user_id=tg.id, lesson_id=l1.id, done_at=utcnow()),
            UserLesson(user_id=tg.id, lesson_id=l2.id, sent_at=utcnow()),
            TutorMessage(user_id=tg.id, role="user", content="salom"),
        ])
        db.commit()
        auth.merge_users(db, web, tg)
        db.commit()
        rows = {r.lesson_id: r for r in db.scalars(select(UserLesson).where(UserLesson.user_id == web.id))}
        assert rows[l1.id].read_at and rows[l1.id].done_at and rows[l2.id].sent_at
        assert web.telegram_id == 5 and web.xp == 35
        assert db.scalar(select(TutorMessage)).user_id == web.id
        assert len(db.scalars(select(User)).all()) == 1


# ---------- Kontent: yig'ish va AI ----------

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>r</title>
<entry><id>tag:1</id><title>v2.0 Yangi funksiya</title><link href="https://x.test/1"/>
<updated>{new}</updated><content type="html">&lt;p&gt;Yangi &lt;b&gt;agent&lt;/b&gt; rejimi&lt;/p&gt;</content></entry>
<entry><id>tag:2</id><title>v1.0 eski</title><link href="https://x.test/2"/>
<updated>2020-01-01T00:00:00Z</updated><content>eski</content></entry>
</feed>"""


def test_collect_and_process(monkeypatch):
    now = utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    monkeypatch.setattr(collector, "_fetch", lambda url: ATOM.format(new=now))
    seen_titles = []

    def fake_ai(title, content, url, topic, tool, recent):
        seen_titles.append(recent)
        assert "agent" in content
        return {"worth": True, "lesson": dict(fake_lesson(topic=topic), source_url=url)}

    monkeypatch.setattr(ai_writer, "lesson_from_news", fake_ai)
    with session_scope() as db:
        db.add(Source(name="Test", url="https://x.test/feed", kind="rss", topic="coding", tool="Claude Code"))
        db.commit()
        res = collector.collect_all(db)
        assert res["new_items"] == 2 and not res["errors"]
        statuses = {i.title: i.status for i in db.scalars(select(RawItem))}
        assert statuses["v1.0 eski"] == "skipped"  # birinchi yig'ishda eski tarix olinmaydi
        made = collector.process_new_items(db)
        assert len(made) == 1
        lesson = made[0]
        assert lesson.status == "published" and lesson.topic == "coding" and lesson.importance == 7
        assert len(lessons.quiz_of(lesson)) == 3
        # Takroriy yig'ish yangi element qo'shmaydi
        assert collector.collect_all(db)["new_items"] == 0


def test_html_source_diff(monkeypatch):
    pages = iter(["<p>Birinchi eski yangilik sarlavhasi bor</p>",
                  "<p>Birinchi eski yangilik sarlavhasi bor</p><p>Ikkinchi butunlay yangi funksiya chiqdi</p>"])
    monkeypatch.setattr(collector, "_fetch", lambda url: next(pages))
    with session_scope() as db:
        db.add(Source(name="Sahifa", url="https://x.test/news", kind="html", topic="chat", tool="Claude"))
        db.commit()
        assert collector.collect_all(db)["new_items"] == 0
        assert collector.collect_all(db)["new_items"] == 1
        item = db.scalar(select(RawItem))
        assert "Ikkinchi" in item.content and "Birinchi" not in item.content


def test_ai_parsing_and_cleaning():
    assert ai_writer.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ai_writer.parse_json('Mana: {"worth": false} tamom') == {"worth": False}
    assert ai_writer.parse_json("json emas") is None
    quiz = ai_writer.clean_quiz([
        {"q": "ok", "options": ["a", "b"], "answer": 1},
        {"q": "yomon javob", "options": ["a", "b"], "answer": 5},
        {"q": "", "options": ["a", "b"], "answer": 0},
    ])
    assert len(quiz) == 1
    cleaned = ai_writer.clean_lesson(fake_lesson(level="xato", importance=99), "chat")
    assert cleaned["level"] == "beginner" and cleaned["importance"] == 10
    assert ai_writer.clean_lesson({"title": "x"}, "chat") is None


# ---------- Tanlov, ertalabki yuborish ----------

def test_ranking_prefers_important_fresh_and_mixes_topics():
    with session_scope() as db:
        user = make_user(db)
        old = make_lesson(db, "Eski muhim", importance=9, days_ago=20)
        fresh = make_lesson(db, "Yangi muhim", importance=9, days_ago=0)
        weak = make_lesson(db, "Ahamiyatsiz", importance=2, days_ago=0)
        other = make_lesson(db, "Kod darsi", topic="coding", importance=7, days_ago=1)
        hard = make_lesson(db, "Juda qiyin", level="advanced", importance=9, days_ago=0)
        picks = lessons.next_lessons_for_user(db, user, 3)
        titles = [p.title for p in picks]
        assert titles[0] == "Yangi muhim"
        assert "Kod darsi" in titles  # mavzular aralashadi
        assert "Ahamiyatsiz" not in titles and "Juda qiyin" not in titles
        lessons.mark_sent(db, user, picks)
        rest = lessons.next_lessons_for_user(db, user, 10)
        assert not set(p.id for p in picks) & set(p.id for p in rest)
        assert {old.id, weak.id, hard.id} <= {p.id for p in rest} | {p.id for p in picks}
        _ = fresh, other


def test_daily_runs_once_after_8(sent, monkeypatch):
    with session_scope() as db:
        user = make_user(db)
        user.daily_count = 2
        db.commit()
        for i in range(4):
            make_lesson(db, f"Dars {i}", importance=5 + i)

        monkeypatch.setattr(service, "now_local", lambda: datetime(2026, 10, 25, 7, 30, tzinfo=lessons.TZ))
        assert service.run_daily(db)["status"] == "early"

        monkeypatch.setattr(service, "now_local", lambda: datetime(2026, 10, 25, 8, 5, tzinfo=lessons.TZ))
        res = service.run_daily(db)
        assert res == {"status": "sent", "users": 1, "lessons": 2}
        assert service.run_daily(db)["status"] == "already"
        assert db.scalar(select(DailyRun)).day == date(2026, 10, 25)
        all_text = "\n".join(texts(sent))
        assert "Xayrli tong" in all_text and "Yana dars yuborish" in all_text
        sent_rows = db.scalars(select(UserLesson).where(UserLesson.sent_at.is_not(None))).all()
        assert len(sent_rows) == 2


def test_daily_skips_unregistered_and_blocked(sent, monkeypatch):
    with session_scope() as db:
        db.add(User(telegram_id=1, name="ro'yxatsiz"))
        blocked = make_user(db, "b@example.com", 2)
        blocked.bot_blocked = True
        db.commit()
        make_lesson(db)
        monkeypatch.setattr(service, "now_local", lambda: datetime(2026, 10, 25, 9, 0, tzinfo=lessons.TZ))
        assert service.run_daily(db)["users"] == 0


# ---------- "Yana dars" ----------

def test_more_sends_ready_then_generates(sent, monkeypatch):
    with session_scope() as db:
        make_user(db)
        make_lesson(db, "Tayyor dars")

    handlers.handle_update(tg_update("📚 Yana dars yuborish"))
    assert any("Tayyor dars" in t for t in texts(sent))

    made = []

    def fake_on_demand(topic, titles, level):
        made.append(topic)
        return fake_lesson(title=f"Yangi {topic} {len(made)}", topic=topic)

    monkeypatch.setattr(ai_writer, "lesson_on_demand", fake_on_demand)
    sent.clear()
    handlers.handle_update(tg_update("/dars"))
    assert len(made) == 3
    out = "\n".join(texts(sent))
    assert "yozilmoqda" in out and "Yangi" in out
    with session_scope() as db:
        assert db.scalar(select(Lesson).where(Lesson.origin == "on_demand")).requested_by is not None


def test_more_respects_daily_limit(sent, monkeypatch):
    monkeypatch.setattr(service.settings, "on_demand_daily_limit", 2)
    monkeypatch.setattr(ai_writer, "lesson_on_demand", lambda t, ti, l: fake_lesson(title=f"x {len(ti)}", topic=t))
    with session_scope() as db:
        make_user(db)
    handlers.handle_update(tg_update("/dars"))
    handlers.handle_update(tg_update("/dars"))  # 2 tasi yuborilgan, yangilari yo'q -> limit
    assert "qo'shimcha dars oldingiz" in texts(sent)[-1]


# ---------- Test, XP, daraja, takrorlash ----------

def test_bot_quiz_flow_and_xp(sent):
    with session_scope() as db:
        make_user(db)
        lesson = make_lesson(db, "Test darsi")
        lid = lesson.id
    handlers.handle_update(tg_callback(f"qz:{lid}:"))
    assert "Savol 1 / 3" in texts(sent)[-1]
    handlers.handle_update(tg_callback(f"qz:{lid}:1"))
    assert "To'g'ri" in texts(sent)[-1] and "Savol 2 / 3" in texts(sent)[-1]
    handlers.handle_update(tg_callback(f"qz:{lid}:11"))
    assert "Noto'g'ri" in texts(sent)[-1]
    handlers.handle_update(tg_callback(f"qz:{lid}:113"))
    assert "2 / 3" in texts(sent)[-1] and "+20 XP" in texts(sent)[-1]
    # Noto'g'ri formatdagi callback
    handlers.handle_update(tg_callback(f"qz:{lid}:11111"))
    with session_scope() as db:
        user = db.scalar(select(User))
        assert user.xp == 20
        ul = db.scalar(select(UserLesson))
        assert ul.quiz_score == 2 and ul.quiz_total == 3


def test_adaptive_level_up():
    with session_scope() as db:
        user = make_user(db)
        for i in range(3):
            lesson = make_lesson(db, f"L{i}")
            res = lessons.grade_quiz(db, user, lesson, [1, 0, 3])
            assert res["score"] == 3
        assert res["level_changed"] == "intermediate" and user.level == "intermediate"
        # Qayta yechish XP bermaydi
        again = lessons.grade_quiz(db, user, lesson, [1, 0, 3])
        assert again["xp"] == 0
        stats = lessons.user_stats(db, user)
        assert stats["quizzes"] == 3 and stats["quiz_accuracy"] == 100 and stats["perfect_quizzes"] == 3


def test_done_schedules_review_and_review_flow(sent):
    with session_scope() as db:
        user = make_user(db)
        lesson = make_lesson(db)
        handlers.handle_update(tg_callback(f"done:{lesson.id}"))
        db.expire_all()
        ul = db.scalar(select(UserLesson))
        assert ul.done_at and ul.review_stage == 1
        assert ul.review_due_at > utcnow() + timedelta(days=2)
        ul.review_due_at = utcnow() - timedelta(minutes=1)
        db.commit()
        assert lessons.due_reviews(db, user)
        qi = lessons.review_question_index(ul)
        correct = QUIZ[qi]["answer"]
        ul_id = ul.id

    handlers.handle_update(tg_callback(f"rv:{ul_id}:{qi}:{correct}"))
    assert "To'g'ri" in texts(sent)[-1]
    with session_scope() as db:
        ul = db.get(UserLesson, ul_id)
        assert ul.review_stage == 2 and ul.review_due_at > utcnow() + timedelta(days=6)
        assert db.scalar(select(User)).xp == 5 + 20 + 15


def test_streak():
    t = date(2026, 10, 25)
    days = {t, t - timedelta(days=1), t - timedelta(days=2), t - timedelta(days=5)}
    assert lessons.compute_streak(days, t) == 3
    assert lessons.compute_streak(days - {t}, t) == 2  # bugun hali o'qimagan
    assert lessons.best_streak(days) == 3


# ---------- AI ustoz ----------

def test_tutor_via_bot_with_lesson_context(sent, monkeypatch):
    captured = {}

    def fake_tutor(question, history, lesson):
        captured.update(question=question, history=history, lesson=lesson)
        return "**Javob:** `kod` bilan"

    monkeypatch.setattr(ai_writer, "tutor_answer", fake_tutor)
    with session_scope() as db:
        make_user(db)
        lid = make_lesson(db, "Ustoz darsi").id
    handlers.handle_update(tg_callback(f"ask:{lid}"))
    handlers.handle_update(tg_update("Bu qanday ishlaydi?"))
    assert captured["lesson"]["title"] == "Ustoz darsi"
    assert "<b>Javob:</b> <code>kod</code>" in texts(sent)[-1]
    handlers.handle_update(tg_update("Yana savol"))
    assert len(captured["history"]) == 2
    handlers.handle_update(tg_update("/yangi"))
    handlers.handle_update(tg_update("Umumiy savol"))
    assert captured["lesson"] is None


def test_tutor_limit(client, monkeypatch):
    monkeypatch.setattr(ai_writer, "tutor_answer", lambda q, h, l: "javob")
    from app import tutor
    monkeypatch.setattr(tutor.settings, "tutor_daily_limit", 2)
    with session_scope() as db:
        user = make_user(db)
    h = auth_header(user)
    assert client.post("/api/tutor", json={"question": "1"}, headers=h).json()["left"] == 1
    assert client.post("/api/tutor", json={"question": "2"}, headers=h).status_code == 200
    assert client.post("/api/tutor", json={"question": "3"}, headers=h).status_code == 429
    assert len(client.get("/api/tutor", headers=h).json()) == 4


# ---------- API ----------

def test_lesson_api_hides_answers_until_quiz(client):
    with session_scope() as db:
        user = make_user(db)
        lesson = make_lesson(db, "API darsi")
        make_lesson(db, "Qo'shni dars")
        draft = Lesson(slug="qoralama", title="Q", topic="chat", status="draft")
        db.add(draft)
        db.commit()
    h = auth_header(user)
    d = client.get(f"/api/lessons/{lesson.slug}", headers=h).json()
    assert "answer" not in d["quiz"][0] and len(d["related"]) == 1
    assert client.get("/api/lessons/qoralama", headers=h).status_code == 404
    r = client.post(f"/api/lessons/{lesson.id}/quiz", json={"answers": [1, 0, 0]}, headers=h).json()
    assert r["score"] == 2 and r["results"][2]["correct"] is False
    d = client.get(f"/api/lessons/{lesson.slug}", headers=h).json()
    assert d["quiz"][0]["answer"] == 1 and d["progress"]["quiz_score"] == 2
    assert client.post(f"/api/lessons/{lesson.id}/done", json={"done": True}, headers=h).status_code == 200
    lst = client.get("/api/lessons?state=done", headers=h).json()
    assert lst["total"] == 1 and lst["items"][0]["progress"]["done"]
    assert client.get("/api/lessons?q=Qo'shni").json()["total"] == 1
    stats = client.get("/api/me/stats", headers=h).json()
    assert stats["done"] == 1 and stats["achievements"][0]["earned"]
    today = client.get("/api/today", headers=h).json()
    assert len(today["lessons"]) >= 1 and today["from_daily"] is False


def test_admin_requires_admin_and_works(client, monkeypatch):
    with session_scope() as db:
        user = make_user(db)
        admin = make_user(db, "admin@example.com", 2002, "Admin")
        admin.is_admin = True
        db.commit()
        lesson = make_lesson(db)
    assert client.get("/api/admin/overview", headers=auth_header(user)).status_code == 403
    assert client.get("/api/admin/overview").status_code == 401
    h = auth_header(admin)
    ov = client.get("/api/admin/overview", headers=h).json()
    assert ov["users"] == 2 and ov["lessons"]["published"] == 1 and len(ov["daily"]) == 14
    full = client.get(f"/api/admin/lessons/{lesson.id}", headers=h).json()
    assert full["quiz"][0]["answer"] == 1
    full["title"] = "Tahrirlangan"
    full["quiz"] = full["quiz"][:1]
    assert client.put(f"/api/admin/lessons/{lesson.id}", json=full, headers=h).json()["title"] == "Tahrirlangan"
    assert client.post(f"/api/admin/lessons/{lesson.id}/reject", headers=h).json()["status"] == "rejected"
    # Standart manbalar ilova ishga tushganda avtomatik qo'shiladi
    assert client.post("/api/admin/sources/seed", headers=h).json()["added"] == 0
    assert len(client.get("/api/admin/sources", headers=h).json()) == len(collector.DEFAULT_SOURCES)
    assert client.patch(f"/api/admin/users/{admin.id}", json={"is_admin": False}, headers=h).status_code == 400


def test_admin_email_gets_admin_on_google_login(client, monkeypatch):
    from app.api import users as users_api
    monkeypatch.setattr(users_api, "verify_google_credential",
                        lambda c: {"email": "admin@example.com", "sub": "s", "name": "A", "email_verified": True})
    r = client.post("/api/auth/google", json={"credential": "x"})
    assert r.json()["user"]["is_admin"] is True


def test_webhook_secret_and_cron_key(client, sent):
    r = client.post("/api/telegram/webhook", json=tg_update("/start"))
    assert r.status_code == 403
    r = client.post("/api/telegram/webhook", json=tg_update("/start"),
                    headers={"X-Telegram-Bot-Api-Secret-Token": "whsecret"})
    assert r.status_code == 200 and "ro'yxatdan" in texts(sent)[-1]
    assert client.get("/api/cron/daily?key=wrong").status_code == 403


def test_settings_callbacks(sent):
    with session_scope() as db:
        make_user(db)
    handlers.handle_update(tg_callback("topic:chat"))
    handlers.handle_update(tg_callback("count:1"))
    handlers.handle_update(tg_callback("count:9"))
    handlers.handle_update(tg_callback("notify"))
    with session_scope() as db:
        user = db.scalar(select(User))
        assert user.topic_list == ["coding", "automation"] and user.daily_count == 1 and not user.notify
    handlers.handle_update(tg_callback("topic:coding"))
    handlers.handle_update(tg_callback("topic:automation"))  # oxirgisini olib bo'lmaydi
    with session_scope() as db:
        assert db.scalar(select(User)).topic_list == ["automation"]


def test_secret_autogenerated_and_webhook_derived(tmp_path, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    s1 = config.Settings(secret_key="", telegram_webhook_secret="", database_url="sqlite://")
    s2 = config.Settings(secret_key="", telegram_webhook_secret="", database_url="sqlite://")
    assert len(s1.secret_key) == 64 and s1.secret_key == s2.secret_key  # faylda saqlanadi
    assert (tmp_path / "secret.key").read_text() == s1.secret_key
    assert s1.telegram_webhook_secret == s2.telegram_webhook_secret and len(s1.telegram_webhook_secret) == 48


def test_md_to_html_escapes():
    from app.bot.messages import md_to_html
    out = md_to_html("<script> **qalin**\n```py\nprint('<a>')\n```\n- band")
    assert "&lt;script&gt;" in out and "<b>qalin</b>" in out and "<pre>print(&#x27;&lt;a&gt;&#x27;)</pre>" in out
    assert "• band" in out


def test_web_more_endpoint(client, monkeypatch):
    with session_scope() as db:
        user = make_user(db)
        make_lesson(db, "Bitta tayyor")
    h = auth_header(user)
    r = client.post("/api/more", headers=h).json()
    assert r["generated"] is False and r["lessons"][0]["title"] == "Bitta tayyor"
    monkeypatch.setattr(ai_writer, "lesson_on_demand", lambda t, ti, lv: fake_lesson(title="AI yozdi", topic=t))
    r = client.post("/api/more", headers=h).json()
    assert r["generated"] is True and r["lessons"][0]["title"] == "AI yozdi"
