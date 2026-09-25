"""Telegram handoff.

Flow: the business owner opens a deep link (t.me/<bot>?start=<code>) which links their chat to
a workspace. When a visitor asks for a human (or leaves a lead), the bot posts the chat to
Telegram. The owner *replies* to that Telegram message and the reply shows up in the website
widget. Replying with /done hands the conversation back to the AI.
"""

from __future__ import annotations

import logging
import threading

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import SessionLocal
from app.i18n import t
from app.models import Conversation, Invoice, Lead, TelegramLink, Workspace, new_connect_code
from app.services import chat

log = logging.getLogger(__name__)

_bot_username: str | None = None


class TelegramError(RuntimeError):
    pass


def api(settings: Settings, method: str, payload: dict | None = None, timeout: float = 15.0) -> dict:
    if not settings.telegram_bot_token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not set")
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}",
            json=payload or {},
            timeout=timeout,
        )
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TelegramError(f"Telegram {method} failed: {exc}") from exc
    if not data.get("ok"):
        raise TelegramError(f"Telegram {method} error: {data.get('description')}")
    return data.get("result")


def bot_username(settings: Settings) -> str | None:
    global _bot_username
    if _bot_username is None and settings.telegram_bot_token:
        try:
            _bot_username = api(settings, "getMe").get("username")
        except TelegramError as exc:
            log.warning("%s", exc)
    return _bot_username


