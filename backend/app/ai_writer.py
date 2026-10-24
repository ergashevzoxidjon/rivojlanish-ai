"""Claude API orqali: yangilikni baholash, o'zbekcha dars + test yozish, AI ustoz javoblari."""
import json
import logging
import re
from typing import List, Optional

from .config import settings
from .models import LEVELS, TOPICS

log = logging.getLogger(__name__)

AUTHOR_SYSTEM = """Sen "Rivojlanish AI" platformasining bosh muallifisan. Vazifang: sun'iy intellekt \
vositalaridagi yangi funksiyalarni o'zbek tilida (lotin yozuvida) oddiy, aniq va amaliy \
qadam-baqadam yo'riqnomaga aylantirish.

Qoidalar:
- Faqat o'zbek tilida (lotin) yoz. Texnik atamalar (prompt, API, MCP, agent, terminal) o'zgarmaydi.
- Faqat berilgan manbadagi va o'zing aniq biladigan faktlarni yoz. Taxmin qilma; narx, sana, \
raqam o'ylab topma. Manbada bo'lmagan menyu nomlarini to'qima — umumiyroq yoz.
- Qadamlar raqamlangan bo'lsin; kod yoki prompt namunasini ``` blokda ber.
- Amaliy topshiriq bitta, aniq, 10-20 daqiqada bajariladigan va natijasi tekshiriladigan bo'lsin.
- Test savollari darsni o'qigan odam javob bera oladigan, aniq bitta to'g'ri javobli bo'lsin.
- Javobni FAQAT JSON ko'rinishida qaytar, boshqa hech narsa yozma."""

TUTOR_SYSTEM = """Sen "Rivojlanish AI" platformasidagi AI ustozsan. Foydalanuvchilarga sun'iy \
intellekt vositalarini (Claude, ChatGPT, Gemini, Claude Code, Cursor, Codex, n8n, MCP va h.k.) \
o'rganishda yordam berasan.

Qoidalar:
- Faqat o'zbek tilida (lotin) javob ber, samimiy va aniq.
- Qisqa yoz: odatda 3-8 gap yoki qisqa raqamlangan qadamlar. Kerak bo'lsa kod/prompt namunasi ber.
- Bilmagan narsangni bilaman deb aytma — "aniq bilmayman, rasmiy hujjatni tekshiring" de.
- Agar savol dars haqida bo'lsa, dars matniga tayan.
- Telegram uchun: markdown jadval ishlatma; **qalin** va `kod` mumkin."""

LESSON_SCHEMA = """{
  "title": "qisqa sarlavha (60 belgigacha)",
  "tool": "vosita nomi: Claude, ChatGPT, Gemini, Claude Code, Cursor, Codex, Gemini CLI, n8n, MCP ...",
  "level": "beginner | intermediate | advanced",
  "minutes": 7,
  "importance": 7,
  "summary": "Bu nima? 2-3 gapda: yangi funksiya va nima uchun kerak",
  "body_md": "## Qadam-baqadam\\n1. ...\\n2. ...\\n\\n## Amaliy misol\\n...\\n\\n## Foydali maslahatlar\\n- ...",
  "task_md": "Amaliy topshiriq: bitta aniq vazifa va natija qanday bo'lishi kerakligi",
  "quiz": [
    {"q": "savol", "options": ["A", "B", "C", "D"], "answer": 0, "explain": "nega bu javob to'g'ri"}
  ]
}
importance: 9-10 = ko'pchilik uchun katta yangi imkoniyat; 6-8 = foydali funksiya; 3-5 = tor doiradagi \
yaxshilanish; 1-2 = deyarli ahamiyatsiz. quiz: aynan 3 ta savol, har birida 3-4 variant."""


def _client():
    import anthropic

    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY sozlanmagan")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=120, max_retries=2)


