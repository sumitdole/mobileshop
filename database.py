"""
database.py (mobile)
---------------------
Same table schema as the Windows desktop app (Phase 1 + the columns the
desktop Phase 2 build added), so that a future sync feature between the
phone and the shop PC doesn't require a data migration on either side.

The one Android-specific difference: the DB file lives in the app's
private data directory (via Kivy's App.user_data_dir) instead of next
to the script, since a phone app can't assume it can write next to its
own installed code.
"""

import sqlite3
import os
from datetime import datetime

_DB_PATH = None


def set_db_path(path):
    """Called once from main.py with App.user_data_dir/shop_data.db."""
    global _DB_PATH
    _DB_PATH = path


def get_db_path():
    if _DB_PATH is None:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop_data.db")
    return _DB_PATH


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    shop_name       TEXT DEFAULT 'My Electrical & Plumbing Shop',
    address         TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    gst_number      TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    invoice_footer  TEXT DEFAULT 'Thank you for shopping with us!',
    currency_symbol TEXT DEFAULT 'Rs.',
    default_gst     REAL DEFAULT 18.0
);

CREATE TABLE IF NOT EXISTS categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT,
    address         TEXT,
    gst_number      TEXT,
    email           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    category_id     INTEGER,
    brand           TEXT,
    purchase_price  REAL DEFAULT 0,
    selling_price   REAL DEFAULT 0,
    gst_percent     REAL DEFAULT 18,
    stock_qty       REAL DEFAULT 0,
    unit            TEXT DEFAULT 'pcs',
    supplier_id     INTEGER,
    shelf_location  TEXT,
    min_stock       REAL DEFAULT 5,
    description     TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS customers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    phone           TEXT,
    address         TEXT,
    gst_number      TEXT,
    email           TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no      TEXT UNIQUE NOT NULL,
    customer_id     INTEGER,
    bill_date       TEXT DEFAULT (datetime('now')),
    subtotal        REAL DEFAULT 0,
    discount        REAL DEFAULT 0,
    gst_amount      REAL DEFAULT 0,
    total           REAL DEFAULT 0,
    profit          REAL DEFAULT 0,
    payment_method  TEXT DEFAULT 'Cash',
    amount_paid     REAL DEFAULT 0,
    credit_amount   REAL DEFAULT 0,
    status          TEXT DEFAULT 'Completed',
    notes           TEXT,
    created_by      TEXT DEFAULT 'admin',
    synced          INTEGER DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS bill_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         INTEGER NOT NULL,
    product_id      INTEGER,
    product_name    TEXT NOT NULL,
    qty             REAL NOT NULL,
    rate            REAL NOT NULL,
    gst_percent     REAL DEFAULT 0,
    discount        REAL DEFAULT 0,
    purchase_price_snapshot REAL DEFAULT 0,
    total           REAL NOT NULL,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS credit_payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     INTEGER NOT NULL,
    bill_id         INTEGER,
    amount          REAL NOT NULL,
    pay_date        TEXT DEFAULT (datetime('now')),
    method          TEXT DEFAULT 'Cash',
    note            TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (bill_id) REFERENCES bills(id)
);

CREATE TABLE IF NOT EXISTS stock_adjustments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL,
    qty_change      REAL NOT NULL,
    reason          TEXT NOT NULL,
    note            TEXT,
    adjustment_date TEXT DEFAULT (datetime('now')),
    created_by      TEXT DEFAULT 'admin',
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS device_info (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    device_label    TEXT DEFAULT 'Phone',
    last_sync       TEXT DEFAULT ''
);
"""

DEFAULT_CATEGORIES = [
    "Wires & Cables", "Switches & Sockets", "MCB & Distribution Boards",
    "Lights & LED", "Fans", "Electrical Tape & Tools", "Motors & Pumps",
    "PVC Pipes & Fittings", "CPVC Pipes & Fittings", "Taps & Faucets",
    "Bathroom Fittings", "Water Tanks", "Valves", "Plumbing Tools",
    "Adhesives & Sealants", "Miscellaneous",
]


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    cur.execute("SELECT COUNT(*) as c FROM settings")
    if cur.fetchone()["c"] == 0:
        cur.execute("INSERT INTO settings (id) VALUES (1)")

    for cat in DEFAULT_CATEGORIES:
        cur.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (cat,))

    cur.execute("SELECT COUNT(*) as c FROM device_info")
    if cur.fetchone()["c"] == 0:
        cur.execute("INSERT INTO device_info (id, device_label) VALUES (1, 'Phone')")

    conn.commit()
    conn.close()
