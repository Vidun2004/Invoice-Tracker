"""Small helpers: formatting, dates, validation."""
from datetime import date, datetime

def fmt_money(amount, currency="LKR") -> str:
    try:
        v = float(amount or 0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{currency} {v:,.2f}"

def parse_date(s: str | None):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def is_overdue(row: dict) -> bool:
    if (row.get("current_stage") or "") == "Paid":
        return False
    due = parse_date(row.get("due_date") or "")
    return bool(due and due < date.today())

def days_overdue(row: dict) -> int:
    due = parse_date(row.get("due_date") or "")
    if not due:
        return 0
    return (date.today() - due).days
