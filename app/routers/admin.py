"""Admin API used by the dashboard (/admin). All routes require a logged-in owner."""

from __future__ import annotations

import csv
import io
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import get_db, utcnow
from app.i18n import t
from app.models import (
    Conversation,
    Document,
    Lead,
    Message,
    User,
    Workspace,
    new_connect_code,
    new_public_key,
)
from app.routers.deps import csrf_guard, current_user, owned_workspace, settings_dep
from app.security import rate_limiter
from app.services import analytics, chat, ingest, telegram
from app.services.ingest import IngestError
from app.services.netguard import UnsafeURLError, validate_url

router = APIRouter(prefix="/api", tags=["admin"], dependencies=[Depends(csrf_guard)])

LANG_PATTERN = r"^(ka|en|ru)$"


# --- workspaces ---------------------------------------------------------------------------------


def workspace_dict(ws: Workspace, db: Session, settings: Settings) -> dict:
    plan = plans.effective_plan(ws, settings)
    username = telegram.bot_username(settings) if settings.telegram_bot_token else None
    return {
        "id": ws.id,
        "name": ws.name,
        "public_key": ws.public_key,
        "bot_name": ws.bot_name,
        "welcome_message": ws.welcome_message,
        "company_info": ws.company_info,
        "brand_color": ws.brand_color,
        "default_language": ws.default_language,
        "lead_capture_enabled": ws.lead_capture_enabled,
        "handoff_enabled": ws.handoff_enabled,
        "allowed_origins": ws.allowed_origins,
        "embed_code": f'<script src="{settings.public_url}/widget.js" data-key="{ws.public_key}" async></script>',
        "telegram": {
            "available": bool(settings.telegram_bot_token),
            "connected": bool(ws.telegram_chat_id),
            "bot_username": username,
            "connect_code": ws.telegram_connect_code,
            "connect_link": f"https://t.me/{username}?start={ws.telegram_connect_code}" if username else None,
        },
        "plan": plan.public(),
        "usage": {"ai_messages": plans.get_usage(db, ws), "period": plans.current_period()},
        "document_count": _doc_count(db, ws),
        "open_handoffs": db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.workspace_id == ws.id, Conversation.status == "handoff"
            )
        ) or 0,
    }


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    bot_name: str | None = Field(None, min_length=1, max_length=100)
    welcome_message: str | None = Field(None, max_length=1000)
    company_info: str | None = Field(None, max_length=8000)
    brand_color: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    default_language: str | None = Field(None, pattern=LANG_PATTERN)
    lead_capture_enabled: bool | None = None
    handoff_enabled: bool | None = None
    allowed_origins: str | None = Field(None, max_length=2000)


