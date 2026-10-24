"""Telegram update'larini qayta ishlash (webhook orqali keladi)."""
import logging
import secrets
from datetime import timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import bg, tutor
from ..auth import get_or_create_telegram_user, merge_users
from ..clock import utcnow
from ..config import settings
from ..db import session_scope
from ..lessons import (
    answer_review,
    grade_quiz,
    leaderboard,
    mark_done,
    quiz_of,
    touch,
    user_stats,
)
from ..models import LEVELS, TOPICS, Lesson, LinkToken, User, UserLesson
from . import messages as m
from .service import request_more
from .telegram import (
    TelegramError,
    answer_callback,
    call,
    edit_markup,
    edit_text,
    send_message,
)

log = logging.getLogger(__name__)


def handle_update(update: dict) -> None:
    try:
        with session_scope() as db:
            if "message" in update:
                handle_message(db, update["message"])
            elif "callback_query" in update:
                handle_callback(db, update["callback_query"])
    except Exception:
        log.exception("Update xatosi")


# ---------- Yordamchilar ----------

def new_link_token(db: Session, telegram_id: int) -> str:
    token = secrets.token_urlsafe(24)
    db.add(LinkToken(token=token, telegram_id=telegram_id, expires_at=utcnow() + timedelta(days=2)))
    db.commit()
    return token


def ask_registration(db: Session, user: User, chat_id: int) -> None:
    send_message(chat_id, m.welcome_unregistered(user.name), m.register_keyboard(new_link_token(db, user.telegram_id)))


def link_from_web(db: Session, tg_user: User, token: str, chat_id: int) -> User:
    """Web'dagi akkauntga shu Telegramni ulaydi (havola: t.me/bot?start=k_<token>)."""
    link = db.scalar(select(LinkToken).where(LinkToken.token == token))
    if not link or link.used or link.expires_at < utcnow() or not link.user_id:
        send_message(chat_id, "⚠️ Havola eskirgan. Saytdagi profil sahifasidan yangi havola oling.")
        return tg_user
    web_user = db.get(User, link.user_id)
    if not web_user or web_user.id == tg_user.id:
        return tg_user
    if tg_user.is_registered:
        send_message(chat_id, "⚠️ Bu Telegram akkaunt boshqa email bilan ro'yxatdan o'tgan.")
        return tg_user
    if web_user.telegram_id and web_user.telegram_id != tg_user.telegram_id:
        send_message(chat_id, "⚠️ Bu web akkauntga boshqa Telegram ulangan.")
        return tg_user
    merge_users(db, web_user, tg_user)
    link.used = True
    db.commit()
    send_message(chat_id, "🔗 Telegram akkauntingiz platformaga ulandi!")
    return web_user


def send_long(chat_id: int, html_text: str, plain: str, markup: Optional[dict] = None) -> None:
    chunks = m.split_text(html_text)
    try:
        for i, chunk in enumerate(chunks):
            send_message(chat_id, chunk, markup if i == len(chunks) - 1 else None)
    except TelegramError:
        # HTML bo'lib qolgan bo'lsa oddiy matn sifatida yuboramiz
        for i, chunk in enumerate(m.split_text(plain)):
            call("sendMessage", chat_id=chat_id, text=chunk,
                 reply_markup=markup if i == len(chunks) - 1 else None)


# ---------- Xabarlar ----------

