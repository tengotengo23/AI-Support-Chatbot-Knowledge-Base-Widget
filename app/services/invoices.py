"""Bank-transfer invoices for local customers (0% payment fees).

Flow: the platform owner issues an invoice from the Platform page -> the customer sees it on
their "Plan & billing" page (and in Telegram, if connected) and pays by bank transfer ->
the owner clicks "Paid" -> the plan is extended automatically by the invoiced number of months.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from html import escape

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import plans
from app.config import Settings
from app.db import utcnow
from app.models import Invoice, Workspace


def add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year, month = dt.year + month_index // 12, month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def next_number(db: Session, settings: Settings) -> str:
    year = utcnow().year
    prefix = f"{settings.invoice_prefix}-{year}-"
    count = db.scalar(select(func.count(Invoice.id)).where(Invoice.number.like(prefix + "%"))) or 0
    return f"{prefix}{count + 1:04d}"


def create(
    db: Session,
    settings: Settings,
    ws: Workspace,
    *,
    plan: str,
    months: int,
    currency: str,
    amount: float | None = None,
    buyer_name: str = "",
    buyer_tax_id: str = "",
    buyer_email: str = "",
    note: str = "",
) -> Invoice:
    now = utcnow()
    inv = Invoice(
        number=next_number(db, settings),
        workspace_id=ws.id,
        workspace_name=ws.name,
        plan=plan,
        months=months,
        amount=round(amount if amount is not None else plans.invoice_amount(plan, months, currency), 2),
        currency=currency,
        buyer_name=buyer_name.strip() or ws.name,
        buyer_tax_id=buyer_tax_id.strip(),
        buyer_email=buyer_email.strip(),
        note=note.strip(),
        issued_at=now,
        due_at=now + timedelta(days=settings.invoice_due_days),
    )
    db.add(inv)
    db.flush()
    return inv


def mark_paid(db: Session, inv: Invoice) -> None:
    """Extend the plan. Renewing the same manually-paid plan continues from its current end date,
    so paying early never loses days."""
    now = utcnow()
    inv.status, inv.paid_at = "paid", now
    ws = db.get(Workspace, inv.workspace_id) if inv.workspace_id else None
    if ws is None:
        return
    start = now
    if ws.plan == inv.plan and ws.plan_source == "manual" and ws.plan_expires_at and ws.plan_expires_at > now:
        start = ws.plan_expires_at
    inv.period_start, inv.period_end = start, add_months(start, inv.months)
    ws.plan, ws.plan_source, ws.plan_expires_at = inv.plan, "manual", inv.period_end


def to_dict(inv: Invoice, settings: Settings) -> dict:
    def iso(dt: datetime | None) -> str | None:
        return dt.isoformat() + "Z" if dt else None

    return {
        "id": inv.id,
        "number": inv.number,
        "workspace_id": inv.workspace_id,
        "workspace_name": inv.workspace_name,
        "plan": inv.plan,
        "months": inv.months,
        "amount": inv.amount,
        "currency": inv.currency,
        "status": inv.status,
        "overdue": inv.status == "issued" and inv.due_at < utcnow(),
        "buyer_name": inv.buyer_name,
        "issued_at": iso(inv.issued_at),
        "due_at": iso(inv.due_at),
        "paid_at": iso(inv.paid_at),
        "period_end": iso(inv.period_end),
        "url": f"{settings.public_url}/invoice/{inv.id}",
    }


def summary(db: Session) -> dict:
    """Cash collected this month and money still owed, per currency."""
    month_start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    paid = db.execute(
        select(Invoice.currency, func.sum(Invoice.amount))
        .where(Invoice.status == "paid", Invoice.paid_at >= month_start)
        .group_by(Invoice.currency)
    ).all()
    outstanding = db.execute(
        select(Invoice.currency, func.sum(Invoice.amount)).where(Invoice.status == "issued").group_by(Invoice.currency)
    ).all()
    return {
        "paid_this_month": {c: round(float(a), 2) for c, a in paid},
        "outstanding": {c: round(float(a), 2) for c, a in outstanding},
    }


# --- printable page ---------------------------------------------------------------------------

_SYMBOL = {"GEL": "₾", "USD": "$", "EUR": "€"}
_STATUS = {"issued": ("გადასახდელია · Unpaid", "#b45309"), "paid": ("გადახდილია · Paid", "#15803d"),
           "void": ("გაუქმებულია · Void", "#6b7280")}


def money(amount: float, currency: str) -> str:
    return f"{amount:,.2f} {_SYMBOL.get(currency, currency)}"


def render_html(inv: Invoice, settings: Settings) -> str:
    e = escape
    plan = plans.PLANS.get(inv.plan)
    plan_name = plan.name if plan else inv.plan
    status_text, status_color = _STATUS.get(inv.status, (inv.status, "#6b7280"))
    period = ""
    if inv.period_start and inv.period_end:
        period = f"<br><span class=m>{inv.period_start:%d.%m.%Y} – {inv.period_end:%d.%m.%Y}</span>"

    def row(label: str, value: str) -> str:
        return f"<tr><th>{label}</th><td>{e(value)}</td></tr>" if value else ""

    seller = "".join([
        f"<div class=n>{e(settings.legal_name or settings.brand_name)}</div>",
        "<table class=kv>",
        row("ს/კ · Tax ID", settings.seller_tax_id),
        row("მისამართი · Address", settings.seller_address),
        row("ელ-ფოსტა · Email", settings.contact_email),
        "</table>",
    ])
    buyer = "".join([
        f"<div class=n>{e(inv.buyer_name)}</div>",
        "<table class=kv>",
        row("ს/კ · Tax ID", inv.buyer_tax_id),
        row("ელ-ფოსტა · Email", inv.buyer_email),
        "</table>",
    ])
    bank = "".join([
        "<table class=kv>",
        row("მიმღები · Beneficiary", settings.legal_name),
        row("ბანკი · Bank", settings.seller_bank),
        row("IBAN", settings.seller_iban),
        row("დანიშნულება · Reference", inv.number),
        "</table>",
    ])
    months_label = f"{inv.months} თვე · {inv.months} month{'s' if inv.months != 1 else ''}"
    note = f"<p class=m>{e(inv.note)}</p>" if inv.note else ""
    return f"""<!doctype html>
