"""Manbalardan yangiliklarni yig'ish va AI orqali darsga aylantirish."""
import hashlib
import html
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai_writer
from .clock import utcnow
from .config import settings
from .lessons import slugify
from .models import Lesson, RawItem, Source

log = logging.getLogger(__name__)

# Boshlang'ich manbalar. Admin panelda qo'shish/o'chirish mumkin.
DEFAULT_SOURCES = [
    # Claude / ChatGPT / Gemini
    {"name": "Anthropic yangiliklari", "url": "https://www.anthropic.com/news", "kind": "html", "topic": "chat", "tool": "Claude"},
    {"name": "OpenAI yangiliklari", "url": "https://openai.com/news/rss.xml", "kind": "rss", "topic": "chat", "tool": "ChatGPT"},
    {"name": "ChatGPT release notes", "url": "https://help.openai.com/en/articles/6825453-chatgpt-release-notes", "kind": "html", "topic": "chat", "tool": "ChatGPT"},
    {"name": "Google Gemini blog", "url": "https://blog.google/products/gemini/rss/", "kind": "rss", "topic": "chat", "tool": "Gemini"},
    # Kod yozish AI'lari
    {"name": "Claude Code releases", "url": "https://github.com/anthropics/claude-code/releases.atom", "kind": "rss", "topic": "coding", "tool": "Claude Code"},
    {"name": "OpenAI Codex releases", "url": "https://github.com/openai/codex/releases.atom", "kind": "rss", "topic": "coding", "tool": "Codex"},
    {"name": "Gemini CLI releases", "url": "https://github.com/google-gemini/gemini-cli/releases.atom", "kind": "rss", "topic": "coding", "tool": "Gemini CLI"},
    {"name": "Cursor changelog", "url": "https://cursor.com/changelog", "kind": "html", "topic": "coding", "tool": "Cursor"},
    # Avtomatlashtirish va agentlar
    {"name": "n8n releases", "url": "https://github.com/n8n-io/n8n/releases.atom", "kind": "rss", "topic": "automation", "tool": "n8n"},
    {"name": "MCP spetsifikatsiyasi", "url": "https://github.com/modelcontextprotocol/modelcontextprotocol/releases.atom", "kind": "rss", "topic": "automation", "tool": "MCP"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RivojlanishAI/1.0)"}
FIRST_RUN_DAYS = 7


def seed_sources(db: Session) -> int:
    added = 0
    for s in DEFAULT_SOURCES:
        if not db.scalar(select(Source).where(Source.url == s["url"])):
            db.add(Source(**s))
            added += 1
    db.commit()
    return added


def strip_html(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text or "", flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def _fetch(url: str) -> str:
    with httpx.Client(timeout=25, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def _entry_time(entry) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6])
    return None


def collect_rss(db: Session, source: Source, text: str) -> int:
    import feedparser

    feed = feedparser.parse(text)
    first_run = source.last_checked_at is None
    cutoff = utcnow() - timedelta(days=FIRST_RUN_DAYS)
    added = 0
    for entry in feed.entries[:30]:
        uid = (entry.get("id") or entry.get("link") or entry.get("title") or "")[:255]
        if not uid or db.scalar(select(RawItem.id).where(RawItem.uid == uid)):
            continue
        content = ""
        if entry.get("content"):
            content = entry.content[0].get("value", "")
        content = strip_html(content or entry.get("summary", ""))
        published = _entry_time(entry)
        status = "new"
        if first_run and published and published < cutoff:
            status = "skipped"  # birinchi ishga tushishda eski tarixni darsga aylantirmaymiz
        db.add(
            RawItem(
                source_id=source.id,
                uid=uid,
                title=(entry.get("title") or "Nomsiz")[:500],
                url=(entry.get("link") or source.url)[:500],
                content=content[:20000],
                published_at=published,
                status=status,
                note="eski (birinchi yig'ish)" if status == "skipped" else None,
            )
        )
        added += 1
    return added


def collect_html(db: Session, source: Source, text: str) -> int:
    """Sahifadagi yangi qatorlarni topadi (oldingi ko'rinish bilan solishtirib)."""
    current = strip_html(text)
    old_lines = set((source.snapshot or "").splitlines())
    source_was_new = source.snapshot is None
    source.snapshot = current[:60000]
    if source_was_new:
        return 0  # birinchi marta faqat eslab qolamiz
    new_lines = [ln for ln in current.splitlines() if ln not in old_lines and len(ln) > 20]
    if not new_lines:
        return 0
    body = "\n".join(new_lines)[:15000]
    uid = f"{source.url}#{hashlib.sha1(body.encode()).hexdigest()[:16]}"
    if db.scalar(select(RawItem.id).where(RawItem.uid == uid)):
        return 0
    db.add(
        RawItem(
            source_id=source.id,
            uid=uid,
            title=f"{source.name}: yangi o'zgarishlar",
            url=source.url,
            content=body,
            published_at=utcnow(),
        )
    )
    return 1


def collect_all(db: Session) -> dict:
    result = {"sources": 0, "new_items": 0, "errors": []}
    for source in db.scalars(select(Source).where(Source.active.is_(True))).all():
        result["sources"] += 1
        try:
            text = _fetch(source.url)
            if source.kind == "html":
                result["new_items"] += collect_html(db, source, text)
            else:
                result["new_items"] += collect_rss(db, source, text)
            source.last_error = None
        except Exception as e:  # bitta manba xatosi boshqalarni to'xtatmasin
            source.last_error = str(e)[:500]
            result["errors"].append(f"{source.name}: {e}")
            log.warning("Manba xatosi %s: %s", source.name, e)
        source.last_checked_at = utcnow()
        db.commit()
    return result


def recent_titles(db: Session, days: int = 45, topic: Optional[str] = None) -> List[str]:
    q = select(Lesson.title).where(
        Lesson.created_at >= utcnow() - timedelta(days=days), Lesson.status != "rejected"
    )
    if topic:
        q = q.where(Lesson.topic == topic)
    return list(db.scalars(q.order_by(Lesson.created_at)))


def save_lesson(
    db: Session,
    data: dict,
    origin: str,
    raw_item_id: Optional[int] = None,
    requested_by: Optional[int] = None,
) -> Lesson:
    publish = settings.auto_publish or origin == "on_demand"
    lesson = Lesson(
        slug=slugify(data["title"]),
        title=data["title"],
        topic=data["topic"],
        tool=data.get("tool", ""),
        level=data.get("level", "beginner"),
        minutes=data.get("minutes", 5),
        summary=data["summary"],
        body_md=data["body_md"],
        task_md=data["task_md"],
        source_url=data.get("source_url", ""),
        importance=data.get("importance", 5),
        quiz_json=json.dumps(data.get("quiz") or [], ensure_ascii=False),
        origin=origin,
        raw_item_id=raw_item_id,
        requested_by=requested_by,
        status="published" if publish else "draft",
        published_at=utcnow() if publish else None,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def process_new_items(db: Session, limit: Optional[int] = None) -> List[Lesson]:
    """Yangi xom elementlarni AI orqali baholab, foydalilarini darsga aylantiradi."""
    limit = limit or settings.collect_max_items
    if not settings.anthropic_api_key:
        # Kalit qo'yilmaguncha yangiliklar "new" holatida kutib turadi (yo'qolmaydi)
        return []
    items = db.scalars(
        select(RawItem)
        .where(RawItem.status == "new")
        .order_by(RawItem.published_at.desc())
        .limit(limit)
    ).all()
    created = []
    for item in items:
        try:
            result = ai_writer.lesson_from_news(
                item.title,
                item.content,
                item.url,
                item.source.topic,
                item.source.tool,
                recent_titles(db, topic=item.source.topic),
            )
            if result["worth"]:
                created.append(save_lesson(db, result["lesson"], "news", item.id))
                item.status = "lesson"
            else:
                item.status = "skipped"
                item.note = "AI: " + (result.get("reason") or "foydali emas")
        except Exception as e:
            item.status = "error"
            item.note = str(e)[:500]
            log.warning("AI xatosi (%s): %s", item.title, e)
        db.commit()
    return created