def handle_message(db: Session, msg: dict) -> None:
    chat = msg.get("chat", {})
    if chat.get("type") != "private" or "from" not in msg:
        return
    chat_id = chat["id"]
    user = get_or_create_telegram_user(db, msg["from"])
    if user.bot_blocked:
        user.bot_blocked = False
    touch(user)
    db.commit()
    text = (msg.get("text") or "").strip()

    if text.startswith("/start"):
        payload = text.split(" ", 1)[1] if " " in text else ""
        if payload.startswith("k_"):
            user = link_from_web(db, user, payload[2:], chat_id)
        if user.is_registered:
            send_message(chat_id, m.welcome_registered(user), m.main_keyboard())
            if payload.startswith("l_"):
                lesson = db.get(Lesson, int(payload[2:])) if payload[2:].isdigit() else None
                if lesson and lesson.status == "published":
                    send_message(chat_id, m.lesson_text(lesson), m.lesson_keyboard(lesson))
        else:
            ask_registration(db, user, chat_id)
        return

    if text in ("/help", "/yordam"):
        send_message(chat_id, m.HELP, m.main_keyboard() if user.is_registered else None)
        return

    if not user.is_registered:
        ask_registration(db, user, chat_id)
        return

    if text in (m.BTN_MORE, "/dars", "/more"):
        more(db, user, chat_id)
    elif text in (m.BTN_PROGRESS, "/progress"):
        send_message(chat_id, m.progress_text(user_stats(db, user)), m.main_keyboard())
    elif text in (m.BTN_SETTINGS, "/sozlamalar", "/settings"):
        send_message(chat_id, m.settings_text(user), m.settings_keyboard(user))
    elif text in ("/reyting", "/top"):
        send_message(chat_id, leaderboard_text(db, user))
    elif text in ("/yangi", "/new"):
        user.tutor_lesson_id = None
        db.commit()
        tutor.clear(db, user, None)
        send_message(chat_id, "🧹 Ustoz bilan suhbat tozalandi. Yangi savolingizni yozing.")
    elif text.startswith("/"):
        send_message(chat_id, m.HELP, m.main_keyboard())
    elif text:
        ask_tutor_async(user.id, chat_id, text)
    else:
        send_message(chat_id, "Hozircha faqat matnli savollarni tushunaman 🙂")


def leaderboard_text(db: Session, user: User) -> str:
    rows = leaderboard(db, 10)
    if not rows:
        return "🏆 Reyting hali bo'sh — birinchi bo'ling!"
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 <b>Eng faol o'quvchilar</b>\n"]
    for r in rows:
        me = " ← siz" if r["id"] == user.id else ""
        lines.append(f"{medals.get(r['place'], str(r['place']) + '.')} {m.e(r['name'])} — {r['xp']} XP{me}")
    return "\n".join(lines)


def more(db: Session, user: User, chat_id: int) -> None:
    result = request_more(db, user)
    if result == "generating":
        send_message(
            chat_id,
            "⏳ Barcha tayyor darslarni olgansiz. Siz uchun yangi darslar yozilmoqda — "
            "1–2 daqiqada yuboraman.",
        )
    elif result == "busy":
        send_message(chat_id, "⏳ Darslar tayyorlanmoqda, biroz kuting...")
    elif result == "limit":
        send_message(
            chat_id,
            f"📚 Bugun {settings.on_demand_daily_limit} ta qo'shimcha dars oldingiz — zo'r natija! "
            "Ertaga yana davom etamiz. Hozir esa o'tilgan darslarni takrorlab, test yechib ko'ring.",
        )


def ask_tutor_async(user_id: int, chat_id: int, question: str) -> None:
    """AI javobi bir necha soniya olishi mumkin — webhookni ushlab turmaslik uchun fon oqimida."""
    try:
        call("sendChatAction", chat_id=chat_id, action="typing")
    except Exception:
        pass

    def work():
        with session_scope() as db:
            user = db.get(User, user_id)
            lesson = db.get(Lesson, user.tutor_lesson_id) if user.tutor_lesson_id else None
            try:
                answer = tutor.ask(db, user, question, lesson)
            except tutor.TutorLimit as e:
                send_message(chat_id, f"⏸ {m.e(str(e))}")
                return
            except Exception:
                log.exception("Ustoz xatosi")
                send_message(chat_id, "😔 Hozir javob bera olmadim. Birozdan keyin qayta so'rang.")
                return
            prefix = f"🎓 <i>{m.e(lesson.title)}</i>\n\n" if lesson else "🎓 "
            send_long(chat_id, prefix + m.md_to_html(answer), answer)

    bg.run_bg(work)


