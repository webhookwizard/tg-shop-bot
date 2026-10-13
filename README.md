# tg-shop-bot

**Your Telegram storefront that takes USDT — no website, no monthly fees, no missed midnight orders.**

中文说明 → [README_CN.md](README_CN.md)

## Demo

One command, zero API keys, zero network — watch a full customer journey:

```
$ python demo.py

  #1 Hand-poured soy candle — 25.00 USDT
  #2 Daigou slot — sneakers drop — 99.00 USDT
  #3 Insider deals channel — 15.00 USDT (subscription, 30d)

  Mei: /watch 1  -> Watching #1 Hand-poured soy candle. I'll ping you if the price drops.
  admin: /price 1 19.99  -> 1 watcher notified
  >> alert to Mei: Price drop: Hand-poured soy candle is now 19.99 USDT (was 25.00).

  Mei: /buy 1
  bot: Order #1: 1 x Hand-poured soy candle = 19.99 USDT.
  Mei sends 19.99 USDT, then: /pay 1 TXN7F2KQ9DEMO001
  bot: TXID received for order #1. The seller will confirm it — usually within a few hours.
  -> review queue: risk=0 (manual_review)

  admin: /approve 1  -> Order #1 is paid. Thank you!

  Leo sends only 90.00 USDT for a 99.00 order...
  -> review queue: risk=60 (amount_mismatch+first_big_order)  <- flagged
  admin: /refund 2 -> Order #2 was refunded (amount mismatch).

  admin: /grant 1001 40 -> Your store credit: 40.00 USDT.
  Mei: /sub 3  (pays 15.00 USDT from credit, no TXID needed)
  ...31 days later: auto-renewed from credit. Mei's credit left: 10.00 USDT.
```

## The problem

Mei sells candles to 300 regulars in a Telegram group. Every order is a DM, every payment a screenshot, every "did you get my USDT?" a 20-minute back-and-forth. On drop nights she loses orders to slow replies — and one wrong address once cost her $120.

## What it does

- **Never lose a midnight order** — buyers browse and buy inside Telegram, 24/7, while you sleep
- **USDT without the headache** — buyer sends USDT, pastes the TXID; you confirm with one tap
- **Catch the cheats before they cost you** — underpayments, reused TXIDs and first-time big orders land in a review queue with a risk score, not in your DMs
- **Turn browsers into repeat buyers** — price-drop alerts bring watchers back on their own
- **Regulars pay in one tap** — store credit means no TXID round-trip for your best customers
- **Recurring revenue on autopilot** — subscriptions renew from credit; failed renewals nudge the buyer instead of silently churning
- **English and Chinese out of the box** — serve both crowds with one bot

## Try it in 2 minutes

```bash
git clone https://github.com/webhookwizard/tg-shop-bot.git
cd tg-shop-bot
python demo.py          # the full journey above, offline, no keys
```

Go live with the real bot:

```bash
pip install -r requirements.txt
cp .env.example .env    # fill in BOT_TOKEN (from @BotFather) + ADMIN_IDS
python -m src.bot
```

## How it works

<details>
<summary>Architecture, payment paths, and honest limits</summary>

**Stack:** Python 3.9+, `python-telegram-bot` for the Telegram layer, SQLite for everything else — one file holds the catalog, orders, payments, review queue, credit ledger, wishlists and subscriptions. Back up the business by copying one file.

**Two payment paths:**
1. **Manual TXID (default, zero API keys):** buyer sends USDT to your address and submits the transaction ID with `/pay`. Every submission enters the review queue; you verify on-chain and tap approve/refund/ignore. This is how most small Telegram sellers already operate — the bot just organizes it.
2. **CryptoBot (optional):** set `CRYPTOBOT_TOKEN` for hosted invoices with automatic confirmation. Never required.

**Review queue flags:** `amount_mismatch` (+40), `first_big_order` ≥ $50 (+20), `prior_refund` (+30), duplicate TXIDs rejected outright.

**Honest limits:**
- The manual path cannot verify the blockchain by itself — **your eyes are the verification**. Approve only what you see on-chain.
- The demo simulates payments; no real USDT moves.
- CryptoBot is a third-party service — check their current fees/docs before relying on it.

**Real costs:** $0 software cost. Buyers pay the chain fee (~$1 on TRON). Hosting: any $5/month VPS — or the computer you already own.

**Buyer commands:** `/catalog` `/buy` `/pay` `/myorders` `/balance` `/watch` `/wishlist` `/sub` `/mysubs` · **Admin:** `/review` `/approve` `/refund` `/ignore` `/grant` `/addproduct` `/price`
</details>

## What you save

No $29/month Shopify, no 2.9% card fees, no "sorry, I missed your DM" — orders take themselves while you do literally anything else.

---

> Want this customized for your shop? DM [@saulgoodmanc99](https://t.me/saulgoodmanc99) — custom builds from $99, settled in USDT.
