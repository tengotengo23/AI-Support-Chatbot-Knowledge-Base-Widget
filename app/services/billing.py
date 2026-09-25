"""Paddle Billing integration for the hosted version.

Paddle is a "merchant of record": it charges the customer's card, handles VAT/sales tax and
invoices worldwide and pays you out (bank transfer / Payoneer / PayPal). This works for sellers
based in Georgia, unlike Stripe. For local customers you can also take bank transfers and set
the plan manually from the Platform page.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Workspace

ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def verify_signature(raw_body: bytes, header: str, secret: str, tolerance: int = 300) -> bool:
    """Paddle-Signature: ts=<unix>;h1=<hex hmac-sha256 of "<ts>:<raw body>">"""
    if not header or not secret:
        return False
    ts = ""
    signatures: list[str] = []
    for part in header.split(";"):
        key, _, value = part.strip().partition("=")
        if key == "ts":
            ts = value
        elif key == "h1":
            signatures.append(value)
    if not ts.isdigit() or not signatures:
        return False
    if abs(time.time() - int(ts)) > tolerance:
        return False
    expected = hmac.new(secret.encode(), ts.encode() + b":" + raw_body, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


def price_to_plan(settings: Settings) -> dict[str, str]:
    mapping = {
        settings.paddle_price_starter: "starter",
        settings.paddle_price_pro: "pro",
        settings.paddle_price_business: "business",
    }
    mapping.pop("", None)
    return mapping


def handle_event(db: Session, settings: Settings, event: dict) -> str:
    """Apply a Paddle webhook event. Returns a short description of what happened."""
    event_type = event.get("event_type", "")
    if not event_type.startswith("subscription."):
        return "ignored"
    data = event.get("data") or {}
    occurred_at = event.get("occurred_at") or ""
    custom = data.get("custom_data") or {}

    ws: Workspace | None = None
    ws_id = str(custom.get("workspace_id") or "")
    if ws_id.isdigit():
        ws = db.get(Workspace, int(ws_id))
    if ws is None and data.get("id"):
        ws = db.scalar(select(Workspace).where(Workspace.paddle_subscription_id == data["id"]))
    if ws is None:
        return "unknown workspace"

    # Paddle may deliver events out of order; ignore anything older than what we already applied.
    if ws.paddle_last_event_at and occurred_at and occurred_at < ws.paddle_last_event_at:
        return "stale"

    status = data.get("status", "")
    plan = None
    for item in data.get("items") or []:
        plan = price_to_plan(settings).get(((item.get("price") or {}).get("id")) or "")
        if plan:
            break

    ws.paddle_subscription_id = data.get("id") or ws.paddle_subscription_id
    ws.paddle_customer_id = data.get("customer_id") or ws.paddle_customer_id
    ws.paddle_status = status
    urls = data.get("management_urls") or {}
    ws.paddle_cancel_url = urls.get("cancel") or ws.paddle_cancel_url
    ws.paddle_update_url = urls.get("update_payment_method") or ws.paddle_update_url
    ws.paddle_last_event_at = occurred_at or ws.paddle_last_event_at

    if status in ACTIVE_STATUSES and plan:
        ws.plan, ws.plan_source, ws.plan_expires_at = plan, "paddle", None
        return f"plan={plan}"
    if status in {"canceled", "paused"} and ws.plan_source == "paddle":
        ws.plan, ws.plan_source = "free", "none"
        return "downgraded"
    return "updated"
