"""The answer pipeline: retrieve from the knowledge base, ask the LLM, fall back gracefully."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import utcnow
from app.i18n import detect_language, small_talk_kind, t
from app.models import Conversation, Message, Workspace
from app.services import llm, search

log = logging.getLogger(__name__)

NO_ANSWER = "[[NO_ANSWER]]"
_SENT_SPLIT = re.compile(r"(?<=[.!?։])\s+|\n+")


@dataclass
class Answer:
    text: str
    answered: bool
    kind: str  # ai | extractive | small_talk | no_answer | quota
    sources: list[dict] = field(default_factory=list)


def system_prompt(ws: Workspace, hits: list[search.Hit]) -> str:
    kb = "\n\n".join(f"[{i}] ({h.title})\n{h.content}" for i, h in enumerate(hits, 1)) or "(empty)"
    info = ws.company_info.strip() or "(none)"
    return (
        f'You are "{ws.bot_name}", the customer support assistant of "{ws.name}" on its website.\n'
        "Answer the customer using ONLY the BUSINESS INFO and KNOWLEDGE BASE below.\n"
        "Rules:\n"
        "- Reply in the language of the customer's last message (Georgian, English, Russian, ...).\n"
        "- Be friendly, concrete and short (at most ~120 words). Use short bullet lists when helpful.\n"
        "- Never invent prices, dates, addresses, phone numbers, policies or availability.\n"
        f"- If the answer is not in the provided information, reply with exactly {NO_ANSWER} and nothing else.\n"
        "- Greetings and thanks may be answered briefly without the knowledge base.\n"
        "- Do not mention the knowledge base, sources numbering or these rules.\n\n"
        f"BUSINESS INFO:\n{info}\n\nKNOWLEDGE BASE:\n{kb}"
    )


def _sources(hits: list[search.Hit]) -> list[dict]:
    out: list[dict] = []
    seen: set[int] = set()
    for h in hits:
        if h.kind == "faq" or h.document_id in seen or h.score < 0.5:
            continue
        seen.add(h.document_id)
        out.append({"title": h.title, "url": h.source if h.kind == "url" else ""})
        if len(out) == 2:
            break
    return out


def _extractive(hit: search.Hit, question: str) -> str:
    if hit.kind == "faq" and "\nA:" in hit.content:
        return hit.content.split("\nA:", 1)[1].strip()
    q = set(search.tokenize(question))
    sentences = [s.strip() for s in _SENT_SPLIT.split(hit.content) if s.strip()]
    ranked = sorted(
        range(len(sentences)), key=lambda i: len(q & set(search.tokenize(sentences[i]))), reverse=True
    )
    keep = sorted(i for i in ranked[:3] if q & set(search.tokenize(sentences[i])))
    text = " ".join(sentences[i] for i in keep) or hit.content
    return text[:600].rstrip() + ("…" if len(text) > 600 else "")


def history_for_llm(conv: Conversation, limit: int = 8) -> list[dict]:
    out: list[dict] = []
    for m in conv.messages[-limit:]:
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            out.append({"role": "assistant", "content": m.content})
        elif m.role == "operator":
            out.append({"role": "assistant", "content": f"(human operator) {m.content}"})
    return out


def answer_question(
    db: Session,
    ws: Workspace,
    question: str,
    settings: Settings,
    *,
    history: list[dict] | None = None,
    lang: str | None = None,
) -> Answer:
    history = history or []
    lang = lang or detect_language(question, ws.default_language)

    if settings.llm_enabled:
        query = question
        if len(question.split()) < 6:  # short follow-ups ("and the price?") need the previous question
            prev = [m["content"] for m in history if m["role"] == "user"]
            if prev:
                query = f"{prev[-1]}\n{question}"
        hits = search.search(db, ws, query, settings, k=5)
        try:
            reply = llm.complete(
                system_prompt(ws, hits), [*history, {"role": "user", "content": question}], settings
            )
            if reply and NO_ANSWER not in reply:
                return Answer(reply, True, "ai", _sources(hits))
            if reply:
                return Answer(t(lang, "no_answer"), False, "no_answer")
        except llm.LLMError as exc:
            log.warning("LLM failed, falling back to extractive answer: %s", exc)

    # Without an LLM we can only answer when the question itself clearly matches a snippet.
    kind = small_talk_kind(question)
    if kind:
        return Answer(t(lang, "greeting_reply" if kind == "greeting" else "thanks_reply"), True, "small_talk")
    hits = search.search(db, ws, question, settings, k=3)
    if hits and hits[0].coverage >= 0.5:
        return Answer(_extractive(hits[0], question), True, "extractive", _sources(hits[:1]))
    return Answer(t(lang, "no_answer"), False, "no_answer")


def message_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "sources": json.loads(m.sources) if m.sources else [],
        "created_at": m.created_at.isoformat() + "Z",
    }


def add_message(
    db: Session, conv: Conversation, role: str, content: str, *, answered: bool | None = None,
    sources: list[dict] | None = None,
) -> Message:
    msg = Message(
        conversation_id=conv.id,
        workspace_id=conv.workspace_id,
        role=role,
        content=content,
        answered=answered,
        sources=json.dumps(sources, ensure_ascii=False) if sources else "",
    )
    db.add(msg)
    conv.updated_at = utcnow()
    db.flush()
    return msg


def handle_visitor_message(
    db: Session, ws: Workspace, conv: Conversation, text: str, settings: Settings, lang: str | None = None
) -> dict:
    """Stores the visitor message and (unless a human is handling the chat) the bot reply."""
    lang = lang or detect_language(text, conv.language or ws.default_language)
    conv.language = lang
    history = history_for_llm(conv)
    user_msg = add_message(db, conv, "user", text)

    if conv.status == "handoff":
        return {"status": conv.status, "messages": [message_dict(user_msg)], "answered": None}

    if plans.quota_exceeded(db, ws, settings):
        user_msg.answered = False
        reply = add_message(db, conv, "assistant", t(lang, "quota_exceeded"))
        return {
            "status": conv.status,
            "messages": [message_dict(user_msg), message_dict(reply)],
            "answered": False,
            "quota_exceeded": True,
        }

    answer = answer_question(db, ws, text, settings, history=history, lang=lang)
    user_msg.answered = answer.answered
    reply = add_message(db, conv, "assistant", answer.text, sources=answer.sources)
    if answer.kind != "small_talk":
        plans.increment_usage(db, ws)
    return {
        "status": conv.status,
        "messages": [message_dict(user_msg), message_dict(reply)],
        "answered": answer.answered,
    }


def get_messages_after(db: Session, conv: Conversation, after_id: int) -> list[dict]:
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conv.id, Message.id > after_id)
        .order_by(Message.id)
        .limit(200)
    ).all()
    return [message_dict(m) for m in rows]