@router.post("/workspaces")
def create_workspace(
    body: WorkspaceCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    count = db.scalar(select(func.count(Workspace.id)).where(Workspace.owner_id == user.id))
    if count >= 20:
        raise HTTPException(400, "Workspace limit reached")
    ws = Workspace(owner_id=user.id, name=body.name.strip())
    db.add(ws)
    db.commit()
    return workspace_dict(ws, db, settings)


@router.get("/workspaces/{ws_id}")
def get_workspace(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    return workspace_dict(ws, db, settings)


@router.patch("/workspaces/{ws_id}")
def update_workspace(
    body: WorkspaceUpdate,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    for key, value in body.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if key == "allowed_origins":
            value = ",".join(o.strip().rstrip("/") for o in value.replace("\n", ",").split(",") if o.strip())
        setattr(ws, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    return workspace_dict(ws, db, settings)


@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    db.delete(ws)
    db.commit()
    return {"ok": True}


@router.post("/workspaces/{ws_id}/rotate-key")
def rotate_key(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    ws.public_key = new_public_key()
    db.commit()
    return workspace_dict(ws, db, settings)


# --- telegram -----------------------------------------------------------------------------------


@router.post("/workspaces/{ws_id}/telegram/disconnect")
def telegram_disconnect(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    ws.telegram_chat_id = None
    ws.telegram_connect_code = new_connect_code()
    db.commit()
    return workspace_dict(ws, db, settings)


@router.post("/workspaces/{ws_id}/telegram/test")
def telegram_test(ws: Workspace = Depends(owned_workspace), settings: Settings = Depends(settings_dep)):
    if not ws.telegram_chat_id:
        raise HTTPException(400, "Telegram is not connected")
    try:
        telegram.send(settings, ws.telegram_chat_id, f"✅ Test message from {settings.brand_name} ({ws.name})")
    except telegram.TelegramError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"ok": True}


# --- knowledge base -----------------------------------------------------------------------------


def _doc_dict(d: Document) -> dict:
    return {
        "id": d.id,
        "kind": d.kind,
        "title": d.title,
        "source": d.source,
        "char_count": d.char_count,
        "preview": d.content[:300],
        "created_at": d.created_at.isoformat() + "Z",
    }


def _doc_count(db: Session, ws: Workspace) -> int:
    return db.scalar(select(func.count(Document.id)).where(Document.workspace_id == ws.id)) or 0


def _remaining_docs(db: Session, ws: Workspace, settings: Settings) -> int | None:
    plan = plans.effective_plan(ws, settings)
    if plan.documents <= 0:
        return None
    remaining = plan.documents - _doc_count(db, ws)
    if remaining <= 0:
        raise HTTPException(
            402, f"Your {plan.name} plan allows {plan.documents} knowledge sources. Upgrade to add more."
        )
    return remaining


@router.get("/workspaces/{ws_id}/documents")
def list_documents(ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    docs = db.scalars(
        select(Document).where(Document.workspace_id == ws.id).order_by(Document.id.desc())
    ).all()
    return [_doc_dict(d) for d in docs]


@router.post("/workspaces/{ws_id}/documents/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    _remaining_docs(db, ws, settings)
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
    name = file.filename or "document.pdf"
    try:
        text = ingest.extract_pdf(data)
        doc = ingest.add_document(db, ws, settings, kind="pdf", title=name, source=name, text=text)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.commit()
    return _doc_dict(doc)


class UrlIn(BaseModel):
    url: str = Field(max_length=2000)
    crawl: bool = False
    max_pages: int = Field(10, ge=1, le=500)


@router.post("/workspaces/{ws_id}/documents/url")
def import_url(
    body: UrlIn,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    remaining = _remaining_docs(db, ws, settings)
    url = body.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        validate_url(url, settings.allow_private_urls)
    except UnsafeURLError as exc:
        raise HTTPException(400, str(exc)) from exc
    plan = plans.effective_plan(ws, settings)
    max_pages = body.max_pages if body.crawl else 1
    max_pages = min(max_pages, plan.crawl_pages or settings.max_crawl_pages, settings.max_crawl_pages)
    if remaining is not None:
        max_pages = min(max_pages, remaining)
    try:
        pages = ingest.crawl(url, max_pages, settings.allow_private_urls)
        docs = [
            ingest.add_document(db, ws, settings, kind="url", title=title, source=page_url, text=text)
            for page_url, title, text in pages
        ]
    except (IngestError, UnsafeURLError) as exc:
        raise HTTPException(400, str(exc)) from exc
    db.commit()
    return [_doc_dict(d) for d in docs]


class TextIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=200_000)


@router.post("/workspaces/{ws_id}/documents/text")
def add_text(
    body: TextIn,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    _remaining_docs(db, ws, settings)
    try:
        doc = ingest.add_document(db, ws, settings, kind="text", title=body.title, source="", text=body.content)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.commit()
    return _doc_dict(doc)


class FaqIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=10_000)


@router.post("/workspaces/{ws_id}/documents/faq")
def add_faq(
    body: FaqIn,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    _remaining_docs(db, ws, settings)
    doc = ingest.add_document(
        db, ws, settings, kind="faq", title=body.question.strip(), source="",
        text=ingest.faq_text(body.question, body.answer), chunk=False,
    )
    db.commit()
    return _doc_dict(doc)


def _get_doc(db: Session, ws: Workspace, doc_id: int) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.workspace_id != ws.id:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/workspaces/{ws_id}/documents/{doc_id}")
def delete_document(doc_id: int, ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    db.delete(_get_doc(db, ws, doc_id))
    ws.kb_version = (ws.kb_version or 0) + 1
    db.commit()
    return {"ok": True}


@router.post("/workspaces/{ws_id}/documents/{doc_id}/refresh")
def refresh_document(
    doc_id: int,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    doc = _get_doc(db, ws, doc_id)
    if doc.kind != "url":
        raise HTTPException(400, "Only website pages can be refreshed")
    try:
        (page_url, title, text), = ingest.crawl(doc.source, 1, settings.allow_private_urls)
    except (IngestError, UnsafeURLError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    db.delete(doc)
    db.flush()
    new_doc = ingest.add_document(db, ws, settings, kind="url", title=title, source=page_url, text=text)
    db.commit()
    return _doc_dict(new_doc)


class TestChatIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/workspaces/{ws_id}/test-chat")
def test_chat(
    body: TestChatIn,
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    """Playground: ask the bot without creating a conversation."""
    if not rate_limiter.allow(f"test:{ws.id}", 30, 60):
        raise HTTPException(429, "Too many requests")
    if plans.quota_exceeded(db, ws, settings):
        raise HTTPException(402, "Monthly AI answer limit reached. Upgrade your plan.")
    answer = chat.answer_question(db, ws, body.text, settings)
    if answer.kind != "small_talk":
        plans.increment_usage(db, ws)
    db.commit()
    return {"text": answer.text, "answered": answer.answered, "kind": answer.kind, "sources": answer.sources}


# --- conversations ------------------------------------------------------------------------------


def _get_conv(db: Session, ws: Workspace, conv_id: int) -> Conversation:
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.workspace_id != ws.id:
        raise HTTPException(404, "Conversation not found")
    return conv


@router.get("/workspaces/{ws_id}/conversations")
def list_conversations(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    status: str | None = Query(None, pattern=r"^(bot|handoff)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    q = select(Conversation).where(Conversation.workspace_id == ws.id)
    if status:
        q = q.where(Conversation.status == status)
    convs = db.scalars(q.order_by(Conversation.updated_at.desc()).limit(limit).offset(offset)).all()
    ids = [c.id for c in convs]
    last: dict[int, Message] = {}
    counts: dict[int, int] = {}
    if ids:
        stats = db.execute(
            select(Message.conversation_id, func.max(Message.id), func.count(Message.id))
            .where(Message.conversation_id.in_(ids))
            .group_by(Message.conversation_id)
        ).all()
        counts = {cid: n for cid, _, n in stats}
        for m in db.scalars(select(Message).where(Message.id.in_([mid for _, mid, _ in stats]))):
            last[m.conversation_id] = m
    return [
        {
            "id": c.id,
            "status": c.status,
            "language": c.language,
            "page_url": c.page_url,
            "created_at": c.created_at.isoformat() + "Z",
            "updated_at": c.updated_at.isoformat() + "Z",
            "message_count": counts.get(c.id, 0),
            "last_message": (
                {"role": last[c.id].role, "content": last[c.id].content[:200]} if c.id in last else None
            ),
        }
        for c in convs
    ]


@router.get("/workspaces/{ws_id}/conversations/{conv_id}")
def get_conversation(conv_id: int, ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    conv = _get_conv(db, ws, conv_id)
    lead = db.scalar(select(Lead).where(Lead.conversation_id == conv.id).order_by(Lead.id.desc()))
    return {
        "id": conv.id,
        "status": conv.status,
        "language": conv.language,
        "page_url": conv.page_url,
        "created_at": conv.created_at.isoformat() + "Z",
        "messages": [
            {**chat.message_dict(m), "answered": m.answered} for m in conv.messages
        ],
        "lead": _lead_dict(lead) if lead else None,
    }


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


@router.post("/workspaces/{ws_id}/conversations/{conv_id}/reply")
def reply_conversation(
    conv_id: int, body: ReplyIn, ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)
):
    conv = _get_conv(db, ws, conv_id)
    conv.status = "handoff"
    msg = chat.add_message(db, conv, "operator", body.text.strip())
    db.commit()
    return chat.message_dict(msg)


@router.post("/workspaces/{ws_id}/conversations/{conv_id}/close")
def close_conversation(conv_id: int, ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    conv = _get_conv(db, ws, conv_id)
    if conv.status == "handoff":
        conv.status = "bot"
        chat.add_message(db, conv, "system", t(conv.language, "handoff_back_to_bot"))
    db.commit()
    return {"ok": True}


# --- leads --------------------------------------------------------------------------------------


def _lead_dict(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "conversation_id": lead.conversation_id,
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "note": lead.note,
        "status": lead.status,
        "value": lead.value,
        "created_at": lead.created_at.isoformat() + "Z",
    }


@router.get("/workspaces/{ws_id}/leads")
def list_leads(ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    leads = db.scalars(select(Lead).where(Lead.workspace_id == ws.id).order_by(Lead.id.desc()).limit(500)).all()
    return [_lead_dict(lead) for lead in leads]


class LeadUpdate(BaseModel):
    status: str | None = Field(None, pattern=r"^(new|contacted|won|lost)$")
    value: float | None = Field(None, ge=0, le=100_000_000)


@router.patch("/workspaces/{ws_id}/leads/{lead_id}")
def update_lead(
    lead_id: int, body: LeadUpdate, ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)
):
    lead = db.get(Lead, lead_id)
    if lead is None or lead.workspace_id != ws.id:
        raise HTTPException(404, "Lead not found")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"]:
        lead.status = data["status"]
    if "value" in data:
        lead.value = data["value"]
    lead.updated_at = utcnow()
    db.commit()
    return _lead_dict(lead)


def _csv_safe(value) -> str:
    """Prevent spreadsheet formula injection from visitor-supplied values."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@router.get("/workspaces/{ws_id}/leads.csv")
def export_leads(ws: Workspace = Depends(owned_workspace), db: Session = Depends(get_db)):
    leads = db.scalars(select(Lead).where(Lead.workspace_id == ws.id).order_by(Lead.id)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "created_at", "name", "phone", "email", "note", "status", "value", "conversation_id"])
    for lead in leads:
        writer.writerow(
            [lead.id, lead.created_at.isoformat(), *(_csv_safe(v) for v in (lead.name, lead.phone, lead.email, lead.note)),
             lead.status, lead.value if lead.value is not None else "", lead.conversation_id or ""]
        )
    return StreamingResponse(
        iter(["﻿" + buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="leads-{ws.id}.csv"'},
    )


# --- analytics & billing ------------------------------------------------------------------------


@router.get("/workspaces/{ws_id}/analytics")
def get_analytics(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    return analytics.summary(db, ws, days)


@router.get("/workspaces/{ws_id}/billing")
def get_billing(
    ws: Workspace = Depends(owned_workspace),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    plan = plans.effective_plan(ws, settings)
    since = utcnow() - timedelta(days=30)
    won_value = db.scalar(
        select(func.coalesce(func.sum(Lead.value), 0.0)).where(
            Lead.workspace_id == ws.id, Lead.status == "won", Lead.updated_at >= since
        )
    ) or 0.0
    prices = {
        "starter": settings.paddle_price_starter,
        "pro": settings.paddle_price_pro,
        "business": settings.paddle_price_business,
    }
    return {
        "billing_enabled": settings.billing_enabled,
        "contact_email": settings.contact_email,
        "plan": plan.public(),
        "plan_source": ws.plan_source,
        "plan_expires_at": ws.plan_expires_at.isoformat() + "Z" if ws.plan_expires_at else None,
        "usage": {"ai_messages": plans.get_usage(db, ws), "documents": _doc_count(db, ws)},
        "plans": [p.public() for p in plans.PLANS.values()],
        "paddle": {
            "enabled": bool(settings.paddle_client_token and any(prices.values())),
            "environment": settings.paddle_env,
            "client_token": settings.paddle_client_token,
            "prices": prices,
            "customer_email": user.email,
            "status": ws.paddle_status,
            "cancel_url": ws.paddle_cancel_url,
            "update_payment_url": ws.paddle_update_url,
        },
        "platform_fee": {
            "percent": settings.platform_fee_percent,
            "won_value_30d": round(float(won_value), 2),
            "fee_30d": round(float(won_value) * settings.platform_fee_percent / 100, 2),
        },
    }
