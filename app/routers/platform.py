"""Platform owner (superadmin) tools for the hosted version: see all customers and set plans
manually, e.g. after a local bank transfer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import get_db, utcnow
from app.models import Document, Invoice, User, Usage, Workspace
from app.routers.deps import csrf_guard, current_user, is_superadmin, settings_dep
from app.services import invoices, telegram

router = APIRouter(prefix="/api/platform", tags=["platform"], dependencies=[Depends(csrf_guard)])


def superadmin(
    user: User = Depends(current_user), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
) -> User:
    if not is_superadmin(user, db, settings):
        raise HTTPException(403, "Superadmin only")
    return user


@router.get("/workspaces")
def all_workspaces(
    _: User = Depends(superadmin), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
):
    period = plans.current_period()
    usage = dict(db.execute(select(Usage.workspace_id, Usage.ai_messages).where(Usage.period == period)).all())
    docs = dict(
        db.execute(select(Document.workspace_id, func.count(Document.id)).group_by(Document.workspace_id)).all()
    )
    rows = db.execute(select(Workspace, User.email).join(User, User.id == Workspace.owner_id).order_by(Workspace.id.desc())).all()
    mrr = 0
    paying = 0
    soon = utcnow() + timedelta(days=7)
    out = []
    for ws, email in rows:
        plan = plans.effective_plan(ws, settings)
        is_paying = plan.price_usd > 0 and ws.plan_source != "trial"
        if is_paying:
            mrr += plan.price_usd
            paying += 1
        out.append(
            {
                "id": ws.id,
                "name": ws.name,
                "owner_email": email,
                "plan": plan.id,
                "plan_source": ws.plan_source,
                "plan_expires_at": ws.plan_expires_at.isoformat() + "Z" if ws.plan_expires_at else None,
                # Renewal reminder: a paid or trial plan that ends within a week.
                "expiring_soon": bool(
                    plan.price_usd > 0 and ws.plan_expires_at and ws.plan_expires_at <= soon
                ),
                "paddle_status": ws.paddle_status,
                "ai_messages": usage.get(ws.id, 0),
                "documents": docs.get(ws.id, 0),
                "telegram": bool(ws.telegram_chat_id),
                "created_at": ws.created_at.isoformat() + "Z",
            }
        )
    return {"mrr_usd": mrr, "paying": paying, "workspaces": out}


class PlanIn(BaseModel):
    plan: str = Field(pattern=r"^(free|starter|pro|business)$")
    expires_at: datetime | None = None


@router.post("/workspaces/{ws_id}/plan")
def set_plan(
    ws_id: int, body: PlanIn, _: User = Depends(superadmin), db: Session = Depends(get_db)
):
    ws = db.get(Workspace, ws_id)
    if ws is None:
        raise HTTPException(404, "Workspace not found")
    ws.plan = body.plan
    ws.plan_source = "manual" if body.plan != "free" else "none"
    expires = body.expires_at
    if expires is not None and expires.tzinfo is not None:
        expires = expires.astimezone(timezone.utc).replace(tzinfo=None)
    ws.plan_expires_at = expires
    db.commit()
    return {"ok": True}


# --- bank-transfer invoices -------------------------------------------------------------------


class InvoiceIn(BaseModel):
    plan: Literal["starter", "pro", "business"]
    months: int = Field(default=1, ge=1, le=36)
    currency: Literal["GEL", "USD", "EUR"] = "GEL"
    amount: float | None = Field(default=None, ge=0, le=1_000_000)
    buyer_name: str = Field(default="", max_length=200)
    buyer_tax_id: str = Field(default="", max_length=64)
    buyer_email: str = Field(default="", max_length=320)
    note: str = Field(default="", max_length=1000)


@router.post("/workspaces/{ws_id}/invoices")
def create_invoice(
    ws_id: int,
    body: InvoiceIn,
    background: BackgroundTasks,
    _: User = Depends(superadmin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    ws = db.get(Workspace, ws_id)
    if ws is None:
        raise HTTPException(404, "Workspace not found")
    if body.amount is None and body.currency == "EUR":
        raise HTTPException(400, "Enter the amount for EUR invoices")
    inv = invoices.create(db, settings, ws, **body.model_dump())
    db.commit()
    background.add_task(telegram.notify_invoice, settings, inv.id)
    return invoices.to_dict(inv, settings)


@router.get("/invoices")
def list_invoices(
    _: User = Depends(superadmin), db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
):
    rows = db.scalars(select(Invoice).order_by(Invoice.id.desc()).limit(500)).all()
    return {**invoices.summary(db), "invoices": [invoices.to_dict(i, settings) for i in rows]}


def _issued_invoice(db: Session, invoice_id: int) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise HTTPException(404, "Invoice not found")
    if inv.status != "issued":
        raise HTTPException(409, f"Invoice is already {inv.status}")
    return inv


@router.post("/invoices/{invoice_id}/paid")
def invoice_paid(
    invoice_id: int,
    background: BackgroundTasks,
    _: User = Depends(superadmin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    inv = _issued_invoice(db, invoice_id)
    invoices.mark_paid(db, inv)
    db.commit()
    background.add_task(telegram.notify_invoice, settings, inv.id)
    return invoices.to_dict(inv, settings)


@router.post("/invoices/{invoice_id}/void")
def invoice_void(
    invoice_id: int,
    _: User = Depends(superadmin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    inv = _issued_invoice(db, invoice_id)
    inv.status = "void"
    db.commit()
    return invoices.to_dict(inv, settings)