# ---------- Tugmalar ----------

def handle_callback(db: Session, cq: dict) -> None:
    data = cq.get("data", "")
    msg = cq.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    message_id = msg.get("message_id")
    user = get_or_create_telegram_user(db, cq["from"])
    touch(user)
    db.commit()

    if not user.is_registered:
        answer_callback(cq["id"], "Avval ro'yxatdan o'ting", alert=True)
        ask_registration(db, user, chat_id)
        return

    kind, _, rest = data.partition(":")

    if kind in ("done", "undo"):
        lesson = db.get(Lesson, int(rest)) if rest.isdigit() else None
        if not lesson:
            return answer_callback(cq["id"], "Dars topilmadi")
        mark_done(db, user, lesson, kind == "done")
        answer_callback(cq["id"], "Barakalla! +XP 🎉" if kind == "done" else "Belgi olib tashlandi")
        edit_markup(chat_id, message_id, m.lesson_keyboard(lesson, done=kind == "done"))

    elif kind == "more":
        answer_callback(cq["id"])
        more(db, user, chat_id)

    elif kind == "qz":
        handle_quiz(db, user, cq, chat_id, message_id, rest)

    elif kind == "rv":
        handle_review(db, user, cq, chat_id, message_id, rest)

    elif kind == "ask":
        lesson = db.get(Lesson, int(rest)) if rest.isdigit() else None
        if not lesson:
            return answer_callback(cq["id"], "Dars topilmadi")
        user.tutor_lesson_id = lesson.id
        db.commit()
        answer_callback(cq["id"])
        send_message(
            chat_id,
            f"🎓 <b>{m.e(lesson.title)}</b> darsi bo'yicha savolingizni yozing.\n"
            "<i>Umumiy savollarga qaytish uchun /yangi</i>",
        )

    elif kind == "topic":
        topics = user.topic_list
        if rest in topics:
            if len(topics) == 1:
                return answer_callback(cq["id"], "Kamida bitta mavzu bo'lishi kerak", alert=True)
            topics.remove(rest)
        elif rest in TOPICS:
            topics.append(rest)
        user.topics = ",".join(t for t in TOPICS if t in topics)
        db.commit()
        answer_callback(cq["id"], "Saqlandi")
        edit_markup(chat_id, message_id, m.settings_keyboard(user))

    elif kind == "count":
        if rest.isdigit() and settings.daily_min_lessons <= int(rest) <= settings.daily_max_lessons:
            user.daily_count = int(rest)
            db.commit()
        answer_callback(cq["id"], "Saqlandi")
        edit_markup(chat_id, message_id, m.settings_keyboard(user))

    elif kind == "notify":
        user.notify = not user.notify
        db.commit()
        answer_callback(cq["id"], "Saqlandi")
        edit_markup(chat_id, message_id, m.settings_keyboard(user))

    else:
        answer_callback(cq["id"])


