from datetime import datetime

from app.services.invoices import add_months
from tests.conftest import signup


def _setup(make_client, **env):
    client = make_client(billing_enabled="true", superadmin_emails="boss@example.com",
                         legal_name="ი/მ Test Seller", seller_iban="GE00TB0000000000000000", **env)
    customer_ws = signup(client)  # customer
    client.post("/api/auth/logout")
    signup(client, "boss@example.com", name="Boss")
    return client, customer_ws


def test_invoice_paid_extends_plan_and_renewal_continues(make_client):
    client, ws_id = _setup(make_client)
    r = client.post(f"/api/platform/workspaces/{ws_id}/invoices", json={"plan": "pro", "months": 12, "buyer_tax_id": "123456789"})
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["number"].endswith("-0001") and inv["status"] == "issued"
    assert inv["amount"] == 129 * 10 and inv["currency"] == "GEL"  # 12 months for the price of 10

    listing = client.get("/api/platform/invoices").json()
    assert listing["outstanding"] == {"GEL": 1290.0} and listing["paid_this_month"] == {}

    page = client.get(f"/invoice/{inv['id']}")
    assert page.status_code == 200
    assert "GE00TB0000000000000000" in page.text and inv["number"] in page.text and "123456789" in page.text

    paid = client.post(f"/api/platform/invoices/{inv['id']}/paid").json()
    assert paid["status"] == "paid" and paid["period_end"]
    assert client.post(f"/api/platform/invoices/{inv['id']}/paid").status_code == 409
    listing = client.get("/api/platform/invoices").json()
    assert listing["paid_this_month"] == {"GEL": 1290.0} and listing["outstanding"] == {}

    ws = next(w for w in client.get("/api/platform/workspaces").json()["workspaces"] if w["id"] == ws_id)
    assert ws["plan"] == "pro" and ws["plan_source"] == "manual" and ws["expiring_soon"] is False

    # paying the next invoice early continues from the current end date
    second = client.post(f"/api/platform/workspaces/{ws_id}/invoices", json={"plan": "pro", "months": 1}).json()
    assert second["amount"] == 129
    renewed = client.post(f"/api/platform/invoices/{second['id']}/paid").json()
    assert renewed["period_end"] == add_months(datetime.fromisoformat(paid["period_end"][:-1]), 1).isoformat() + "Z"


def test_customer_sees_only_own_invoices(make_client):
    client, ws_id = _setup(make_client)
    inv = client.post(f"/api/platform/workspaces/{ws_id}/invoices", json={"plan": "starter", "currency": "USD"}).json()
    assert inv["amount"] == 19
    voided = client.post(f"/api/platform/workspaces/{ws_id}/invoices", json={"plan": "starter"}).json()
    assert client.post(f"/api/platform/invoices/{voided['id']}/void").json()["status"] == "void"

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": "owner@example.com", "password": "password123"})
    assert client.post(f"/api/platform/workspaces/{ws_id}/invoices", json={"plan": "pro"}).status_code == 403
    mine = client.get(f"/api/workspaces/{ws_id}/invoices").json()
    assert [i["id"] for i in mine] == [inv["id"]]
    assert client.get(f"/invoice/{inv['id']}").status_code == 200

    client.post("/api/auth/logout")
    signup(client, "stranger@example.com")
    assert client.get(f"/invoice/{inv['id']}").status_code == 404
    client.post("/api/auth/logout")
    r = client.get(f"/invoice/{inv['id']}", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/admin"


def test_invoice_page_escapes_html(make_client):
    client, ws_id = _setup(make_client)
    inv = client.post(f"/api/platform/workspaces/{ws_id}/invoices",
                      json={"plan": "pro", "buyer_name": "<script>alert(1)</script>"}).json()
    page = client.get(f"/invoice/{inv['id']}").text
    assert "<script>alert(1)" not in page and "&lt;script&gt;" in page


def test_signup_trial(make_client):
    client = make_client(billing_enabled="true", trial_days="14", superadmin_emails="boss@example.com")
    ws_id = signup(client)
    billing = client.get(f"/api/workspaces/{ws_id}/billing").json()
    assert billing["plan"]["id"] == "pro" and billing["plan_source"] == "trial" and billing["plan_expires_at"]
    client.post("/api/auth/logout")
    signup(client, "boss@example.com")
    data = client.get("/api/platform/workspaces").json()
    assert data["mrr_usd"] == 0 and data["paying"] == 0  # trials are not revenue


def test_add_months_clamps_day():
    assert add_months(datetime(2026, 1, 31), 1) == datetime(2026, 2, 28)
    assert add_months(datetime(2026, 11, 15), 3) == datetime(2027, 2, 15)
