"""Telegram handoff, Paddle billing and LLM provider wiring (all network calls mocked)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from app.services import llm, telegram
from tests.conftest import signup

VISITOR = "visitor_abcdefghijklmnop"


class FakeTelegram:
    def __init__(self):
        self.sent: list[dict] = []
        self.next_id = 100

    def __call__(self, settings, method, payload=None, timeout=15.0):
        payload = payload or {}
        if method == "getMe":
            return {"username": "test_support_bot"}
        if method == "sendMessage":
            self.next_id += 1
            self.sent.append({**payload, "message_id": self.next_id})
            return {"message_id": self.next_id}
        return True


def test_telegram_connect_handoff_and_reply(make_client, monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(telegram, "api", fake)
    client = make_client(telegram_bot_token="123:abc", telegram_mode="off")
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    assert ws["telegram"]["connect_link"] == f"https://t.me/test_support_bot?start={ws['telegram']['connect_code']}"

    from app.db import SessionLocal

    def update(text, reply_to=None, message_id=500, chat_id=42):
        msg = {"message_id": message_id, "chat": {"id": chat_id}, "text": text}
        if reply_to:
            msg["reply_to_message"] = {"message_id": reply_to}
        with SessionLocal() as db:
            telegram.handle_update(db, _settings(), {"message": msg})
            db.commit()

    # wrong code does not connect
    update("/start wrongcode")
    assert client.get(f"/api/workspaces/{ws_id}").json()["telegram"]["connected"] is False
    update(f"/start {ws['telegram']['connect_code']}")
    ws2 = client.get(f"/api/workspaces/{ws_id}").json()
    assert ws2["telegram"]["connected"] is True
    assert ws2["telegram"]["connect_code"] != ws["telegram"]["connect_code"]  # one-time code

    key = ws["public_key"]
    conv = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "Do you deliver to Batumi?"}).json()
    cid = conv["conversation_id"]
    r = client.post(f"/api/widget/{key}/handoff", json={"visitor_id": VISITOR, "conversation_id": cid}).json()
    assert r["available"] is True and r["status"] == "handoff"
    handoff_msg = fake.sent[-1]
    assert handoff_msg["chat_id"] == "42" and "Batumi" in handoff_msg["text"]

    # visitor messages during handoff are forwarded, not answered by the bot
    r = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "conversation_id": cid, "text": "I need it by Friday"}).json()
    assert len(r["messages"]) == 1
    assert fake.sent[-1]["text"].endswith("I need it by Friday")

    # a stranger replying from another chat is ignored
    update("hacked", reply_to=handoff_msg["message_id"], chat_id=999)
    # the owner replies in Telegram
    update("Yes, delivery to Batumi takes 2 days.", reply_to=handoff_msg["message_id"], message_id=501)
    poll = client.get(f"/api/widget/{key}/conversations/{cid}", params={"visitor_id": VISITOR}).json()
    operator = [m for m in poll["messages"] if m["role"] == "operator"]
    assert [m["content"] for m in operator] == ["Yes, delivery to Batumi takes 2 days."]

    # /done hands the chat back to the AI
    update("/done", reply_to=501, message_id=502)
    poll = client.get(f"/api/widget/{key}/conversations/{cid}", params={"visitor_id": VISITOR}).json()
    assert poll["status"] == "bot"

    # new leads are sent to Telegram too
    client.post(f"/api/widget/{key}/leads", json={"visitor_id": VISITOR, "conversation_id": cid, "phone": "555123456"})
    assert "555123456" in fake.sent[-1]["text"]


def _settings():
    from app.config import get_settings

    return get_settings()


def _paddle_event(event_type, ws_id, status="active", price="pri_pro", occurred_at="2026-09-01T10:00:00.000000Z"):
    return {
        "event_id": "evt_1",
        "event_type": event_type,
        "occurred_at": occurred_at,
        "data": {
            "id": "sub_123",
            "status": status,
            "customer_id": "ctm_1",
            "custom_data": {"workspace_id": str(ws_id)},
            "items": [{"price": {"id": price}, "quantity": 1}],
            "management_urls": {"cancel": "https://paddle.test/cancel", "update_payment_method": "https://paddle.test/pay"},
        },
    }


def _signed_post(client, body: dict, secret: str, ts: int | None = None):
    raw = json.dumps(body).encode()
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}:".encode() + raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/billing/paddle/webhook",
        content=raw,
        headers={"Paddle-Signature": f"ts={ts};h1={sig}", "Content-Type": "application/json"},
    )


def test_paddle_webhook_upgrades_and_downgrades(make_client):
    secret = "pdl_ntfset_test"
    client = make_client(
        billing_enabled="true", paddle_webhook_secret=secret,
        paddle_price_starter="pri_starter", paddle_price_pro="pri_pro", paddle_price_business="pri_biz",
    )
    ws_id = signup(client)

    # bad / missing / expired signatures are rejected
    body = _paddle_event("subscription.created", ws_id)
    assert client.post("/api/billing/paddle/webhook", json=body).status_code == 401
    assert _signed_post(client, body, "wrong-secret").status_code == 401
    assert _signed_post(client, body, secret, ts=int(time.time()) - 3600).status_code == 401

    r = _signed_post(client, body, secret)
    assert r.status_code == 200 and r.json()["result"] == "plan=pro"
    billing = client.get(f"/api/workspaces/{ws_id}/billing").json()
    assert billing["plan"]["id"] == "pro"
    assert billing["paddle"]["cancel_url"] == "https://paddle.test/cancel"

    # an older, out-of-order event is ignored
    stale = _paddle_event("subscription.updated", ws_id, status="canceled", occurred_at="2026-08-01T00:00:00Z")
    assert _signed_post(client, stale, secret).json()["result"] == "stale"

    cancel = _paddle_event("subscription.canceled", ws_id, status="canceled", occurred_at="2026-09-20T00:00:00Z")
    assert _signed_post(client, cancel, secret).json()["result"] == "downgraded"
    assert client.get(f"/api/workspaces/{ws_id}/billing").json()["plan"]["id"] == "free"


def test_platform_fee_is_reported_transparently(make_client):
    client = make_client(billing_enabled="true", platform_fee_percent="1")
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    client.post(f"/api/widget/{ws['public_key']}/leads", json={"visitor_id": VISITOR, "phone": "555000000"})
    lead = client.get(f"/api/workspaces/{ws_id}/leads").json()[0]
    client.patch(f"/api/workspaces/{ws_id}/leads/{lead['id']}", json={"status": "won", "value": 300})
    fee = client.get(f"/api/workspaces/{ws_id}/billing").json()["platform_fee"]
    assert fee == {"percent": 1.0, "won_value_30d": 300.0, "fee_30d": 3.0}
    assert client.get("/api/public/plans").json()["platform_fee_percent"] == 1.0


def test_llm_answer_uses_knowledge_and_handles_no_answer(make_client, monkeypatch):
    calls = []

    def fake_post(url, *, headers=None, json=None, timeout=60.0):
        calls.append({"url": url, "headers": headers, "json": json})
        question = json["messages"][-1]["content"]
        if "Mars" in question:
            return {"content": [{"type": "text", "text": "[[NO_ANSWER]]"}]}
        return {"content": [{"type": "text", "text": "მიწოდება 5 ლარია."}]}

    monkeypatch.setattr(llm, "_post", fake_post)
    client = make_client(llm_provider="anthropic", anthropic_api_key="sk-ant-test")
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    client.post(f"/api/workspaces/{ws_id}/documents/faq", json={"question": "მიწოდების ფასი?", "answer": "5 ლარი"})

    r = client.post(f"/api/widget/{ws['public_key']}/messages", json={"visitor_id": VISITOR, "text": "რა ღირს მიწოდება?"}).json()
    assert r["answered"] is True and r["messages"][1]["content"] == "მიწოდება 5 ლარია."
    call = calls[-1]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "sk-ant-test"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert "5 ლარი" in call["json"]["system"]  # retrieved knowledge is in the prompt
    assert call["json"]["messages"][0]["role"] == "user"

    r = client.post(
        f"/api/widget/{ws['public_key']}/messages",
        json={"visitor_id": VISITOR, "conversation_id": r["conversation_id"], "text": "Do you fly to Mars?"},
    ).json()
    assert r["answered"] is False and "Sorry" in r["messages"][1]["content"]
    # conversation history is sent and roles alternate
    roles = [m["role"] for m in calls[-1]["json"]["messages"]]
    assert roles == ["user", "assistant", "user"]


def test_llm_failure_falls_back_to_keyword_answer(make_client, monkeypatch):
    def broken(*a, **k):
        raise llm.LLMError("boom")

    monkeypatch.setattr(llm, "_post", broken)
    client = make_client(llm_provider="openai", openai_api_key="sk-test")
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    client.post(f"/api/workspaces/{ws_id}/documents/faq", json={"question": "Opening hours?", "answer": "10:00-19:00 daily"})
    r = client.post(f"/api/widget/{ws['public_key']}/messages", json={"visitor_id": VISITOR, "text": "opening hours"}).json()
    assert r["answered"] is True and "10:00-19:00" in r["messages"][1]["content"]


def test_openai_and_ollama_request_shapes(monkeypatch):
    from dataclasses import replace

    calls = []

    def fake_post(url, *, headers=None, json=None, timeout=60.0):
        calls.append((url, headers, json))
        if "chat/completions" in url:
            return {"choices": [{"message": {"content": "ok-openai"}}]}
        return {"message": {"content": "ok-ollama"}}

    monkeypatch.setattr(llm, "_post", fake_post)
    base = _settings()
    s = replace(base, llm_provider="openai", openai_api_key="k", openai_model="m1")
    assert llm.complete("sys", [{"role": "assistant", "content": "hi"}, {"role": "user", "content": "q"}], s) == "ok-openai"
    url, headers, body = calls[-1]
    assert url.endswith("/chat/completions") and headers["Authorization"] == "Bearer k"
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "q"}]

    s = replace(base, llm_provider="ollama", ollama_model="llama3.1")
    assert llm.complete("sys", [{"role": "user", "content": "q"}], s) == "ok-ollama"
    assert calls[-1][0].endswith("/api/chat") and calls[-1][2]["stream"] is False
