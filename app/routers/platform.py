"""Platform owner (superadmin) tools for the hosted version: see all customers and set plans
manually, e.g. after a local bank transfer."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import get_db
from app.models import Document, User, Usage, Workspace
from app.routers.deps import csrf_guard, current_user, is_superadmin, settings_dep

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
    out = []
    for ws, email in rows:
        plan = plans.effective_plan(ws, settings)
        mrr += plan.price_usd
        out.append(
            {
                "id": ws.id,
                "name": ws.name,
                "owner_email": email,
                "plan": plan.id,
                "plan_source": ws.plan_source,
                "plan_expires_at": ws.plan_expires_at.isoformat() + "Z" if ws.plan_expires_at else None,
                "paddle_status": ws.paddle_status,
                "ai_messages": usage.get(ws.id, 0),
                "documents": docs.get(ws.id, 0),
                "telegram": bool(ws.telegram_chat_id),
                "created_at": ws.created_at.isoformat() + "Z",
            }
        )
    return {"mrr_usd": mrr, "workspaces": out}


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
