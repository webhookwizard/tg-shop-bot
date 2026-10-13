"""Payment review queue: the seller's safety net.

Every manual USDT payment lands here. The seller sees each order with a
risk score and a plain-English reason, then decides:

  approve -> money confirmed, order marked paid
  refund  -> money sent back, order marked refunded
  ignore  -> flag dismissed, order goes back to awaiting payment
            (buyer can fix and resubmit)
"""
from __future__ import annotations

import sqlite3
import time

from .models import ReviewItem
from .orders import OrderService
from .payments import PaymentService


class ReviewError(Exception):
    pass


class ReviewService:
    def __init__(self, conn: sqlite3.Connection, payments: PaymentService,
                 clock=time.time):
        self.conn = conn
        self.payments = payments
        self.orders: OrderService = payments.orders
        self.clock = clock

    def record(self, order_id: int, reason: str, risk_score: int) -> ReviewItem:
        # A resubmitted payment reopens review for the same order.
        cur = self.conn.execute(
            """INSERT INTO review_items
               (order_id, reason, risk_score, status, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(order_id) DO UPDATE SET
                 reason=excluded.reason,
                 risk_score=excluded.risk_score,
                 status='open',
                 created_at=excluded.created_at,
                 decided_at=NULL""",
            (order_id, reason or "manual_review", risk_score, "open",
             self.clock()),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM review_items WHERE order_id=?", (order_id,)).fetchone()
        return ReviewItem.from_row(row)

    def get(self, item_id: int) -> ReviewItem | None:
        row = self.conn.execute(
            "SELECT * FROM review_items WHERE id=?", (item_id,)).fetchone()
        return ReviewItem.from_row(row) if row else None

    def list_open(self) -> list[ReviewItem]:
        rows = self.conn.execute(
            "SELECT * FROM review_items WHERE status='open'"
            " ORDER BY risk_score DESC, id").fetchall()
        return [ReviewItem.from_row(r) for r in rows]

    def open_with_orders(self) -> list[dict]:
        """Open items joined with order + product info for the admin view."""
        rows = self.conn.execute(
            """SELECT ri.*, o.buyer_id, o.buyer_name, o.total_cents,
                      o.pay_method, p.name AS product_name
               FROM review_items ri
               JOIN orders o ON o.id = ri.order_id
               JOIN products p ON p.id = o.product_id
               WHERE ri.status='open'
               ORDER BY ri.risk_score DESC, ri.id""").fetchall()
        return [dict(r) for r in rows]

    def approve(self, item_id: int) -> ReviewItem:
        item = self._get_open(item_id)
        payment = self.payments.payment_for_order(item.order_id)
        if payment is None:
            raise ReviewError(f"no payment for order #{item.order_id}")
        self.payments.confirm(payment.id)
        return self._decide(item_id, "approved")

    def refund(self, item_id: int, reason: str = "") -> ReviewItem:
        item = self._get_open(item_id)
        payment = self.payments.payment_for_order(item.order_id)
        if payment is not None:
            self.payments.reject(payment.id)
        self.orders.mark_refunded(item.order_id)
        if reason:
            self._note(item.order_id, reason)
        return self._decide(item_id, "refunded")

    def ignore(self, item_id: int) -> ReviewItem:
        item = self._get_open(item_id)
        self.orders.back_to_awaiting(item.order_id)
        return self._decide(item_id, "ignored")

    # -- internals ----------------------------------------------------
    def _get_open(self, item_id: int) -> ReviewItem:
        item = self.get(item_id)
        if item is None:
            raise ReviewError(f"no review item #{item_id}")
        if item.status != "open":
            raise ReviewError(f"review #{item_id} already {item.status}")
        return item

    def _decide(self, item_id: int, status: str) -> ReviewItem:
        self.conn.execute(
            "UPDATE review_items SET status=?, decided_at=? WHERE id=?",
            (status, self.clock(), item_id))
        self.conn.commit()
        return self.get(item_id)

    def _note(self, order_id: int, reason: str) -> None:
        # Refund reason is journaled on the payment for the books.
        self.conn.execute(
            "UPDATE payments SET sender_note=? WHERE order_id=?",
            (f"refund: {reason}", order_id))
        self.conn.commit()
