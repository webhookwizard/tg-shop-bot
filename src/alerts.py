"""Alert outbox. Services drop notifications here; the bot (or demo)
delivers them. Keeps business logic free of Telegram specifics.
"""
from __future__ import annotations

import sqlite3
import time

from .models import Alert


def add_alert(conn: sqlite3.Connection, user_id: int, kind: str,
              text: str, clock=time.time) -> Alert:
    cur = conn.execute(
        "INSERT INTO alerts (user_id, kind, text, created_at) VALUES (?,?,?,?)",
        (user_id, kind, text, clock()),
    )
    conn.commit()
    return get_alert(conn, cur.lastrowid)


def get_alert(conn: sqlite3.Connection, alert_id: int) -> Alert:
    row = conn.execute("SELECT * FROM alerts WHERE id=?", (alert_id,)).fetchone()
    return Alert.from_row(row)


def unread_for(conn: sqlite3.Connection, user_id: int) -> list[Alert]:
    rows = conn.execute(
        "SELECT * FROM alerts WHERE user_id=? AND read=0 ORDER BY id", (user_id,)
    ).fetchall()
    return [Alert.from_row(r) for r in rows]


def mark_read(conn: sqlite3.Connection, user_id: int) -> int:
    cur = conn.execute(
        "UPDATE alerts SET read=1 WHERE user_id=? AND read=0", (user_id,))
    conn.commit()
    return cur.rowcount
