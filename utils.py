"""
utils.py (mobile)
------------------
Same helper functions as the desktop app (kept logically identical on
purpose, so invoice numbers / GST math match exactly between the two
apps for when sync is built later).
"""

from datetime import datetime
import database as db


def get_settings():
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def currency(amount):
    settings = get_settings()
    symbol = settings.get("currency_symbol", "Rs.")
    try:
        return f"{symbol} {float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{symbol} 0.00"


def next_invoice_number():
    """Mobile invoices are prefixed MINV- so they're visually distinct from
    desktop-created invoices (MINV = Mobile INVoice) until sync unifies them."""
    today_str = datetime.now().strftime("%Y%m%d")
    conn = db.get_connection()
    row = conn.execute(
        "SELECT invoice_no FROM bills WHERE invoice_no LIKE ? ORDER BY id DESC LIMIT 1",
        (f"MINV-{today_str}-%",),
    ).fetchone()
    conn.close()
    if row:
        last_seq = int(row["invoice_no"].split("-")[-1])
        seq = last_seq + 1
    else:
        seq = 1
    return f"MINV-{today_str}-{seq:04d}"


def calc_line_total(qty, rate, gst_percent, discount_percent=0):
    qty = float(qty or 0)
    rate = float(rate or 0)
    gst_percent = float(gst_percent or 0)
    discount_percent = float(discount_percent or 0)

    gross = qty * rate
    discount_amount = gross * (discount_percent / 100.0)
    taxable = gross - discount_amount
    gst_amount = taxable * (gst_percent / 100.0)
    total = taxable + gst_amount
    return round(gross, 2), round(discount_amount, 2), round(gst_amount, 2), round(total, 2)


def today_range():
    today = datetime.now().strftime("%Y-%m-%d")
    return f"{today} 00:00:00", f"{today} 23:59:59"


def month_range():
    now = datetime.now()
    start = now.strftime("%Y-%m-01 00:00:00")
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    end = next_month.strftime("%Y-%m-%d 00:00:00")
    return start, end


def validate_positive_number(value, field_name="Value"):
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number.")
    if num < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return num
