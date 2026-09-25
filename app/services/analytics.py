from __future__ import annotations

from collections import Counter
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import Conversation, Lead, Message, Workspace


def _norm(text: str) -> str:
    return " ".join("".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())


def summary(db: Session, ws: Workspace, days: int = 30) -> dict:
    since = utcnow() - timedelta(days=days)

    conversations = db.scalars(
        select(Conversation.created_at).where(
            Conversation.workspace_id == ws.id, Conversation.created_at >= since
        )
    ).all()
    per_day: Counter[str] = Counter(c.strftime("%Y-%m-%d") for c in conversations)
    daily = []
    for i in range(days - 1, -1, -1):
        day = (utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily.append({"date": day, "conversations": per_day.get(day, 0)})

    questions = db.execute(
        select(Message.content, Message.answered).where(
            Message.workspace_id == ws.id, Message.role == "user", Message.created_at >= since
        )
    ).all()
    total_q = len(questions)
    answered = sum(1 for _, a in questions if a is True)
    unanswered = sum(1 for _, a in questions if a is False)

    top: Counter[str] = Counter()
    sample: dict[str, str] = {}
    for content, _ in questions:
        key = _norm(content)
        if len(key) < 3:
            continue
        top[key] += 1
        sample.setdefault(key, content.strip())

    unanswered_rows = db.execute(
        select(Message.content, func.max(Message.created_at), func.count(Message.id))
        .where(
            Message.workspace_id == ws.id,
            Message.role == "user",
            Message.answered.is_(False),
            Message.created_at >= since,
        )
        .group_by(Message.content)
        .order_by(func.count(Message.id).desc(), func.max(Message.created_at).desc())
        .limit(25)
    ).all()

    leads = db.scalar(
        select(func.count(Lead.id)).where(Lead.workspace_id == ws.id, Lead.created_at >= since)
    )
    handoffs = db.scalar(
        select(func.count(func.distinct(Message.conversation_id))).where(
            Message.workspace_id == ws.id, Message.role == "operator", Message.created_at >= since
        )
    )

    return {
        "days": days,
        "totals": {
            "conversations": len(conversations),
            "questions": total_q,
            "answered": answered,
            "unanswered": unanswered,
            "answer_rate": round(answered / total_q * 100) if total_q else None,
            "leads": leads or 0,
            "human_chats": handoffs or 0,
        },
        "daily": daily,
        "top_questions": [{"question": sample[k], "count": n} for k, n in top.most_common(10)],
        "unanswered_questions": [
            {"question": q, "count": n, "last_at": last.isoformat() + "Z"} for q, last, n in unanswered_rows
        ],
    }
