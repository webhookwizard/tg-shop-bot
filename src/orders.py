"""Orders: the lifecycle of a purchase.

created (awaiting_payment) -> payment_submitted -> paid -> completed
                                     \-> cancelled / refunded

Credit orders skip the payment round-trip: created -> paid.
"""
from __future__ import annotations

import sqlite3
import time

from .catalog import CatalogService
from .credit import CreditService, InsufficientCredit
from .models import Order

# Order statuses
AWAITING_PAYMENT = "awaiting_payment"
PAYMENT_SUBMITTED = "payment_submitted"
PAID = "paid"
COMPLETED = "completed"
CANCELLED = "cancelled"
REFUNDED = "refunded"

TERMINAL = {PAID, COMPLETED, CANCELLED, REFUNDED}


class OrderError(Exception):
    pass


class OrderService:
    def __init__(self, conn: sqlite3.Connection, catalog: CatalogService,
                 credit: CreditService, clock=time.time):
        self.conn = conn
        self.catalog = catalog
        self.credit = credit
        self.clock = clock

    def create_order(self, buyer_id: int, buyer_name: str, product_id: int,
                     qty: int = 1, pay_method: str = "usdt_manual") -> Order:
        product = self.catalog.get(product_id)
        if product is None or not product.active:
            raise OrderError(f"product #{product_id} is not available")
        if qty <= 0:
            raise OrderError("quantity must be positive")
        if product.stock >= 0 and product.stock < qty:
            raise OrderError(f"only {product.stock} left in stock")
        total = product.price_cents * qty
        cur = self.conn.execute(
            """INSERT INTO orders
               (buyer_id, buyer_name, product_id, qty, total_cents,
                pay_method, status, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (buyer_id, buyer_name or "", product_id, qty, total,
             pay_method, AWAITING_PAYMENT, self.clock()),
        )
        self.conn.commit()
        if product.stock >= 0:
            self.catalog.adjust_stock(product_id, -qty)
        return self.get(cur.lastrowid)

    def get(self, order_id: int) -> Order | None:
        row = self.conn.execute(
            "SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return Order.from_row(row) if row else None

    def list_for_buyer(self, buyer_id: int) -> list[Order]:
        rows = self.conn.execute(
            "SELECT * FROM orders WHERE buyer_id=? ORDER BY id DESC",
            (buyer_id,)).fetchall()
        return [Order.from_row(r) for r in rows]

    def pay_with_credit(self, order_id: int) -> Order:
        """One-tap payment from store credit."""
        order = self._get_for_update(order_id)
        if order.status != AWAITING_PAYMENT:
            raise OrderError(f"order #{order_id} is {order.status}")
        if order.pay_method != "credit":
            raise OrderError("order is not a credit order")
        try:
            self.credit.deduct(order.buyer_id, order.total_cents,
                               reason=f"order #{order_id}")
        except InsufficientCredit as e:
            raise OrderError(str(e)) from e
        return self._set_status(order_id, PAID, paid_now=True)

    def mark_paid(self, order_id: int) -> Order:
        """Admin confirmed the money arrived."""
        order = self._get_for_update(order_id)
        if order.status not in (AWAITING_PAYMENT, PAYMENT_SUBMITTED):
            raise OrderError(f"order #{order_id} is {order.status}")
        return self._set_status(order_id, PAID, paid_now=True)

    def complete(self, order_id: int) -> Order:
        order = self._get_for_update(order_id)
        if order.status != PAID:
            raise OrderError(f"order #{order_id} is {order.status}")
        return self._set_status(order_id, COMPLETED)

    def cancel(self, order_id: int) -> Order:
        order = self._get_for_update(order_id)
        if order.status != AWAITING_PAYMENT:
            raise OrderError(f"order #{order_id} is {order.status}")
        self._restock(order)
        return self._set_status(order_id, CANCELLED)

    def mark_refunded(self, order_id: int) -> Order:
        order = self._get_for_update(order_id)
        if order.status not in (PAYMENT_SUBMITTED, PAID):
            raise OrderError(f"order #{order_id} is {order.status}")
        self._restock(order)
        return self._set_status(order_id, REFUNDED)

    # -- internals ----------------------------------------------------
    def _get_for_update(self, order_id: int) -> Order:
        order = self.get(order_id)
        if order is None:
            raise OrderError(f"no order #{order_id}")
        return order

    def _set_status(self, order_id: int, status: str,
                    paid_now: bool = False) -> Order:
        if paid_now:
            self.conn.execute(
                "UPDATE orders SET status=?, paid_at=? WHERE id=?",
                (status, self.clock(), order_id))
        else:
            self.conn.execute("UPDATE orders SET status=? WHERE id=?",
                              (status, order_id))
        self.conn.commit()
        return self.get(order_id)

    def _restock(self, order: Order) -> None:
        product = self.catalog.get(order.product_id)
        if product and product.stock >= 0:
            self.catalog.adjust_stock(order.product_id, order.qty)

    def set_payment_submitted(self, order_id: int, txid: str) -> Order:
        order = self._get_for_update(order_id)
        if order.status != AWAITING_PAYMENT:
            raise OrderError(f"order #{order_id} is {order.status}")
        self.conn.execute(
            "UPDATE orders SET status=?, txid=? WHERE id=?",
            (PAYMENT_SUBMITTED, txid, order_id))
        self.conn.commit()
        return self.get(order_id)

    def back_to_awaiting(self, order_id: int) -> Order:
        """Return an order to awaiting payment (e.g. review ignored)."""
        order = self._get_for_update(order_id)
        if order.status != PAYMENT_SUBMITTED:
            raise OrderError(f"order #{order_id} is {order.status}")
        self.conn.execute(
            "UPDATE orders SET status=?, txid=NULL WHERE id=?",
            (AWAITING_PAYMENT, order_id))
        self.conn.commit()
        return self.get(order_id)