<html lang="ka"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(inv.number)} · {e(settings.brand_name)}</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}
body{{margin:0;background:#f3f4f6;font:14px/1.5 system-ui,-apple-system,"Segoe UI","Noto Sans Georgian",sans-serif;color:#111827}}
.page{{max-width:800px;margin:24px auto;background:#fff;padding:40px;border-radius:12px;box-shadow:0 1px 3px #0002}}
.top{{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-start}}
h1{{margin:0;font-size:26px}}.m{{color:#6b7280;font-size:13px}}
.badge{{display:inline-block;padding:4px 10px;border-radius:999px;color:#fff;font-weight:600;background:{status_color}}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:28px 0}}
.lbl{{text-transform:uppercase;letter-spacing:.05em;font-size:11px;color:#6b7280;margin-bottom:4px}}
.n{{font-weight:700;font-size:15px}}
.kv{{border-collapse:collapse}}.kv th{{text-align:left;font-weight:400;color:#6b7280;padding:2px 12px 2px 0;white-space:nowrap}}
.kv td{{padding:2px 0;word-break:break-all}}
.items{{width:100%;border-collapse:collapse;margin:8px 0 0}}
.items th,.items td{{padding:10px 8px;border-bottom:1px solid #e5e7eb;text-align:left}}
.items th{{font-size:12px;color:#6b7280;font-weight:600}}.r{{text-align:right!important}}
.total td{{font-weight:800;font-size:18px;border-bottom:0}}
.pay{{margin-top:28px;padding:16px;border:1px dashed #d1d5db;border-radius:10px;background:#fafafa}}
.actions{{max-width:800px;margin:0 auto 24px;text-align:right}}
button{{font:inherit;padding:8px 14px;border-radius:8px;border:0;background:#111827;color:#fff;cursor:pointer}}
@media (max-width:600px){{.page{{padding:20px;margin:0;border-radius:0}}.cols{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}}.page{{box-shadow:none;margin:0;max-width:none}}.actions{{display:none}}}}
</style></head><body>
<div class=page>
  <div class=top>
    <div><h1>ინვოისი · Invoice</h1><div class=m>№ {e(inv.number)}</div></div>
    <div style="text-align:right"><span class=badge>{status_text}</span>
      <div class=m style="margin-top:6px">გაცემის თარიღი · Issued: {inv.issued_at:%d.%m.%Y}<br>
      გადახდის ვადა · Due: {inv.due_at:%d.%m.%Y}</div></div>
  </div>
  <div class=cols>
    <div><div class=lbl>გამყიდველი · Seller</div>{seller}</div>
    <div><div class=lbl>მყიდველი · Bill to</div>{buyer}</div>
  </div>
  <table class=items>
    <thead><tr><th>მომსახურება · Description</th><th>პერიოდი · Period</th><th class=r>თანხა · Amount</th></tr></thead>
    <tbody>
      <tr><td>{e(settings.brand_name)} — AI ჩატ-ასისტენტი, პაკეტი „{e(plan_name)}“<br>
        <span class=m>AI chat assistant, {e(plan_name)} plan · {e(inv.workspace_name)}</span></td>
        <td>{months_label}{period}</td><td class=r>{money(inv.amount, inv.currency)}</td></tr>
      <tr class=total><td colspan=2 class=r>სულ გადასახდელი · Total</td><td class=r>{money(inv.amount, inv.currency)}</td></tr>
    </tbody>
  </table>
  {note}
  <div class=pay><div class=lbl>საბანკო რეკვიზიტები · Bank details</div>{bank}
    <p class=m style="margin:8px 0 0">გადარიცხვისას დანიშნულებაში მიუთითეთ ინვოისის ნომერი.
    Please include the invoice number as the payment reference.</p></div>
</div>
<div class=actions><button type=button onclick="window.print()">🖨 ბეჭდვა / PDF · Print</button></div>
</body></html>"""