def _ask(system: str, messages: List[dict], max_tokens: int = 6000) -> str:
    msg = _client().messages.create(
        model=settings.claude_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def parse_json(text: str) -> Optional[dict]:
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return None
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def clean_quiz(raw) -> list:
    quiz = []
    if not isinstance(raw, list):
        return quiz
    for item in raw[:5]:
        if not isinstance(item, dict):
            continue
        q = str(item.get("q", "")).strip()
        options = [str(o).strip()[:100] for o in item.get("options", []) if str(o).strip()]
        try:
            answer = int(item.get("answer", -1))
        except (TypeError, ValueError):
            continue
        if q and 2 <= len(options) <= 5 and 0 <= answer < len(options):
            quiz.append(
                {"q": q[:300], "options": options, "answer": answer, "explain": str(item.get("explain", ""))[:500]}
            )
    return quiz


def clean_lesson(data: dict, topic: str, default_tool: str = "") -> Optional[dict]:
    required = ("title", "summary", "body_md", "task_md")
    if not all(str(data.get(k, "")).strip() for k in required):
        return None

    def num(key, default, lo, hi):
        try:
            return max(lo, min(hi, int(data.get(key) or default)))
        except (TypeError, ValueError):
            return default

    return {
        "title": str(data["title"]).strip()[:300],
        "tool": str(data.get("tool") or default_tool).strip()[:40],
        "level": data.get("level") if data.get("level") in LEVELS else "beginner",
        "minutes": num("minutes", 7, 2, 60),
        "importance": num("importance", 5, 1, 10),
        "summary": str(data["summary"]).strip(),
        "body_md": str(data["body_md"]).strip(),
        "task_md": str(data["task_md"]).strip(),
        "quiz": clean_quiz(data.get("quiz")),
        "topic": topic,
    }


def _titles_block(titles: List[str]) -> str:
    return "\n".join(f"- {t}" for t in titles[-60:]) or "- (hali yo'q)"


def lesson_from_news(
    title: str, content: str, url: str, topic: str, tool: str, recent_titles: List[str]
) -> dict:
    """Yangilikni baholaydi.
    Qaytaradi: {"worth": False, "reason": ...} yoki {"worth": True, "lesson": {...}}"""
    prompt = f"""Quyidagi yangilik "{TOPICS.get(topic, topic)}" mavzusiga oid ({tool or 'AI vosita'}).

1-qadam — baholash. Bu foydalanuvchi o'rganib, amalda ishlata oladigan YANGI FUNKSIYA yoki muhim \
imkoniyatmi? Quyidagilar foydali EMAS: oddiy xato tuzatishlar, kichik versiyalar, ichki \
o'zgarishlar, korporativ/moliya/xodimlar yangiliklari, tadqiqot maqolasi (amaliy funksiyasiz).

2-qadam — takrorni tekshirish. Platformada so'nggi darslar:
{_titles_block(recent_titles)}
Agar shu funksiya allaqachon yoritilgan bo'lsa — foydali emas (sabab: "takror").

Foydali bo'lmasa faqat: {{"worth": false, "reason": "qisqa sabab"}}
Foydali bo'lsa: {{"worth": true, "lesson": {LESSON_SCHEMA}}}

Manba: {url}
Sarlavha: {title}
Matn:
{content[:14000]}"""
    data = parse_json(_ask(AUTHOR_SYSTEM, [{"role": "user", "content": prompt}]))
    if not data:
        raise ValueError("AI javobi JSON emas")
    if not data.get("worth"):
        return {"worth": False, "reason": str(data.get("reason", ""))[:300]}
    lesson = clean_lesson(data.get("lesson") or {}, topic, tool)
    if not lesson:
        raise ValueError("AI dars maydonlarini to'liq qaytarmadi")
    lesson["source_url"] = url
    return {"worth": True, "lesson": lesson}


def lesson_on_demand(topic: str, existing_titles: List[str], level: str = "beginner") -> Optional[dict]:
    """Foydalanuvchi "Yana dars" bosganda yangi mustaqil dars yozadi."""
    prompt = f"""Mavzu: {TOPICS.get(topic, topic)}. O'quvchi darajasi: {LEVELS.get(level, LEVELS['beginner'])}.

Shu darajadagi o'quvchi bugun o'rganib, darhol amalda qo'llay oladigan bitta foydali dars yoz: \
aniq funksiya, samarali usul yoki amaliy ish jarayoni (masalan, kundalik ishni avtomatlashtirish). \
Quyidagi darslar allaqachon bor — ularni takrorlama, yangi burchak tanla:
{_titles_block(existing_titles)}

Faqat shu JSONni qaytar:
{LESSON_SCHEMA}"""
    data = parse_json(_ask(AUTHOR_SYSTEM, [{"role": "user", "content": prompt}]))
    if not data:
        raise ValueError("AI javobi JSON emas")
    lesson = clean_lesson(data, topic)
    if lesson:
        lesson["level"] = level if level in LEVELS else lesson["level"]
    return lesson


def tutor_answer(question: str, history: List[dict], lesson: Optional[dict] = None) -> str:
    """AI ustoz javobi. history: [{"role": "user"|"assistant", "content": "..."}] (eski -> yangi)."""
    context = ""
    if lesson:
        context = (
            f"Foydalanuvchi quyidagi darsni o'rganmoqda.\n"
            f"Sarlavha: {lesson['title']}\nVosita: {lesson.get('tool', '')}\n"
            f"Qisqacha: {lesson['summary']}\n\nDars matni:\n{lesson['body_md'][:8000]}\n\n"
            f"Topshiriq: {lesson['task_md'][:1500]}\n\n---\n"
        )
    messages = [m for m in history[-8:] if m.get("role") in ("user", "assistant")]
    # Claude API: xabarlar user bilan boshlanishi va navbatma-navbat bo'lishi kerak
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    merged: List[dict] = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n\n" + m["content"]
        else:
            merged.append({"role": m["role"], "content": m["content"]})
    if merged and merged[-1]["role"] == "user":
        merged.pop()
    merged.append({"role": "user", "content": context + question})
    return _ask(TUTOR_SYSTEM, merged, max_tokens=1500).strip()
