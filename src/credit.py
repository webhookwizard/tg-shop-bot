"""Store credit: the seller can top up a buyer's balance.

Credit is the private-seller superpower: regulars pay from balance in one
tap, no TXID round-trip, and the seller keeps them coming back. Every
movement is journaled in credit_ledger so the books always balance.
"""
from __future__ import annotations

import sqlite3
import time


class InsufficientCredit(Exception):
    pass


class CreditService:
    def __init__(self, conn: sqlite3.Connection, clock=time.time):
        self.conn = conn
        self.clock = clock

    def grant(self, user_id: int, cents: int, reason: str = "",
              admin: str = "") -> int:
        """Admin tops up a buyer. Returns the new balance."""
        if cents <= 0:
            raise ValueError("grant amount must be positive")
        note = f"{reason} (by {admin})" if admin else reason
        self.conn.execute(
            "INSERT INTO credit_ledger (user_id, delta_cents, reason, created_at)"
            " VALUES (?,?,?,?)",
            (user_id, cents, note, self.clock()),
        )
        self.conn.commit()
        return self.balance(user_id)

    def deduct(self, user_id: int, cents: int, reason: str = "") -> int:
        """Spend credit. Raises InsufficientCredit. Returns new balance."""
        if cents <= 0:
            raise ValueError("deduct amount must be positive")
        if self.balance(user_id) < cents:
            raise InsufficientCredit(
                f"need {cents}, have {self.balance(user_id)}")
        self.conn.execute(
            "INSERT INTO credit_ledger (user_id, delta_cents, reason, created_at)"
            " VALUES (?,?,?,?)",
            (user_id, -cents, reason, self.clock()),
        )
        self.conn.commit()
        return self.balance(user_id)

    def balance(self, user_id: int) -> int:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(delta_cents),0) AS bal FROM credit_ledger"
            " WHERE user_id=?", (user_id,)).fetchone()
        return int(row["bal"])

    def ledger(self, user_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT delta_cents, reason, created_at FROM credit_ledger"
            " WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
        return [dict(r) for r in rows]
