"""Invoices as seen by the customer: a list on the billing page and a printable invoice page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.models import Invoice, Workspace
from app.routers.deps import csrf_guard, current_user, is_superadmin, owned_workspace, settings_dep
from app.services import invoices

router = APIRouter(dependencies=[Depends(csrf_guard)])


@router.get("/api/workspaces/{ws_id}/invoices", tags=["billing"])
def workspace_invoices(
    ws: Workspace = Depends(owned_workspace),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    rows = db.scalars(
        select(Invoice).where(Invoice.workspace_id == ws.id, Invoice.status != "void").order_by(Invoice.id.desc())
    ).all()
    return [invoices.to_dict(i, settings) for i in rows]


@router.get("/invoice/{invoice_id}", include_in_schema=False)
def invoice_page(
    invoice_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    try:
        user = current_user(request, db, settings)
    except HTTPException:
        return RedirectResponse("/admin")
    inv = db.get(Invoice, invoice_id)
    ws = db.get(Workspace, inv.workspace_id) if inv and inv.workspace_id else None
    allowed = inv is not None and (
        (ws is not None and ws.owner_id == user.id) or is_superadmin(user, db, settings)
    )
    if not allowed:
        raise HTTPException(404, "Invoice not found")
    return HTMLResponse(invoices.render_html(inv, settings))
