"""Product catalog: what the shop sells."""
from __future__ import annotations

import sqlite3
import time

from .models import Product


class CatalogError(Exception):
    pass


class CatalogService:
    def __init__(self, conn: sqlite3.Connection, clock=time.time):
        self.conn = conn
        self.clock = clock

    def add_product(self, name: str, description: str = "",
                    price_cents: int = 0, kind: str = "once",
                    billing_days: int = 0, stock: int = -1) -> Product:
        name = name.strip()
        if not name:
            raise CatalogError("product name is required")
        if price_cents < 0:
            raise CatalogError("price cannot be negative")
        if kind not in ("once", "subscription"):
            raise CatalogError("kind must be 'once' or 'subscription'")
        if kind == "subscription" and billing_days <= 0:
            raise CatalogError("subscription products need billing_days > 0")
        cur = self.conn.execute(
            """INSERT INTO products
               (name, description, price_cents, kind, billing_days, stock, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (name, description, price_cents, kind, billing_days, stock, self.clock()),
        )
        self.conn.commit()
        return self.get(cur.lastrowid)

    def get(self, product_id: int) -> Product | None:
        row = self.conn.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        return Product.from_row(row) if row else None

    def list_active(self) -> list[Product]:
        rows = self.conn.execute(
            "SELECT * FROM products WHERE active=1 ORDER BY id").fetchall()
        return [Product.from_row(r) for r in rows]

    def set_price(self, product_id: int, new_cents: int) -> tuple[Product, int]:
        """Change price; returns (product, old_price_cents)."""
        product = self.get(product_id)
        if product is None:
            raise CatalogError(f"no product #{product_id}")
        if new_cents < 0:
            raise CatalogError("price cannot be negative")
        old = product.price_cents
        self.conn.execute("UPDATE products SET price_cents=? WHERE id=?",
                          (new_cents, product_id))
        self.conn.commit()
        return self.get(product_id), old

    def set_active(self, product_id: int, active: bool) -> Product:
        if self.get(product_id) is None:
            raise CatalogError(f"no product #{product_id}")
        self.conn.execute("UPDATE products SET active=? WHERE id=?",
                          (1 if active else 0, product_id))
        self.conn.commit()
        return self.get(product_id)

    def adjust_stock(self, product_id: int, delta: int) -> Product:
        product = self.get(product_id)
        if product is None:
            raise CatalogError(f"no product #{product_id}")
        if product.stock >= 0:
            new_stock = max(0, product.stock + delta)
            self.conn.execute("UPDATE products SET stock=? WHERE id=?",
                              (new_stock, product_id))
            self.conn.commit()
        return self.get(product_id)
