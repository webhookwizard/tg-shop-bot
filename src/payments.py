"""USDT payments, two paths.

1. Manual TXID path (default, zero API keys): the buyer sends USDT to the
   seller's address, then submits the transaction ID. Every submission lands
   in the review queue; the seller confirms the money on-chain and approves.
   Honest limit: the bot cannot verify the chain by itself — the seller's
   eyes are the verification. That is exactly how thousands of small
   Telegram sellers already operate; the bot just organizes it.

2. CryptoBot path (optional): hosted invoices with automatic confirmation
   via the CryptoBot API. Needs a CRYPTOBOT_TOKEN. Documented below and in
   the README; never required.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import urllib.request
import urllib.error

from .models import Payment
from .orders import OrderService, AWAITING_PAYMENT

TXID_RE = re.compile(r"^[A-Za-z0-9]{8,128}$")

# Risk weights for the review queue.
RISK_WEIGHTS = {
    "amount_mismatch": 40,   # paid != order total
    "first_big_order": 20,   # first purchase and >= $50
    "prior_refund": 30,      # buyer was refunded before
}
BIG_ORDER_CENTS = 5000  # $50


class PaymentError(Exception):
    pass


class InvalidTxidError(PaymentError):
    pass


class DuplicateTxidError(PaymentError):
    pass


class PaymentService:
    def __init__(self, conn: sqlite3.Connection, orders: OrderService,
                 clock=time.time):
        self.conn = conn
        self.orders = orders
        self.clock = clock

    def submit_usdt(self, order_id: int, txid: str, amount_cents: int,
                    sender_note: str = "") -> tuple[Payment, list[str], int]:
        """Buyer submits a TXID. Returns (payment, flags, risk_score).

        Raises InvalidTxidError / DuplicateTxidError / OrderError.
        """
        order = self.orders.get(order_id)
        if order is None:
            raise PaymentError(f"no order #{order_id}")
        if order.status != AWAITING_PAYMENT:
            raise PaymentError(f"order #{order_id} is {order.status}")
        txid = (txid or "").strip()
        if not TXID_RE.match(txid):
            raise InvalidTxidError("txid must be 8-128 letters/digits")
        if self.find_by_txid(txid) is not None:
            raise DuplicateTxidError("txid already used")

        flags: list[str] = []
        if amount_cents != order.total_cents:
            flags.append("amount_mismatch")
        if self._is_first_big_order(order):
            flags.append("first_big_order")
        if self._has_prior_refund(order.buyer_id):
            flags.append("prior_refund")
        risk = sum(RISK_WEIGHTS[f] for f in flags)

        cur = self.conn.execute(
            """INSERT INTO payments
               (order_id, txid, amount_cents, sender_note, status, created_at)
               VALUES (?,?,?,?,?,?)""",
            (order_id, txid, amount_cents, sender_note,
             "submitted", self.clock()),
        )
        self.conn.commit()
        self.orders.set_payment_submitted(order_id, txid)
        row = self.conn.execute(
            "SELECT * FROM payments WHERE id=?", (cur.lastrowid,)).fetchone()
        return Payment.from_row(row), flags, risk

    def find_by_txid(self, txid: str) -> Payment | None:
        row = self.conn.execute(
            "SELECT * FROM payments WHERE txid=?", (txid,)).fetchone()
        return Payment.from_row(row) if row else None

    def payment_for_order(self, order_id: int) -> Payment | None:
        row = self.conn.execute(
            "SELECT * FROM payments WHERE order_id=? ORDER BY id DESC LIMIT 1",
            (order_id,)).fetchone()
        return Payment.from_row(row) if row else None

    def confirm(self, payment_id: int) -> Payment:
        self.conn.execute("UPDATE payments SET status='confirmed' WHERE id=?",
                          (payment_id,))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        payment = Payment.from_row(row)
        self.orders.mark_paid(payment.order_id)
        return payment

    def reject(self, payment_id: int) -> Payment:
        self.conn.execute("UPDATE payments SET status='rejected' WHERE id=?",
                          (payment_id,))
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
        return Payment.from_row(row)

    # -- flag helpers -------------------------------------------------
    def _is_first_big_order(self, order) -> bool:
        if order.total_cents < BIG_ORDER_CENTS:
            return False
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE buyer_id=? AND status IN"
            " ('paid','completed') AND id != ?",
            (order.buyer_id, order.id)).fetchone()
        return int(row["n"]) == 0

    def _has_prior_refund(self, buyer_id: int) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM orders WHERE buyer_id=? AND status='refunded'",
            (buyer_id,)).fetchone()
        return int(row["n"]) > 0


class CryptoBotError(Exception):
    pass


class CryptoBotClient:
    """Optional CryptoBot (https://pay.crypt.bot) invoice integration.

    With a CRYPTOBOT_TOKEN the shop can issue hosted USDT invoices that
    auto-confirm on payment — no manual TXID step. Without it, everything
    still works through the manual path above. Stdlib only (urllib).
    """

    def __init__(self, token: str,
                 base_url: str = "https://pay.crypt.bot/api"):
        if not token:
            raise CryptoBotError("CRYPTOBOT_TOKEN is required")
        self.token = token
        self.base_url = base_url.rstrip("/")

    def build_invoice_payload(self, amount_usdt: str, payload: str = "",
                              description: str = "") -> dict:
        """Pure function — no network. Unit-testable."""
        return {
            "asset": "USDT",
            "amount": str(amount_usdt),
            "payload": payload,
            "description": description[:1024],
        }

    def _call(self, method: str, params: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}/{method}",
            data=json.dumps(params).encode(),
            headers={"Crypto-Pay-API-Token": self.token,
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise CryptoBotError(f"network error: {e}") from e
        if not data.get("ok"):
            raise CryptoBotError(f"api error: {data.get('error')}")
        return data["result"]

    def create_invoice(self, amount_usdt: str, payload: str = "",
                       description: str = "") -> dict:
        """Returns the invoice dict (includes 'bot_invoice_url')."""
        return self._call("createInvoice",
                          self.build_invoice_payload(amount_usdt, payload,
                                                     description))

    def invoice_status(self, invoice_id: int) -> str:
        """Returns the invoice status ('active' | 'paid' | ...)."""
        result = self._call("getInvoices", {"invoice_ids": [invoice_id]})
        items = result.get("items", [])
        if not items:
            raise CryptoBotError(f"invoice {invoice_id} not found")
        return items[0].get("status", "unknown")
