from __future__ import annotations

from tests.conftest import signup

VISITOR = "visitor_abcdefghijklmnop"


def _faq(client, ws_id, q, a):
    r = client.post(f"/api/workspaces/{ws_id}/documents/faq", json={"question": q, "answer": a})
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_flow(client):
    assert client.get("/api/auth/me").status_code == 401
    ws_id = signup(client)
    me = client.get("/api/auth/me").json()
    assert me["email"] == "owner@example.com"
    assert me["is_superadmin"] is True  # first user on a server without SUPERADMIN_EMAILS
    assert me["workspaces"][0]["plan"] == "self_hosted"

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "nope"}).status_code == 401
    r = client.post("/api/auth/login", json={"email": "OWNER@example.com", "password": "password123"})
    assert r.status_code == 200
    assert client.get(f"/api/workspaces/{ws_id}").status_code == 200


def test_csrf_header_required(client):
    client.headers.pop("X-Requested-With")
    r = client.post("/api/auth/signup", json={"email": "a@b.co", "password": "password123"})
    assert r.status_code == 403


def test_workspace_isolation(client):
    ws_a = signup(client, "a@example.com")
    client.post("/api/auth/logout")
    signup(client, "b@example.com")
    assert client.get(f"/api/workspaces/{ws_a}").status_code == 404
    assert client.get(f"/api/workspaces/{ws_a}/leads").status_code == 404


def test_signup_disabled_after_first_user(make_client):
    client = make_client(signup_enabled="false")
    signup(client, "first@example.com")
    client.post("/api/auth/logout")
    r = client.post("/api/auth/signup", json={"email": "x@example.com", "password": "password123"})
    assert r.status_code == 403


def test_widget_answers_from_faq_and_tracks_unanswered(owner):
    client, ws = owner
    _faq(client, ws["id"], "რა ღირს მიწოდება თბილისში?", "მიწოდება თბილისში 5 ლარია, 100 ლარზე მეტ შეკვეთაზე უფასოა.")
    _faq(client, ws["id"], "What are your opening hours?", "We are open Monday to Saturday, 10:00–19:00.")

    key = ws["public_key"]
    cfg = client.get(f"/api/widget/{key}/config").json()
    assert cfg["strings"]["ka"]["send"] == "გაგზავნა"
    assert cfg["show_badge"] is True

    r = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "მიწოდება რა ღირს?"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["answered"] is True
    assert "5 ლარი" in data["messages"][1]["content"]
    conv_id = data["conversation_id"]

    r = client.post(
        f"/api/widget/{key}/messages",
        json={"visitor_id": VISITOR, "conversation_id": conv_id, "text": "What are your opening hours?"},
    )
    assert r.json()["answered"] is True
    assert "10:00" in r.json()["messages"][1]["content"]

    r = client.post(
        f"/api/widget/{key}/messages",
        json={"visitor_id": VISITOR, "conversation_id": conv_id, "text": "Do you sell spaceships to Mars?"},
    )
    data = r.json()
    assert data["answered"] is False and data["suggest_handoff"] is True
    assert data["conversation_id"] == conv_id

    stats = client.get(f"/api/workspaces/{ws['id']}/analytics").json()
    assert stats["totals"]["questions"] == 3
    assert stats["totals"]["unanswered"] == 1
    assert stats["unanswered_questions"][0]["question"] == "Do you sell spaceships to Mars?"

    # another visitor cannot read this conversation
    r = client.get(f"/api/widget/{key}/conversations/{conv_id}", params={"visitor_id": "someone_else_1234567"})
    assert r.status_code == 404
    r = client.get(f"/api/widget/{key}/conversations/{conv_id}", params={"visitor_id": VISITOR, "after": 0})
    assert len(r.json()["messages"]) == 6


def test_short_follow_up_does_not_reuse_previous_answer_without_llm(owner):
    client, ws = owner
    _faq(client, ws["id"], "რა ღირს მიწოდება თბილისში?", "მიწოდება თბილისში 5 ლარია.")
    key = ws["public_key"]
    first = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "მიწოდება რა ღირს?"}).json()
    assert first["answered"] is True
    second = client.post(
        f"/api/widget/{key}/messages",
        json={"visitor_id": VISITOR, "conversation_id": first["conversation_id"], "text": "Do you sell chocolate?"},
    ).json()
    assert second["answered"] is False


