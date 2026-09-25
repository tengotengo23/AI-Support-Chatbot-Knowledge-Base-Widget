from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

BASE_ENV = {
    "SECRET_KEY": "test-secret",
    "LLM_PROVIDER": "none",
    "EMBEDDINGS_PROVIDER": "none",
    "TELEGRAM_BOT_TOKEN": "",
    "BILLING_ENABLED": "false",
    "SIGNUP_ENABLED": "true",
    "SUPERADMIN_EMAILS": "",
    "PADDLE_WEBHOOK_SECRET": "",
    "PADDLE_PRICE_STARTER": "",
    "PADDLE_PRICE_PRO": "",
    "PADDLE_PRICE_BUSINESS": "",
    "PLATFORM_FEE_PERCENT": "0",
}


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    """Factory: make_client(**env) -> TestClient with a fresh database."""
    clients = []

    def _make(**env):
        from app.config import get_settings
        from app.security import rate_limiter
        from app.services import search, telegram

        # TEST_DATABASE_URL=postgresql+psycopg://... runs the suite against PostgreSQL.
        db_url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path}/test.db"
        values = {**BASE_ENV, "DATA_DIR": str(tmp_path), "DATABASE_URL": db_url}
        values.update({k.upper(): str(v) for k, v in env.items()})
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        rate_limiter.reset()
        search.clear_cache()
        telegram._bot_username = None

        if os.environ.get("TEST_DATABASE_URL"):
            from app import db, models  # noqa: F401

            db.Base.metadata.drop_all(db.configure(db_url))

        from app.main import create_app

        client = TestClient(create_app())
        client.__enter__()
        client.headers.update({"X-Requested-With": "fetch"})
        clients.append(client)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def client(make_client):
    return make_client()


def signup(client, email="owner@example.com", password="password123", name="Test Shop") -> int:
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "workspace_name": name})
    assert r.status_code == 200, r.text
    me = client.get("/api/auth/me").json()
    return me["workspaces"][0]["id"]


@pytest.fixture
def owner(client):
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    return client, ws


os.environ.setdefault("SECRET_KEY", "test-secret")
