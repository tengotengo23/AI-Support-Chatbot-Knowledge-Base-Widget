"""Public API used by the embeddable widget (widget.js). Authenticated by the workspace public key
plus a random visitor id that only the visitor's browser knows."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import get_db
from app.i18n import STRINGS, normalize_lang, t
from app.models import Conversation, Lead, Workspace
from app.routers.deps import client_ip, settings_dep
from app.security import rate_limiter
from app.services import chat, telegram

router = APIRouter(prefix="/api/widget/{public_key}", tags=["widget"])

VISITOR_PATTERN = r"^[A-Za-z0-9_-]{16,64}$"


def widget_workspace(
    public_key: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> Workspace:
    ws = db.scalar(select(Workspace).where(Workspace.public_key == public_key))
    if ws is None:
        raise HTTPException(404, "Unknown widget key")
    allowed = ws.origin_list()
    origin = (request.headers.get("origin") or "").rstrip("/")
    if allowed and origin and origin not in allowed and origin != settings.public_url:
        raise HTTPException(403, "This website is not allowed to use this widget")
    return ws


def _conversation(db: Session, ws: Workspace, conv_id: int | None, visitor_id: str) -> Conversation | None:
    if not conv_id:
        return None
    conv = db.get(Conversation, conv_id)
    if conv is None or conv.workspace_id != ws.id or not hmac.compare_digest(conv.visitor_id, visitor_id):
        return None
    return conv


@router.get("/config")
def config(ws: Workspace = Depends(widget_workspace), settings: Settings = Depends(settings_dep)):
    strings = {lang: dict(values) for lang, values in STRINGS.items()}
    if ws.welcome_message.strip():
        strings[ws.default_language]["welcome"] = ws.welcome_message.strip()
    return {
        "name": ws.name,
        "bot_name": ws.bot_name,
        "brand_color": ws.brand_color,
        "default_language": ws.default_language,
        "lead_capture_enabled": ws.lead_capture_enabled,
        "handoff_enabled": ws.handoff_enabled,
        "show_badge": plans.show_badge(ws, settings),
        "badge_text": settings.brand_name,
        "badge_url": settings.badge_url,
        "strings": strings,
    }


class VisitorIn(BaseModel):
    visitor_id: str = Field(pattern=VISITOR_PATTERN)
    conversation_id: int | None = None
    lang: str | None = Field(None, max_length=5)  # the widget's UI language


class MessageIn(VisitorIn):
    text: str = Field(min_length=1, max_length=2000)
    page_url: str | None = Field(None, max_length=1000)


@router.post("/messages")
def send_message(
    body: MessageIn,
    request: Request,
    background: BackgroundTasks,
    ws: Workspace = Depends(widget_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    limit = settings.widget_rate_limit_per_minute
    if not rate_limiter.allow(f"w:{ws.id}:{client_ip(request)}", limit) or not rate_limiter.allow(
        f"v:{body.visitor_id}", limit
    ):
        raise HTTPException(429, "Too many messages, please wait a moment")
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Empty message")

    conv = _conversation(db, ws, body.conversation_id, body.visitor_id)
    if conv is None:
        conv = Conversation(
            workspace_id=ws.id,
            visitor_id=body.visitor_id,
            language=normalize_lang(body.lang, ws.default_language),
            page_url=(body.page_url or "")[:1000],
        )
        db.add(conv)
        db.flush()

    result = chat.handle_visitor_message(db, ws, conv, text, settings)
    db.commit()
    if conv.status == "handoff":
        background.add_task(telegram.forward_visitor_message, settings, conv.id, text)
    return {
        "conversation_id": conv.id,
        **result,
        "suggest_handoff": result.get("answered") is False and ws.handoff_enabled,
    }


@router.get("/conversations/{conv_id}")
def poll(
    conv_id: int,
    visitor_id: str = Query(pattern=VISITOR_PATTERN),
    after: int = Query(0, ge=0),
    ws: Workspace = Depends(widget_workspace),
    db: Session = Depends(get_db),
):
    conv = _conversation(db, ws, conv_id, visitor_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return {"status": conv.status, "messages": chat.get_messages_after(db, conv, after)}


@router.post("/handoff")
def handoff(
    body: VisitorIn,
    background: BackgroundTasks,
    ws: Workspace = Depends(widget_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    if not ws.handoff_enabled:
        raise HTTPException(400, "Human handoff is disabled")
    conv = _conversation(db, ws, body.conversation_id, body.visitor_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    lang = normalize_lang(body.lang, conv.language or ws.default_language)
    available = bool(ws.telegram_chat_id and settings.telegram_bot_token)
    if available:
        already = conv.status == "handoff"
        conv.status = "handoff"
        msg = chat.add_message(db, conv, "system", t(lang, "handoff_started"))
        db.commit()
        if not already:
            background.add_task(telegram.notify_handoff, settings, conv.id)
    else:
        msg = chat.add_message(db, conv, "system", t(lang, "handoff_unavailable"))
        db.commit()
    return {"status": conv.status, "available": available, "messages": [chat.message_dict(msg)]}


class LeadIn(VisitorIn):
    name: str = Field("", max_length=200)
    phone: str = Field("", max_length=64)
    email: str = Field("", max_length=320)
    note: str = Field("", max_length=2000)


@router.post("/leads")
def create_lead(
    body: LeadIn,
    request: Request,
    background: BackgroundTasks,
    ws: Workspace = Depends(widget_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    if not rate_limiter.allow(f"lead:{ws.id}:{client_ip(request)}", 5, 600):
        raise HTTPException(429, "Too many requests")
    conv = _conversation(db, ws, body.conversation_id, body.visitor_id)
    lang = normalize_lang(body.lang, (conv.language if conv else None) or ws.default_language)
    if not body.phone.strip() and not body.email.strip():
        raise HTTPException(400, t(lang, "lead_invalid"))
    lead = Lead(
        workspace_id=ws.id,
        conversation_id=conv.id if conv else None,
        name=body.name.strip(),
        phone=body.phone.strip(),
        email=body.email.strip(),
        note=body.note.strip(),
    )
    db.add(lead)
    messages = []
    if conv is not None:
        messages.append(chat.message_dict(chat.add_message(db, conv, "system", t(lang, "lead_thanks"))))
    db.commit()
    background.add_task(telegram.notify_lead, settings, lead.id)
    return {"ok": True, "messages": messages}