def test_small_talk_and_language(owner):
    client, ws = owner
    key = ws["public_key"]
    r = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "Привет"}).json()
    assert r["answered"] is True
    assert "Здравствуйте" in r["messages"][1]["content"]
    r = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "რა ფასი აქვს?"}).json()
    assert r["answered"] is False
    assert "სამწუხაროდ" in r["messages"][1]["content"]


def test_allowed_origins(owner):
    client, ws = owner
    client.patch(f"/api/workspaces/{ws['id']}", json={"allowed_origins": "https://shop.ge\nhttps://www.shop.ge/"})
    key = ws["public_key"]
    assert client.get(f"/api/widget/{key}/config", headers={"Origin": "https://evil.example"}).status_code == 403
    r = client.get(f"/api/widget/{key}/config", headers={"Origin": "https://www.shop.ge"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://www.shop.ge"
    pre = client.options(f"/api/widget/{key}/messages", headers={"Origin": "https://shop.ge"})
    assert pre.status_code == 204


def test_leads(owner):
    client, ws = owner
    key = ws["public_key"]
    conv = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "hello"}).json()
    r = client.post(f"/api/widget/{key}/leads", json={"visitor_id": VISITOR, "name": "Nino"})
    assert r.status_code == 400
    r = client.post(
        f"/api/widget/{key}/leads",
        json={"visitor_id": VISITOR, "conversation_id": conv["conversation_id"], "name": "Nino",
              "phone": "+995 555 12 34 56", "note": "=HYPERLINK(1)"},
    )
    assert r.status_code == 200
    leads = client.get(f"/api/workspaces/{ws['id']}/leads").json()
    assert leads[0]["name"] == "Nino" and leads[0]["conversation_id"] == conv["conversation_id"]

    r = client.patch(f"/api/workspaces/{ws['id']}/leads/{leads[0]['id']}", json={"status": "won", "value": 250})
    assert r.json()["status"] == "won"
    csv_text = client.get(f"/api/workspaces/{ws['id']}/leads.csv").text
    assert "Nino" in csv_text and "'=HYPERLINK(1)" in csv_text


def test_operator_reply_from_admin(owner):
    client, ws = owner
    key = ws["public_key"]
    conv = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "hello"}).json()
    cid = conv["conversation_id"]
    last_id = conv["messages"][-1]["id"]
    client.post(f"/api/workspaces/{ws['id']}/conversations/{cid}/reply", json={"text": "Hi, this is Nino!"})
    poll = client.get(f"/api/widget/{key}/conversations/{cid}", params={"visitor_id": VISITOR, "after": last_id}).json()
    assert poll["status"] == "handoff"
    assert poll["messages"][0]["role"] == "operator"
    # while a human handles the chat, the bot stays silent
    r = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "conversation_id": cid, "text": "thanks"})
    assert len(r.json()["messages"]) == 1
    client.post(f"/api/workspaces/{ws['id']}/conversations/{cid}/close")
    detail = client.get(f"/api/workspaces/{ws['id']}/conversations/{cid}").json()
    assert detail["status"] == "bot"
    assert detail["messages"][-1]["role"] == "system"
    listing = client.get(f"/api/workspaces/{ws['id']}/conversations").json()
    assert listing[0]["id"] == cid and listing[0]["message_count"] == 5


def test_handoff_without_telegram_suggests_contact(owner):
    client, ws = owner
    key = ws["public_key"]
    conv = client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "hello"}).json()
    r = client.post(f"/api/widget/{key}/handoff", json={"visitor_id": VISITOR, "conversation_id": conv["conversation_id"]})
    assert r.json()["available"] is False
    assert r.json()["status"] == "bot"


