"""Shop: one facade wiring all services together.

The bot, the demo and the tests all talk to Shop — never to raw SQL.
Cross-service flows (price change -> wishlist alerts, payment -> review
queue) live here, so the individual services stay independent.
"""
from __future__ import annotations

import sqlite3
import time

from . import alerts
from .catalog import CatalogService
from .config import ShopConfig
from .credit import CreditService
from .db import init_schema
from .i18n import t, fmt_money
from .models import Alert, Order, Payment, Product, ReviewItem
from .orders import OrderService
from .payments import PaymentService
from .review_queue import ReviewService
from .subscriptions import SubscriptionService
from .wishlist import WishlistService


class Shop:
    def __init__(self, conn: sqlite3.Connection,
                 config: ShopConfig | None = None, clock=time.time):
        self.conn = conn
        self.config = config or ShopConfig()
        self.clock = clock
        init_schema(conn)
        self.catalog = CatalogService(conn, clock)
        self.credit = CreditService(conn, clock)
        self.orders = OrderService(conn, self.catalog, self.credit, clock)
        self.payments = PaymentService(conn, self.orders, clock)
        self.review = ReviewService(conn, self.payments, clock)
        self.wishlist = WishlistService(conn, clock)
        self.subs = SubscriptionService(conn, self.catalog, self.credit, clock)

    # -- cross-service flows -----------------------------------------
    def set_product_price(self, product_id: int, new_cents: int,
                          lang: str = "en") -> dict:
        product, old_cents = self.catalog.set_price(product_id, new_cents)
        notified = self.wishlist.notify_price_drop(product, old_cents, lang)
        return {"product": product, "old_cents": old_cents,
                "notified": notified}

    def submit_usdt_payment(self, order_id: int, txid: str, amount_cents: int,
                            sender_note: str = "") -> dict:
        payment, flags, risk = self.payments.submit_usdt(
            order_id, txid, amount_cents, sender_note)
        reason = "+".join(flags) if flags else "manual_review"
        item = self.review.record(order_id, reason, risk)
        return {"payment": payment, "flags": flags,
                "risk_score": risk, "review_item": item}

    # -- alerts --------------------------------------------------------
    def alerts_for(self, user_id: int) -> list[Alert]:
        return alerts.unread_for(self.conn, user_id)

    def mark_alerts_read(self, user_id: int) -> int:
        return alerts.mark_read(self.conn, user_id)

    # -- demo seeding --------------------------------------------------
    def seed_demo_catalog(self) -> list[Product]:
        """Three realistic products for the demo / first run."""
        return [
            self.catalog.add_product(
                "Hand-poured soy candle",
                "Cedar & amber, 220g. Ships worldwide.",
                2500, stock=20),
            self.catalog.add_product(
                "Daigou slot — sneakers drop",
                "One guaranteed pair, your size, this week's drop.",
                9900, stock=5),
            self.catalog.add_product(
                "Insider deals channel",
                "Daily price-error alerts, members only.",
                1500, kind="subscription", billing_days=30),
        ]
