"""Hosted plans and usage limits.

Self-hosted installs (BILLING_ENABLED=false) are never limited: everything is free and
unlimited, forever. Limits below only apply to the paid hosted cloud version.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.config import Settings
from app.db import utcnow
from app.models import Usage, Workspace


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_usd: int
    ai_messages: int  # AI answers per month (0 = unlimited)
    documents: int  # knowledge sources (0 = unlimited)
    crawl_pages: int  # pages per website import
    remove_badge: bool
    features: tuple[str, ...]

    def public(self) -> dict:
        data = asdict(self)
        data["features"] = list(self.features)
        return data


PLANS: dict[str, Plan] = {
    "free": Plan(
        "free", "Free", 0, 100, 5, 5, False,
        ("Website chat widget", "Georgian / English / Russian", "Telegram handoff", "Basic analytics"),
    ),
    "starter": Plan(
        "starter", "Starter", 19, 1_000, 25, 30, False,
        ("Everything in Free", "1,000 AI answers / month", "25 knowledge sources", "Lead capture + CSV export"),
    ),
    "pro": Plan(
        "pro", "Pro", 49, 5_000, 100, 100, True,
        ("Everything in Starter", "5,000 AI answers / month", "Remove branding", "Priority email support"),
    ),
    "business": Plan(
        "business", "Business", 99, 20_000, 500, 300, True,
        ("Everything in Pro", "20,000 AI answers / month", "500 knowledge sources", "Setup help & onboarding call"),
    ),
}

SELF_HOSTED = Plan("self_hosted", "Self-hosted", 0, 0, 0, 0, True, ("Unlimited",))
PAID_PLAN_IDS = ("starter", "pro", "business")


def effective_plan(ws: Workspace, settings: Settings) -> Plan:
    if not settings.billing_enabled:
        return SELF_HOSTED
    if ws.plan_expires_at is not None and ws.plan_expires_at < utcnow():
        return PLANS["free"]
    return PLANS.get(ws.plan, PLANS["free"])


def current_period() -> str:
    return utcnow().strftime("%Y-%m")


def get_usage(db: Session, ws: Workspace) -> int:
    row = db.get(Usage, (ws.id, current_period()))
    return row.ai_messages if row else 0


def increment_usage(db: Session, ws: Workspace) -> None:
    row = db.get(Usage, (ws.id, current_period()))
    if row is None:
        row = Usage(workspace_id=ws.id, period=current_period(), ai_messages=0)
        db.add(row)
    row.ai_messages += 1


def quota_exceeded(db: Session, ws: Workspace, settings: Settings) -> bool:
    plan = effective_plan(ws, settings)
    return plan.ai_messages > 0 and get_usage(db, ws) >= plan.ai_messages


def show_badge(ws: Workspace, settings: Settings) -> bool:
    """Small "Powered by" link in the widget. Self-hosters can switch it off with SHOW_BADGE=false;
    on the hosted version it is removed on plans that include "Remove branding"."""
    if not settings.show_badge:
        return False
    if not settings.billing_enabled:
        return True
    return not effective_plan(ws, settings).remove_badge
