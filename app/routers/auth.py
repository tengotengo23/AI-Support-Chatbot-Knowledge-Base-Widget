from __future__ import annotations

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db, utcnow
from app.models import User, Workspace
from app.plans import TRIAL_PLAN, effective_plan
from app.routers.deps import (
    SESSION_COOKIE,
    client_ip,
    csrf_guard,
    current_user,
    is_superadmin,
    settings_dep,
)
from app.security import SESSION_TTL_SECONDS, hash_password, rate_limiter, sign_session, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(csrf_guard)])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=200)
    workspace_name: str = Field(default="My business", min_length=1, max_length=200)


class LoginIn(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(max_length=200)


def _set_session(response: Response, user: User, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        sign_session(user.id, settings.secret_key),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        path="/",
    )


@router.post("/signup")
def signup(
    body: SignupIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    if not rate_limiter.allow(f"signup:{client_ip(request)}", 5, 3600):
        raise HTTPException(429, "Too many signups, try again later")
    has_users = db.scalar(select(func.count(User.id))) > 0
    if has_users and not settings.signup_enabled:
        raise HTTPException(403, "Sign-up is disabled on this server")
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(400, "Invalid email")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "This email is already registered")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    ws = Workspace(owner_id=user.id, name=body.workspace_name.strip(), bot_name="Assistant")
    if settings.billing_enabled and settings.trial_days:
        # Free trial of the Pro plan for the first chatbot; it falls back to Free when it ends.
        ws.plan, ws.plan_source = TRIAL_PLAN, "trial"
        ws.plan_expires_at = utcnow() + timedelta(days=settings.trial_days)
    db.add(ws)
    db.commit()
    _set_session(response, user, settings)
    return {"ok": True}


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    if not rate_limiter.allow(f"login:{client_ip(request)}", 10, 60):
        raise HTTPException(429, "Too many attempts, wait a minute")
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    _set_session(response, user, settings)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    workspaces = db.scalars(select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.id)).all()
    return {
        "email": user.email,
        "is_superadmin": is_superadmin(user, db, settings),
        "billing_enabled": settings.billing_enabled,
        "brand_name": settings.brand_name,
        "llm_enabled": settings.llm_enabled,
        "llm_provider": settings.llm_provider,
        "telegram_enabled": bool(settings.telegram_bot_token),
        "workspaces": [
            {"id": w.id, "name": w.name, "plan": effective_plan(w, settings).id} for w in workspaces
        ],
    }


@router.get("/status")
def status(db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)):
    """Lets the login page know whether sign-up is possible (first user can always sign up)."""
    has_users = db.scalar(select(func.count(User.id))) > 0
    return {
        "brand_name": settings.brand_name,
        "signup_enabled": settings.signup_enabled or not has_users,
        "has_users": has_users,
    }
