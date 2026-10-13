"""Subscriptions: recurring products (e.g. a 30-day membership).

Renewals are charged against store credit — one tap for the buyer, zero
chasing for the seller. If credit runs dry the subscription goes past_due
and the buyer gets a nudge instead of silent churn.
"""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone

from . import alerts
from .catalog import CatalogService
from .credit import CreditService, InsufficientCredit
from .i18n import t, fmt_money
from .models import Subscription

DAY = 86400.0


class SubscriptionError(Exception):
    pass


def _date(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


class SubscriptionService:
    def __init__(self, conn: sqlite3.Connection, catalog: CatalogService,
                 credit: CreditService, clock=time.time):
        self.conn = conn
        self.catalog = catalog
        self.credit = credit
        self.clock = clock

    def subscribe(self, user_id: int, product_id: int,
                  lang: str = "en") -> Subscription:
        product = self.catalog.get(product_id)
        if product is None or not product.active:
            raise SubscriptionError(f"product #{product_id} not available")
        if not product.is_subscription:
            raise SubscriptionError(f"#{product_id} is not a subscription")
        now = self.clock()
        try:
            self.credit.deduct(user_id, product.price_cents,
                               reason=f"subscribe #{product_id} {product.name}")
        except InsufficientCredit as e:
            raise SubscriptionError(str(e)) from e
        cur = self.conn.execute(
            """INSERT INTO subscriptions
               (user_id, product_id, status, started_at, renews_at, last_paid_at)
               VALUES (?,?,?,?,?,?)""",
            (user_id, product_id, "active", now,
             now + product.billing_days * DAY, now),
        )
        self.conn.commit()
        sub = self.get(cur.lastrowid)
        alerts.add_alert(
            self.conn, user_id, "info",
            t("subscribed", lang, name=product.name,
              price=fmt_money(product.price_cents),
              days=product.billing_days, date=_date(sub.renews_at)),
            self.clock)
        return sub

    def get(self, sub_id: int) -> Subscription | None:
        row = self.conn.execute(
            "SELECT * FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
        return Subscription.from_row(row) if row else None

    def mysubs(self, user_id: int) -> list[Subscription]:
        rows = self.conn.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND status != 'cancelled'"
            " ORDER BY id", (user_id,)).fetchall()
        return [Subscription.from_row(r) for r in rows]

    def cancel(self, sub_id: int, user_id: int) -> Subscription:
        sub = self.get(sub_id)
        if sub is None or sub.user_id != user_id:
            raise SubscriptionError(f"no subscription #{sub_id}")
        self.conn.execute("UPDATE subscriptions SET status='cancelled' WHERE id=?",
                          (sub_id,))
        self.conn.commit()
        return self.get(sub_id)

    def renewals_due(self, now: float | None = None) -> list[Subscription]:
        now = self.clock() if now is None else now
        rows = self.conn.execute(
            "SELECT * FROM subscriptions WHERE status='active' AND renews_at <= ?"
            " ORDER BY renews_at", (now,)).fetchall()
        return [Subscription.from_row(r) for r in rows]

    def renew(self, sub_id: int, lang: str = "en") -> Subscription:
        """Charge one period of credit; on failure mark past_due + alert."""
        sub = self.get(sub_id)
        if sub is None:
            raise SubscriptionError(f"no subscription #{sub_id}")
        if sub.status != "active":
            raise SubscriptionError(f"subscription #{sub_id} is {sub.status}")
        product = self.catalog.get(sub.product_id)
        now = self.clock()
        try:
            self.credit.deduct(sub.user_id, product.price_cents,
                               reason=f"renew sub #{sub_id} {product.name}")
        except InsufficientCredit:
            self.conn.execute(
                "UPDATE subscriptions SET status='past_due' WHERE id=?", (sub_id,))
            self.conn.commit()
            alerts.add_alert(self.conn, sub.user_id, "renewal",
                             t("renew_failed", lang, name=product.name),
                             self.clock)
            return self.get(sub_id)
        new_renews = max(sub.renews_at, now) + product.billing_days * DAY
        self.conn.execute(
            "UPDATE subscriptions SET renews_at=?, last_paid_at=? WHERE id=?",
            (new_renews, now, sub_id))
        self.conn.commit()
        alerts.add_alert(
            self.conn, sub.user_id, "renewal",
            t("renewed", lang, name=product.name,
              price=fmt_money(product.price_cents), date=_date(new_renews)),
            self.clock)
        return self.get(sub_id)