def test_documents_text_and_delete(owner):
    client, ws = owner
    wid = ws["id"]
    r = client.post(f"/api/workspaces/{wid}/documents/text", json={
        "title": "Returns policy",
        "content": "You can return any product within 14 days. Refunds are processed in 5 business days.",
    })
    assert r.status_code == 200
    doc_id = r.json()["id"]
    ans = client.post(f"/api/workspaces/{wid}/test-chat", json={"text": "How many days do I have to return a product?"}).json()
    assert ans["answered"] is True and "14 days" in ans["text"]
    assert client.delete(f"/api/workspaces/{wid}/documents/{doc_id}").status_code == 200
    ans = client.post(f"/api/workspaces/{wid}/test-chat", json={"text": "How many days do I have to return a product?"}).json()
    assert ans["answered"] is False


def test_url_import_blocks_private_addresses(owner):
    client, ws = owner
    r = client.post(f"/api/workspaces/{ws['id']}/documents/url", json={"url": "http://127.0.0.1:8000/admin"})
    assert r.status_code == 400
    r = client.post(f"/api/workspaces/{ws['id']}/documents/url", json={"url": "http://169.254.169.254/latest/meta-data"})
    assert r.status_code == 400


def test_quota_and_plan_limits_when_billing_enabled(make_client):
    client = make_client(billing_enabled="true", superadmin_emails="boss@example.com")
    ws_id = signup(client)
    ws = client.get(f"/api/workspaces/{ws_id}").json()
    assert ws["plan"]["id"] == "free"
    assert client.get("/api/auth/me").json()["is_superadmin"] is False

    for i in range(5):
        _faq(client, ws_id, f"Question {i}?", f"Answer {i}.")
    r = client.post(f"/api/workspaces/{ws_id}/documents/faq", json={"question": "Q6?", "answer": "A6"})
    assert r.status_code == 402

    from app.db import SessionLocal
    from app.models import Usage
    from app.plans import current_period

    with SessionLocal() as db:
        db.add(Usage(workspace_id=ws_id, period=current_period(), ai_messages=100))
        db.commit()
    r = client.post(f"/api/widget/{ws['public_key']}/messages", json={"visitor_id": VISITOR, "text": "Question 1?"}).json()
    assert r["quota_exceeded"] is True
    assert r["answered"] is False

    # platform owner upgrades the plan manually (e.g. after a bank transfer)
    assert client.get("/api/platform/workspaces").status_code == 403
    client.post("/api/auth/logout")
    signup(client, "boss@example.com")
    listing = client.get("/api/platform/workspaces").json()
    assert any(w["id"] == ws_id for w in listing["workspaces"])
    r = client.post(f"/api/platform/workspaces/{ws_id}/plan", json={"plan": "pro", "expires_at": "2099-01-01T00:00:00Z"})
    assert r.status_code == 200
    r = client.post(f"/api/widget/{ws['public_key']}/messages", json={"visitor_id": VISITOR, "text": "Question 1?"}).json()
    assert r["answered"] is True
    cfg = client.get(f"/api/widget/{ws['public_key']}/config").json()
    assert cfg["show_badge"] is False  # Pro removes branding
    assert client.get("/api/platform/workspaces").json()["mrr_usd"] == 49


def test_widget_rate_limit(make_client):
    client = make_client(widget_rate_limit_per_minute="3")
    ws_id = signup(client)
    key = client.get(f"/api/workspaces/{ws_id}").json()["public_key"]
    codes = [
        client.post(f"/api/widget/{key}/messages", json={"visitor_id": VISITOR, "text": "hi"}).status_code
        for _ in range(4)
    ]
    assert codes == [200, 200, 200, 429]


def test_public_pages(make_client):
    client = make_client(billing_enabled="true")
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/widget.js").headers["content-type"].startswith("application/javascript")
    assert client.get("/admin").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/legal").status_code == 200
    r = client.get("/terms", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/legal#terms"
    assert client.get("/favicon.ico").status_code == 200
    plans = client.get("/api/public/plans").json()["plans"]
    assert [p["id"] for p in plans] == ["free", "starter", "pro", "business"]


def test_self_hosted_root_redirects_to_admin(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/admin"
