"""Inbound webhooks: Paddle (billing) and Telegram (operator replies)."""

from __future__ import annotations

import hmac
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.routers.deps import settings_dep
from app.services import billing, telegram

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["webhooks"])


@router.post("/billing/paddle/webhook")
async def paddle_webhook(
    request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
):
    raw = await request.body()
    if not billing.verify_signature(raw, request.headers.get("paddle-signature", ""), settings.paddle_webhook_secret):
        raise HTTPException(401, "Invalid signature")
    try:
        event = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(400, "Invalid JSON") from exc
    result = billing.handle_event(db, settings, event)
    db.commit()
    log.info("paddle %s -> %s", event.get("event_type"), result)
    return {"ok": True, "result": result}


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
):
    secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not settings.telegram_webhook_secret or not hmac.compare_digest(secret, settings.telegram_webhook_secret):
        raise HTTPException(401, "Invalid secret")
    try:
        update = await request.json()
    except ValueError as exc:
        raise HTTPException(400, "Invalid JSON") from exc
    try:
        telegram.handle_update(db, settings, update)
        db.commit()
    except telegram.TelegramError as exc:
        log.warning("%s", exc)
        db.rollback()
    return {"ok": True}