def send(settings: Settings, chat_id: str, text: str, reply_to: int | None = None) -> int:
    payload: dict = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if reply_to:
        payload["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    return int(api(settings, "sendMessage", payload)["message_id"])


def _link(db: Session, ws: Workspace, conv: Conversation, message_id: int) -> None:
    db.add(
        TelegramLink(
            workspace_id=ws.id,
            conversation_id=conv.id,
            chat_id=str(ws.telegram_chat_id),
            telegram_message_id=message_id,
        )
    )


def _transcript(conv: Conversation, limit: int = 8) -> str:
    labels = {"user": "👤", "assistant": "🤖", "operator": "🧑‍💼"}
    lines = [
        f"{labels[m.role]} {m.content[:500]}" for m in conv.messages[-limit:] if m.role in labels
    ]
    return "\n".join(lines)


# --- outgoing notifications (run as background tasks with their own DB session) ---------------


def _with_session(fn):
    def wrapper(*args, **kwargs):
        db = SessionLocal()
        try:
            fn(db, *args, **kwargs)
            db.commit()
        except TelegramError as exc:
            log.warning("%s", exc)
            db.rollback()
        except Exception:  # noqa: BLE001
            log.exception("telegram notification failed")
            db.rollback()
        finally:
            db.close()

    return wrapper


@_with_session
def notify_handoff(db: Session, settings: Settings, conversation_id: int) -> None:
    conv = db.get(Conversation, conversation_id)
    ws = db.get(Workspace, conv.workspace_id) if conv else None
    if not ws or not ws.telegram_chat_id:
        return
    text = (
        f"🙋 {ws.name}: a visitor wants a human (chat #{conv.id}, {conv.language.upper()})\n"
        f"{conv.page_url}\n\n{_transcript(conv)}\n\n"
        "↩️ Reply to this message to answer. Reply /done to hand the chat back to the AI."
    )
    _link(db, ws, conv, send(settings, ws.telegram_chat_id, text))


@_with_session
def forward_visitor_message(db: Session, settings: Settings, conversation_id: int, text: str) -> None:
    conv = db.get(Conversation, conversation_id)
    ws = db.get(Workspace, conv.workspace_id) if conv else None
    if not ws or not ws.telegram_chat_id:
        return
    _link(db, ws, conv, send(settings, ws.telegram_chat_id, f"💬 #{conv.id}: {text}"))


@_with_session
def notify_lead(db: Session, settings: Settings, lead_id: int) -> None:
    lead = db.get(Lead, lead_id)
    ws = db.get(Workspace, lead.workspace_id) if lead else None
    if not ws or not ws.telegram_chat_id:
        return
    parts = [f"📇 {ws.name}: new lead"]
    for label, value in (("Name", lead.name), ("Phone", lead.phone), ("Email", lead.email), ("Note", lead.note)):
        if value:
            parts.append(f"{label}: {value}")
    message_id = send(settings, ws.telegram_chat_id, "\n".join(parts))
    if lead.conversation_id:
        conv = db.get(Conversation, lead.conversation_id)
        if conv:
            _link(db, ws, conv, message_id)


@_with_session
def notify_invoice(db: Session, settings: Settings, invoice_id: int) -> None:
    """Tell the customer about a new invoice or a confirmed payment."""
    from app.services.invoices import money  # local import: invoices imports nothing from here

    inv = db.get(Invoice, invoice_id)
    ws = db.get(Workspace, inv.workspace_id) if inv and inv.workspace_id else None
    if not ws or not ws.telegram_chat_id:
        return
    link = f"{settings.public_url}/invoice/{inv.id}"
    if inv.status == "paid":
        until = f"{inv.period_end:%d.%m.%Y}" if inv.period_end else ""
        text = (f"✅ {ws.name}: გადახდა მიღებულია / payment received ({inv.number}).\n"
                f"პაკეტი / plan: {inv.plan}, ვადა / until {until}. მადლობა! / Thank you!")
    else:
        text = (f"🧾 {ws.name}: ახალი ინვოისი / new invoice {inv.number}\n"
                f"{money(inv.amount, inv.currency)} · {inv.plan} · {inv.months} თვე / month(s)\n"
                f"გადახდის ვადა / due: {inv.due_at:%d.%m.%Y}\n{link}")
    send(settings, ws.telegram_chat_id, text)


# --- incoming updates -------------------------------------------------------------------------


HELP = (
    "This bot forwards website chats to you.\n"
    "• Open the link from your admin panel (Settings → Telegram) to connect a website.\n"
    "• Reply to a forwarded chat message to answer the visitor.\n"
    "• Reply /done to hand the chat back to the AI assistant."
)


def handle_update(db: Session, settings: Settings, update: dict) -> None:
    msg = update.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id") or "")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return

    if text.startswith("/start"):
        code = text.split(maxsplit=1)[1].strip() if " " in text else ""
        ws = db.scalar(select(Workspace).where(Workspace.telegram_connect_code == code)) if code else None
        if ws is None:
            send(settings, chat_id, HELP)
            return
        ws.telegram_chat_id = chat_id
        ws.telegram_connect_code = new_connect_code()  # one-time code
        db.commit()
        send(settings, chat_id, f"✅ Connected to “{ws.name}”. Website chats that need a human will appear here.")
        return

    reply_to = msg.get("reply_to_message") or {}
    if not reply_to:
        send(settings, chat_id, HELP)
        return

    link = db.scalar(
        select(TelegramLink).where(
            TelegramLink.chat_id == chat_id, TelegramLink.telegram_message_id == reply_to.get("message_id")
        )
    )
    if link is None:
        send(settings, chat_id, "⚠️ I don't know which chat this is. Reply to a forwarded chat message.", msg.get("message_id"))
        return
    ws = db.get(Workspace, link.workspace_id)
    conv = db.get(Conversation, link.conversation_id)
    if ws is None or conv is None or str(ws.telegram_chat_id) != chat_id:
        send(settings, chat_id, "⚠️ This chat is no longer connected.", msg.get("message_id"))
        return

    if text.split("@")[0] in {"/done", "/close", "/bot"}:
        conv.status = "bot"
        chat.add_message(db, conv, "system", t(conv.language, "handoff_back_to_bot"))
        db.commit()
        send(settings, chat_id, f"✅ Chat #{conv.id} handed back to the AI.", msg.get("message_id"))
        return

    conv.status = "handoff"
    chat.add_message(db, conv, "operator", text)
    _link(db, ws, conv, int(msg["message_id"]))  # replies to your own reply also work
    db.commit()
    try:
        api(
            settings,
            "setMessageReaction",
            {"chat_id": chat_id, "message_id": msg["message_id"], "reaction": [{"type": "emoji", "emoji": "👍"}]},
        )
    except TelegramError:
        pass


# --- transport: long polling (default, no public URL needed) or webhook ------------------------


class Poller(threading.Thread):
    def __init__(self, settings: Settings) -> None:
        super().__init__(daemon=True, name="telegram-poller")
        self.settings = settings
        self.stop_event = threading.Event()

    def run(self) -> None:
        offset = 0
        try:
            api(self.settings, "deleteWebhook")
        except TelegramError as exc:
            log.warning("%s", exc)
        while not self.stop_event.is_set():
            try:
                updates = api(
                    self.settings,
                    "getUpdates",
                    {"offset": offset, "timeout": 25, "allowed_updates": ["message"]},
                    timeout=35,
                )
            except TelegramError as exc:
                log.warning("%s", exc)
                self.stop_event.wait(5)
                continue
            for update in updates or []:
                offset = max(offset, int(update["update_id"]) + 1)
                db = SessionLocal()
                try:
                    handle_update(db, self.settings, update)
                    db.commit()
                except Exception:  # noqa: BLE001
                    log.exception("failed to handle telegram update")
                    db.rollback()
                finally:
                    db.close()

    def stop(self) -> None:
        self.stop_event.set()


def setup_webhook(settings: Settings) -> None:
    api(
        settings,
        "setWebhook",
        {
            "url": f"{settings.public_url}/api/telegram/webhook",
            "secret_token": settings.telegram_webhook_secret,
            "allowed_updates": ["message"],
        },
    )