def handle_quiz(db: Session, user: User, cq: dict, chat_id: int, message_id: int, rest: str) -> None:
    lid, _, answers = rest.partition(":")
    lesson = db.get(Lesson, int(lid)) if lid.isdigit() else None
    quiz = quiz_of(lesson) if lesson else []
    valid = answers == "" or (answers.isdigit() and len(answers) <= len(quiz))
    if not quiz or not valid:
        return answer_callback(cq["id"], "Test topilmadi")
    answer_callback(cq["id"])

    if answers == "":  # testni boshlash — yangi xabar
        send_message(chat_id, m.quiz_question_text(lesson, quiz, 0), m.quiz_keyboard(lesson, quiz, ""))
        return

    qi = len(answers) - 1
    given = int(answers[-1])
    q = quiz[qi]
    ok = given == q["answer"]
    feedback = (
        ("✅ To'g'ri!" if ok else f"❌ Noto'g'ri. To'g'ri javob: <b>{m.e(q['options'][q['answer']])}</b>")
        + (f"\n<i>{m.e(q['explain'])}</i>" if q.get("explain") else "")
        + "\n\n"
    )
    if len(answers) < len(quiz):
        edit_text(chat_id, message_id, m.quiz_question_text(lesson, quiz, len(answers), feedback),
                  m.quiz_keyboard(lesson, quiz, answers))
        return

    result = grade_quiz(db, user, lesson, [int(c) for c in answers])
    text = (
        f"📝 <b>Test yakunlandi: {m.e(lesson.title)}</b>\n\n{feedback}"
        f"Natija: <b>{result['score']} / {result['total']}</b>"
    )
    if result["xp"]:
        text += f"\n+{result['xp']} XP 🎉"
    elif result["total"]:
        text += "\n<i>(XP faqat birinchi urinish uchun beriladi)</i>"
    if result["level_changed"]:
        text += f"\n\n🎚 Darajangiz yangilandi: <b>{LEVELS[result['level_changed']]}</b>"
    edit_text(chat_id, message_id, text)


def handle_review(db: Session, user: User, cq: dict, chat_id: int, message_id: int, rest: str) -> None:
    try:
        ul_id, qi, oi = (int(x) for x in rest.split(":"))
    except ValueError:
        return answer_callback(cq["id"])
    ul = db.get(UserLesson, ul_id)
    if not ul or ul.user_id != user.id:
        return answer_callback(cq["id"], "Topilmadi")
    quiz = quiz_of(ul.lesson)
    if qi >= len(quiz) or ul.review_stage not in (1, 2):
        answer_callback(cq["id"], "Bu savol allaqachon yechilgan")
        return edit_markup(chat_id, message_id, {"inline_keyboard": []})
    q = quiz[qi]
    ok = oi == q["answer"]
    res = answer_review(db, user, ul, ok)
    answer_callback(cq["id"], "To'g'ri! 🎉" if ok else "Noto'g'ri")
    text = (
        f"🧠 <b>Takrorlash:</b> <i>{m.e(ul.lesson.title)}</i>\n\n❓ {m.e(q['q'])}\n\n"
        + (f"✅ To'g'ri! +{res['xp']} XP" if ok else f"❌ To'g'ri javob: <b>{m.e(q['options'][q['answer']])}</b>")
        + (f"\n<i>{m.e(q['explain'])}</i>" if q.get("explain") else "")
        + ("\n\n🏁 Bu dars xotirangizda mustahkamlandi!" if res["finished"] else "")
        + ("" if ok else "\n\nErtaga yana so'rayman 😉")
    )
    edit_text(chat_id, message_id, text)


def setup_bot() -> dict:
    """Webhook, buyruqlar ro'yxati va menyu tugmasini sozlaydi."""
    base = settings.web_url.rstrip("/")
    results = {}
    results["webhook"] = call(
        "setWebhook",
        url=f"{base}/api/telegram/webhook",
        secret_token=settings.telegram_webhook_secret,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=False,
    )
    results["commands"] = call(
        "setMyCommands",
        commands=[
            {"command": "dars", "description": "Yana dars yuborish"},
            {"command": "progress", "description": "Progressim"},
            {"command": "sozlamalar", "description": "Mavzular va darslar soni"},
            {"command": "reyting", "description": "Eng faol o'quvchilar"},
            {"command": "yangi", "description": "Ustoz suhbatini tozalash"},
            {"command": "help", "description": "Yordam"},
        ],
    )
    results["menu"] = call(
        "setChatMenuButton",
        menu_button={"type": "web_app", "text": "Platforma", "web_app": {"url": base + "/"}},
    )
    results["me"] = call("getMe")
    return results
