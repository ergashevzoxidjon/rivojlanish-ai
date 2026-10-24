"""Bot matnlari va tugmalari."""
import html
from typing import Optional

from ..config import settings
from ..models import LEVELS, TOPICS, Lesson, User

BTN_MORE = "📚 Yana dars yuborish"
BTN_PROGRESS = "📊 Progressim"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_OPEN = "🚀 Platformani ochish"

TOPIC_ICONS = {"chat": "💬", "coding": "💻", "automation": "🤖"}


def e(text: str) -> str:
    return html.escape(text or "")


def web(path: str = "/") -> str:
    return settings.web_url.rstrip("/") + path


def main_keyboard() -> dict:
    return {
        "keyboard": [
            [{"text": BTN_MORE}],
            [{"text": BTN_PROGRESS}, {"text": BTN_SETTINGS}],
            [{"text": BTN_OPEN, "web_app": {"url": web("/")}}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def register_keyboard(token: str) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🔐 Google bilan ro'yxatdan o'tish", "url": web(f"/register?t={token}")}]
        ]
    }


def welcome_unregistered(name: str) -> str:
    return (
        f"Assalomu alaykum, <b>{e(name)}</b>! 👋\n\n"
        f"<b>{e(settings.app_name)}</b> — sun'iy intellektdagi yangi funksiyalarni har kuni "
        "o'zbek tilida qadam-baqadam o'rgatadigan platforma.\n\n"
        f"☀️ Har kuni soat {settings.daily_hour}:00 da {settings.daily_min_lessons}–"
        f"{settings.daily_max_lessons} ta yangi dars\n"
        "✍️ Har darsda amaliy topshiriq\n"
        "📊 Progress va ketma-ket kunlar\n\n"
        "Boshlash uchun Google (email) orqali ro'yxatdan o'ting 👇"
    )


def welcome_registered(user: User) -> str:
    return (
        f"Xush kelibsiz, <b>{e(user.name)}</b>! ✅\n\n"
        f"Har kuni soat {settings.daily_hour}:00 da sizga yangi darslar keladi.\n"
        f"Vaqtingiz ko'p bo'lsa — <b>{BTN_MORE}</b> tugmasini bosing, "
        "xohlagancha dars olasiz."
    )


def lesson_text(lesson: Lesson, index: Optional[int] = None) -> str:
    head = f"{index}. " if index else ""
    icon = TOPIC_ICONS.get(lesson.topic, "📘")
    meta = " · ".join(
        x for x in [lesson.tool, LEVELS.get(lesson.level, ""), f"{lesson.minutes} daqiqa"] if x
    )
    task = lesson.task_md.strip()
    if len(task) > 600:
        task = task[:600].rsplit(" ", 1)[0] + "…"
    return (
        f"{icon} <b>{head}{e(lesson.title)}</b>\n"
        f"<i>{e(meta)}</i>\n\n"
        f"{e(lesson.summary)}\n\n"
        f"✍️ <b>Topshiriq:</b> {e(task)}"
    )


def lesson_keyboard(lesson: Lesson, done: bool = False) -> dict:
    done_btn = (
        {"text": "✅ Bajarildi", "callback_data": f"undo:{lesson.id}"}
        if done
        else {"text": "☑️ Bajardim", "callback_data": f"done:{lesson.id}"}
    )
    rows = [[{"text": "📖 To'liq o'qish", "web_app": {"url": web(f"/lessons/{lesson.slug}")}}]]
    second = [done_btn]
    if lesson.quiz_json and lesson.quiz_json != "[]":
        second.append({"text": "📝 Test", "callback_data": f"qz:{lesson.id}:"})
    rows.append(second)
    rows.append([{"text": "❓ Ustozdan so'rash", "callback_data": f"ask:{lesson.id}"}])
    return {"inline_keyboard": rows}


def more_keyboard() -> dict:
    return {"inline_keyboard": [[{"text": BTN_MORE, "callback_data": "more"}]]}


def progress_text(stats: dict) -> str:
    rank = stats["rank"]
    to_next = (
        f" (keyingisi «{rank['next_name']}» — yana {rank['next_xp'] - rank['xp']} XP)"
        if rank["next_xp"]
        else ""
    )
    lines = [
        "📊 <b>Sizning progressingiz</b>\n",
        f"🏅 Unvon: <b>{e(rank['name'])}</b> · {rank['xp']} XP{e(to_next)}",
        f"🎚 Daraja: <b>{e(stats['level_name'])}</b> (testlarga qarab moslashadi)",
        f"🔥 Ketma-ket kunlar: <b>{stats['streak']}</b> (eng yaxshisi: {stats['best_streak']})",
        f"📖 O'qilgan: <b>{stats['read']}</b> · ✅ Bajarilgan: <b>{stats['done']}</b>",
        f"🎯 Testlar: {stats['quizzes']} ta, aniqlik {stats['quiz_accuracy']}%\n",
    ]
    for t in stats["by_topic"]:
        lines.append(f"{TOPIC_ICONS.get(t['key'], '')} {e(t['name'])}: {t['done']} / {t['total']}")
    earned = [a for a in stats["achievements"] if a["earned"]]
    if earned:
        lines.append("\n🏆 Yutuqlar: " + " ".join(a["icon"] for a in earned))
    return "\n".join(lines)


def quiz_question_text(lesson: Lesson, quiz: list, qi: int, feedback: str = "") -> str:
    q = quiz[qi]
    return (
        f"📝 <b>Test: {e(lesson.title)}</b>\n"
        f"Savol {qi + 1} / {len(quiz)}\n\n"
        f"{feedback}"
        f"❓ {e(q['q'])}"
    )


def quiz_keyboard(lesson: Lesson, quiz: list, answers: str) -> dict:
    qi = len(answers)
    return {
        "inline_keyboard": [
            [{"text": opt, "callback_data": f"qz:{lesson.id}:{answers}{oi}"}]
            for oi, opt in enumerate(quiz[qi]["options"])
        ]
    }


def settings_text(user: User) -> str:
    return (
        "⚙️ <b>Sozlamalar</b>\n\n"
        "Mavzular va kunlik darslar sonini tanlang. "
        f"Darslar har kuni soat {settings.daily_hour}:00 da keladi."
    )


def settings_keyboard(user: User) -> dict:
    rows = []
    for key, name in TOPICS.items():
        mark = "✅" if key in user.topic_list else "⬜"
        rows.append([{"text": f"{mark} {name}", "callback_data": f"topic:{key}"}])
    counts = []
    for n in range(settings.daily_min_lessons, settings.daily_max_lessons + 1):
        mark = "• " if user.daily_count == n else ""
        counts.append({"text": f"{mark}{n} ta dars", "callback_data": f"count:{n}"})
    rows.append(counts)
    rows.append(
        [
            {
                "text": "🔔 Ertalabki xabar: yoqilgan" if user.notify else "🔕 Ertalabki xabar: o'chirilgan",
                "callback_data": "notify",
            }
        ]
    )
    return {"inline_keyboard": rows}


HELP = (
    "ℹ️ <b>Yordam</b>\n\n"
    f"{BTN_MORE} — yana darslar olish\n"
    f"{BTN_PROGRESS} — statistika\n"
    f"{BTN_SETTINGS} — mavzular va darslar soni\n"
    f"{BTN_OPEN} — barcha darslar, arxiv va qidiruv\n\n"
    "❓ Har qanday savolingizni shunchaki yozing — AI ustoz o'zbek tilida javob beradi.\n\n"
    "Buyruqlar: /start, /dars, /progress, /sozlamalar, /reyting, /yangi (ustoz suhbatini tozalash), /help"
)


def md_to_html(text: str) -> str:
    """AI javobidagi oddiy markdownni Telegram HTML ga o'giradi."""
    import re

    parts = re.split(r"```(?:[\w+-]*)\n?(.*?)```", text or "", flags=re.S)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(f"<pre>{e(part.strip())}</pre>")
            continue
        chunk = e(part)
        chunk = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", chunk)
        chunk = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", chunk)
        chunk = re.sub(r"(?m)^#{1,6}\s*(.+)$", r"<b>\1</b>", chunk)
        chunk = re.sub(r"(?m)^\s*[-*]\s+", "• ", chunk)
        out.append(chunk)
    return "".join(out).strip()


def split_text(text: str, size: int = 3800) -> list:
    """Telegram 4096 belgi chegarasi uchun matnni qatorlar bo'yicha bo'ladi."""
    if len(text) <= size:
        return [text]
    chunks, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > size and cur:
            chunks.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks
