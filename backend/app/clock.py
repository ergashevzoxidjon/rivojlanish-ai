from datetime import datetime, timezone


def utcnow() -> datetime:
    """Joriy UTC vaqt (naive) — bazada shunday saqlanadi."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
