from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.models import User, Workspace
from app.security import read_session

SESSION_COOKIE = "d2c_session"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def settings_dep() -> Settings:
    return get_settings()


def csrf_guard(request: Request) -> None:
    """Admin API calls must carry a custom header. Browsers never send custom headers on
    cross-site form posts, and cross-origin fetches with it are blocked by CORS."""
    if request.method not in _SAFE_METHODS and request.headers.get("x-requested-with") != "fetch":
        raise HTTPException(403, "Missing X-Requested-With header")


def current_user(
    request: Request, db: Session = Depends(get_db), settings: Settings = Depends(settings_dep)
) -> User:
    token = request.cookies.get(SESSION_COOKIE, "")
    user_id = read_session(token, settings.secret_key) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "Not logged in")
    return user


def is_superadmin(user: User, db: Session, settings: Settings) -> bool:
    if settings.superadmin_emails:
        return user.email.lower() in settings.superadmin_emails
    first_id = db.scalar(select(func.min(User.id)))
    return user.id == first_id


def owned_workspace(
    ws_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
) -> Workspace:
    ws = db.get(Workspace, ws_id)
    if ws is None or (ws.owner_id != user.id and not is_superadmin(user, db, settings)):
        raise HTTPException(404, "Workspace not found")
    return ws


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
