#!/usr/bin/env python
"""One-command demo: a full customer journey with ZERO api keys and
ZERO network. Everything runs against an in-memory database.

Run:  python demo.py
"""
import os
import sys

if sys.platform == "win32":  # pragma: no cover
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import ShopConfig
from src.db import connect
from src.i18n import fmt_money, t
from src.shop import Shop

BAR = "=" * 64


def section(title):
    print(f"\n{BAR}\n{title}\n{BAR}")


def main():
    now = [1_700_000_000.0]
    config = ShopConfig(
        shop_name="Mei's Corner Store",
        usdt_address="TXdemoAddr123456789",
        usdt_network="TRC20",
        admin_ids=(9001,),
    )
    shop = Shop(connect(":memory:"), config, clock=lambda: now[0])
    MEILIN, ADMIN = 1001, 9001

    section("SETUP — no API keys, no network, in-memory database")
    products = shop.seed_demo_catalog()
    for p in products:
        kind = f" (subscription, {p.billing_days}d)" if p.is_subscription else ""
        print(f"  #{p.id} {p.name} — {fmt_money(p.price_cents)} USDT{kind}")

    section("1. BUYER BROWSES + WATCHES — Mei eyes the candle")
    print("  Mei: /catalog  -> sees 3 products")
    shop.wishlist.add(MEILIN, 1)
    print("  Mei: /watch 1  ->", t("wishlist_added", "en", id=1,
                                   name="Hand-poured soy candle"))

    section("2. PRICE DROP — admin lowers the candle to 19.99 USDT")
    res = shop.set_product_price(1, 1999, lang="cn")
    print(f"  admin: /price 1 19.99  -> {res['notified']} watcher notified")
    for a in shop.alerts_for(MEILIN):
        print(f"  >> alert to Mei: {a.text}")
    shop.mark_alerts_read(MEILIN)

    section("3. ORDER — Mei buys the candle, pays USDT by TXID")
    order = shop.orders.create_order(MEILIN, "Mei", 1, qty=1)
    print("  Mei: /buy 1")
    print("  bot:", t("order_created", "en", id=order.id, qty=1,
                       name="Hand-poured soy candle",
                       total=fmt_money(order.total_cents)).replace("\n", " "))
    print("  Mei sends 19.99 USDT to", config.usdt_address)
    print("  Mei: /pay 1 TXN7F2KQ9DEMO001")
    result = shop.submit_usdt_payment(order.id, "TXN7F2KQ9DEMO001", 1999)
    print("  bot:", t("txid_received", "en", id=order.id).replace("\n", " "))
    print(f"  -> review queue: risk={result['risk_score']} "
          f"({result['review_item'].reason})")

    section("4. REVIEW QUEUE — admin approves, order completes")
    for item in shop.review.open_with_orders():
        print(f"  admin sees: order #{item['order_id']} "
              f"{fmt_money(item['total_cents'])} USDT "
              f"risk={item['risk_score']} ({item['reason']})")
    shop.review.approve(result["review_item"].id)
    shop.orders.complete(order.id)
    print("  admin: /approve 1  ->", t("order_paid", "en", id=order.id))
    print("  order status:", shop.orders.get(order.id).status)

    section("5. FLAGGED PAYMENT — Leo underpays, admin refunds")
    leo_order = shop.orders.create_order(1002, "Leo", 2, qty=1)  # 99.00 USDT
    print("  Leo: /buy 2  (daigou slot, 99.00 USDT)")
    print("  Leo sends only 90.00 USDT, submits TXID anyway")
    bad = shop.submit_usdt_payment(leo_order.id, "TXNLEO000BAD999", 9000)
    print(f"  -> review queue: risk={bad['risk_score']} "
          f"({bad['review_item'].reason})  <- amount mismatch flagged")
    shop.review.refund(bad["review_item"].id, reason="amount mismatch")
    print("  admin: /refund 2 ->",
          t("order_refunded", "en", id=leo_order.id,
            reason="amount mismatch"))
    print("  order status:", shop.orders.get(leo_order.id).status)

    section("6. CREDIT + SUBSCRIPTION — Mei joins the deals channel")
    shop.credit.grant(MEILIN, 4000, reason="welcome bonus", admin="admin")
    print("  admin: /grant 1001 40 ->",
          t("balance_line", "en",
            amount=fmt_money(shop.credit.balance(MEILIN))))
    sub = shop.subs.subscribe(MEILIN, 3, lang="en")
    print("  Mei: /sub 3  (pays 15.00 USDT from credit, no TXID needed)")
    for a in shop.alerts_for(MEILIN):
        print(f"  >> alert to Mei: {a.text}")
    shop.mark_alerts_read(MEILIN)

    section("7. RENEWAL — 31 days later, auto-renewed from credit")
    now[0] += 31 * 86400
    due = shop.subs.renewals_due()
    print(f"  renewals due: {len(due)}")
    for s in due:
        shop.subs.renew(s.id)
    for a in shop.alerts_for(MEILIN):
        print(f"  >> alert to Mei: {a.text}")
    print("  Mei's credit left:",
          fmt_money(shop.credit.balance(MEILIN)), "USDT")

    section("DEMO COMPLETE")
    print("  Covered: catalog, wishlist + price-drop alerts, USDT TXID")
    print("  payments, review queue (approve + refund), store credit,")
    print("  subscriptions + auto-renewal.")
    print("  Real bot: set BOT_TOKEN + ADMIN_IDS and run")
    print("  'python -m src.bot'. See README.md.")


if __name__ == "__main__":
    main()
