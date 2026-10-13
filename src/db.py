"""SQLite storage. One file, zero servers, zero maintenance.

The whole shop — catalog, orders, payments, review queue, credit ledger,
wishlists, subscriptions, alert outbox — lives in a single SQLite file,
so a seller can back up the business by copying one file.
"""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT NOT NULL,
  description   TEXT NOT NULL DEFAULT '',
  price_cents   INTEGER NOT NULL CHECK (price_cents >= 0),
  kind          TEXT NOT NULL DEFAULT 'once' CHECK (kind IN ('once','subscription')),
  billing_days  INTEGER NOT NULL DEFAULT 0,
  stock         INTEGER NOT NULL DEFAULT -1,
  active        INTEGER NOT NULL DEFAULT 1,
  created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  buyer_id      INTEGER NOT NULL,
  buyer_name    TEXT NOT NULL DEFAULT '',
  product_id    INTEGER NOT NULL REFERENCES products(id),
  qty           INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
  total_cents   INTEGER NOT NULL,
  pay_method    TEXT NOT NULL DEFAULT 'usdt_manual',
  status        TEXT NOT NULL DEFAULT 'awaiting_payment',
  txid          TEXT,
  created_at    REAL NOT NULL,
  paid_at       REAL
);
CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(buyer_id);

CREATE TABLE IF NOT EXISTS payments (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id      INTEGER NOT NULL REFERENCES orders(id),
  txid          TEXT NOT NULL UNIQUE,
  amount_cents  INTEGER NOT NULL,
  sender_note   TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT 'submitted',
  created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS review_items (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id      INTEGER NOT NULL UNIQUE REFERENCES orders(id),
  reason        TEXT NOT NULL,
  risk_score    INTEGER NOT NULL DEFAULT 0,
  status        TEXT NOT NULL DEFAULT 'open',
  created_at    REAL NOT NULL,
  decided_at    REAL
);

CREATE TABLE IF NOT EXISTS credit_ledger (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  delta_cents   INTEGER NOT NULL,
  reason        TEXT NOT NULL DEFAULT '',
  created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_credit_user ON credit_ledger(user_id);

CREATE TABLE IF NOT EXISTS wishlist (
  user_id       INTEGER NOT NULL,
  product_id    INTEGER NOT NULL REFERENCES products(id),
  added_at      REAL NOT NULL,
  PRIMARY KEY (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  product_id    INTEGER NOT NULL REFERENCES products(id),
  status        TEXT NOT NULL DEFAULT 'active',
  started_at    REAL NOT NULL,
  renews_at     REAL NOT NULL,
  last_paid_at  REAL
);
CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_id);

CREATE TABLE IF NOT EXISTS alerts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL,
  kind          TEXT NOT NULL,
  text          TEXT NOT NULL,
  created_at    REAL NOT NULL,
  read          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_alerts_user ON alerts(user_id);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    """Open a SQLite connection with sane defaults."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables. Safe to call on an existing database."""
    conn.executescript(SCHEMA)
    conn.commit()
