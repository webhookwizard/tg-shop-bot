"""Wishlist: buyers watch products, the shop pings them on price drops.

Turns one-time browsers into repeat buyers — the cheapest "marketing"
a small seller has.
"""
from __future__ import annotations

import sqlite3
import time

from . import alerts
from .i18n import t, fmt_money
from .models import Product


class WishlistService:
    def __init__(self, conn: sqlite3.Connection, clock=time.time):
        self.conn = conn
        self.clock = clock

    def add(self, user_id: int, product_id: int) -> bool:
        """Watch a product. Returns True if newly added."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO wishlist (user_id, product_id, added_at)"
            " VALUES (?,?,?)", (user_id, product_id, self.clock()))
        self.conn.commit()
        return cur.rowcount == 1

    def remove(self, user_id: int, product_id: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM wishlist WHERE user_id=? AND product_id=?",
            (user_id, product_id))
        self.conn.commit()
        return cur.rowcount == 1

    def list_for(self, user_id: int) -> list[Product]:
        rows = self.conn.execute(
            """SELECT p.* FROM products p
               JOIN wishlist w ON w.product_id = p.id
               WHERE w.user_id=? AND p.active=1 ORDER BY w.added_at""",
            (user_id,)).fetchall()
        return [Product.from_row(r) for r in rows]

    def watchers_of(self, product_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT user_id FROM wishlist WHERE product_id=?", (product_id,)
        ).fetchall()
        return [r["user_id"] for r in rows]

    def notify_price_drop(self, product: Product, old_cents: int,
                          lang: str = "en") -> int:
        """Alert every watcher about a price drop. Returns watcher count."""
        if product.price_cents >= old_cents:
            return 0
        text = t("price_drop", lang, name=product.name,
                 new=fmt_money(product.price_cents),
                 old=fmt_money(old_cents))
        count = 0
        for user_id in self.watchers_of(product.id):
            alerts.add_alert(self.conn, user_id, "price_drop", text, self.clock)
            count += 1
        return count
