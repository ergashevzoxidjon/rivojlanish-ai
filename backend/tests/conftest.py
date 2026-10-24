import os
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
        "TELEGRAM_BOT_TOKEN": "123456:TEST-TOKEN",
        "TELEGRAM_BOT_USERNAME": "rivojlanish_test_bot",
        "TELEGRAM_WEBHOOK_SECRET": "whsecret",
        "WEB_URL": "http://test.local",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-123456",
        "ADMIN_EMAILS": "admin@example.com",
        "GOOGLE_CLIENT_ID": "test-client",
        "CRON_KEY": "cronkey",
    }
)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from app.db import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def sent(monkeypatch):
    """Telegram API chaqiruvlarini ushlab qoladi."""
    calls = []

    def fake_call(method, **params):
        calls.append((method, params))
        if method == "getMe":
            return {"username": "rivojlanish_test_bot"}
        return {"message_id": len(calls)}

    from app import bg
    from app.bot import handlers, telegram

    monkeypatch.setattr(telegram, "call", fake_call)
    monkeypatch.setattr(handlers, "call", fake_call)
    monkeypatch.setattr(bg, "run_bg", lambda target, *args: target(*args))
    return calls


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
