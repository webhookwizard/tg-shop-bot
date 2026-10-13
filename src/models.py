"""Plain data objects. Services return these; the bot and demo print them."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class Product:
    id: int
    name: str
    description: str
    price_cents: int
    kind: str = "once"  # "once" | "subscription"
    billing_days: int = 0
    stock: int = -1  # -1 = unlimited
    active: bool = True
    created_at: float = 0.0

    @property
    def is_subscription(self) -> bool:
        return self.kind == "subscription"

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "Product":
        return cls(
            id=r["id"], name=r["name"], description=r["description"],
            price_cents=r["price_cents"], kind=r["kind"],
            billing_days=r["billing_days"], stock=r["stock"],
            active=bool(r["active"]), created_at=r["created_at"],
        )


@dataclass
class Order:
    id: int
    buyer_id: int
    buyer_name: str
    product_id: int
    qty: int
    total_cents: int
    pay_method: str = "usdt_manual"
    status: str = "awaiting_payment"
    txid: str | None = None
    created_at: float = 0.0
    paid_at: float | None = None

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "Order":
        return cls(
            id=r["id"], buyer_id=r["buyer_id"], buyer_name=r["buyer_name"],
            product_id=r["product_id"], qty=r["qty"], total_cents=r["total_cents"],
            pay_method=r["pay_method"], status=r["status"], txid=r["txid"],
            created_at=r["created_at"], paid_at=r["paid_at"],
        )


@dataclass
class Payment:
    id: int
    order_id: int
    txid: str
    amount_cents: int
    sender_note: str = ""
    status: str = "submitted"  # submitted | confirmed | rejected
    created_at: float = 0.0

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "Payment":
        return cls(
            id=r["id"], order_id=r["order_id"], txid=r["txid"],
            amount_cents=r["amount_cents"], sender_note=r["sender_note"],
            status=r["status"], created_at=r["created_at"],
        )


@dataclass
class ReviewItem:
    id: int
    order_id: int
    reason: str
    risk_score: int = 0
    status: str = "open"  # open | approved | refunded | ignored
    created_at: float = 0.0
    decided_at: float | None = None

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "ReviewItem":
        return cls(
            id=r["id"], order_id=r["order_id"], reason=r["reason"],
            risk_score=r["risk_score"], status=r["status"],
            created_at=r["created_at"], decided_at=r["decided_at"],
        )


@dataclass
class Subscription:
    id: int
    user_id: int
    product_id: int
    status: str = "active"  # active | past_due | cancelled
    started_at: float = 0.0
    renews_at: float = 0.0
    last_paid_at: float | None = None

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "Subscription":
        return cls(
            id=r["id"], user_id=r["user_id"], product_id=r["product_id"],
            status=r["status"], started_at=r["started_at"],
            renews_at=r["renews_at"], last_paid_at=r["last_paid_at"],
        )


@dataclass
class Alert:
    id: int
    user_id: int
    kind: str  # price_drop | renewal | payment | info
    text: str
    created_at: float = 0.0
    read: bool = False

    @classmethod
    def from_row(cls, r: sqlite3.Row) -> "Alert":
        return cls(
            id=r["id"], user_id=r["user_id"], kind=r["kind"], text=r["text"],
            created_at=r["created_at"], read=bool(r["read"]),
        )
