"""Telegram bot: thin adapter over Shop.

All business logic lives in src/shop.py — this file only translates
Telegram messages into Shop calls and Shop results into replies.
Run:  BOT_TOKEN=... ADMIN_IDS=123 python -m src.bot
"""
from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes)

from .config import ShopConfig
from .db import connect
from .i18n import t, fmt_money
from .orders import AWAITING_PAYMENT
from .shop import Shop

log = logging.getLogger(__name__)

# Ephemeral per-user language choice. (Restart clears it; fine for v1.)
_user_lang: dict[int, str] = {}


def _lang(update: Update, config: ShopConfig) -> str:
    uid = update.effective_user.id if update.effective_user else 0
    return _user_lang.get(uid, config.default_lang)


def _shop(ctx: ContextTypes.DEFAULT_TYPE) -> Shop:
    return ctx.application.bot_data["shop"]


def _config(ctx: ContextTypes.DEFAULT_TYPE) -> ShopConfig:
    return ctx.application.bot_data["config"]


def _is_admin(update: Update, config: ShopConfig) -> bool:
    return update.effective_user is not None and config.is_admin(
        update.effective_user.id)


def _admin_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update, _config(ctx)):
            await update.message.reply_text(t("not_admin", _lang(update, _config(ctx))))
            return
        return await func(update, ctx)
    return wrapper


# -- buyer commands ---------------------------------------------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = _config(ctx)
    await update.message.reply_text(
        t("welcome", _lang(update, cfg), shop=cfg.shop_name))


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t("help", _lang(update, _config(ctx))))


async def lang_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur = _user_lang.get(uid, _config(ctx).default_lang)
    new = "cn" if cur == "en" else "en"
    _user_lang[uid] = new
    await update.message.reply_text(t("lang_set", new))


async def catalog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    products = shop.catalog.list_active()
    if not products:
        await update.message.reply_text(t("catalog_empty", lang))
        return
    lines = [t("catalog_title", lang, shop=shop.config.shop_name), ""]
    for p in products:
        kind = t("kind_sub", lang, days=p.billing_days) if p.is_subscription else ""
        lines.append(t("product_line", lang, id=p.id, name=p.name,
                       price=fmt_money(p.price_cents), kind=kind,
                       desc=p.description or ""))
    await update.message.reply_text("\n".join(lines))


async def buy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, cfg, lang = _shop(ctx), _config(ctx), _lang(update, _config(ctx))
    if len(ctx.args) < 1:
        await update.message.reply_text(
            t("bad_args", lang, usage="/buy <product_id> [qty]"))
        return
    try:
        pid, qty = int(ctx.args[0]), int(ctx.args[1]) if len(ctx.args) > 1 else 1
    except ValueError:
        await update.message.reply_text(
            t("bad_args", lang, usage="/buy <product_id> [qty]"))
        return
    user = update.effective_user
    try:
        order = shop.orders.create_order(user.id, user.full_name, pid, qty)
    except Exception as e:  # ProductUnavailableError / OrderError
        await update.message.reply_text(
            t("unknown_product", lang) if "not available" in str(e) else str(e))
        return
    product = shop.catalog.get(pid)
    await update.message.reply_text(
        t("order_created", lang, id=order.id, qty=qty, name=product.name,
          total=fmt_money(order.total_cents)))
    await update.message.reply_text(
        t("pay_how_usdt", lang, total=fmt_money(order.total_cents),
          network=cfg.usdt_network, address=cfg.usdt_address,
          order_id=order.id))


async def pay(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if len(ctx.args) < 2:
        await update.message.reply_text(
            t("bad_args", lang, usage="/pay <order_id> <TXID>"))
        return
    try:
        order_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text(
            t("bad_args", lang, usage="/pay <order_id> <TXID>"))
        return
    txid = ctx.args[1]
    order = shop.orders.get(order_id)
    user = update.effective_user
    if order is None:
        await update.message.reply_text(t("no_such_order", lang))
        return
    if order.buyer_id != user.id and not _is_admin(update, _config(ctx)):
        await update.message.reply_text(t("not_your_order", lang))
        return
    amount = order.total_cents
    if len(ctx.args) > 2:
        try:
            amount = int(float(ctx.args[2]) * 100)
        except ValueError:
            pass
    try:
        shop.submit_usdt_payment(order_id, txid, amount)
    except Exception as e:
        msg = str(e)
        if "txid must be" in msg:
            await update.message.reply_text(t("bad_txid", lang))
        elif "already used" in msg:
            await update.message.reply_text(t("dup_txid", lang))
        else:
            await update.message.reply_text(t("wrong_state", lang, id=order_id))
        return
    await update.message.reply_text(t("txid_received", lang, id=order_id))


async def myorders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    orders = shop.orders.list_for_buyer(update.effective_user.id)
    if not orders:
        await update.message.reply_text(t("myorders_empty", lang))
        return
    lines = [t("myorders_title", lang)]
    for o in orders:
        p = shop.catalog.get(o.product_id)
        lines.append(t("order_line", lang, id=o.id, name=p.name if p else "?",
                       qty=o.qty, total=fmt_money(o.total_cents),
                       status=o.status))
    await update.message.reply_text("\n".join(lines))


async def balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    bal = shop.credit.balance(update.effective_user.id)
    await update.message.reply_text(
        t("balance_line", lang, amount=fmt_money(bal)))


async def watch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if not ctx.args:
        await update.message.reply_text(
            t("bad_args", lang, usage="/watch <product_id>"))
        return
    try:
        pid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text(
            t("bad_args", lang, usage="/watch <product_id>"))
        return
    product = shop.catalog.get(pid)
    if product is None or not product.active:
        await update.message.reply_text(t("unknown_product", lang))
        return
    shop.wishlist.add(update.effective_user.id, pid)
    await update.message.reply_text(
        t("wishlist_added", lang, id=pid, name=product.name))


async def unwatch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if ctx.args and ctx.args[0].isdigit():
        shop.wishlist.remove(update.effective_user.id, int(ctx.args[0]))
        await update.message.reply_text(
            t("wishlist_removed", lang, id=ctx.args[0]))
    else:
        await update.message.reply_text(
            t("bad_args", lang, usage="/unwatch <product_id>"))


async def wishlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    items = shop.wishlist.list_for(update.effective_user.id)
    if not items:
        await update.message.reply_text(t("wishlist_empty", lang))
        return
    lines = [t("wishlist_title", lang)]
    lines += [t("wishlist_line", lang, id=p.id, name=p.name,
                price=fmt_money(p.price_cents)) for p in items]
    await update.message.reply_text("\n".join(lines))


async def sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            t("bad_args", lang, usage="/sub <product_id>"))
        return
    pid = int(ctx.args[0])
    product = shop.catalog.get(pid)
    if product is None or not product.active or not product.is_subscription:
        await update.message.reply_text(t("unknown_product", lang))
        return
    uid = update.effective_user.id
    bal = shop.credit.balance(uid)
    if bal < product.price_cents:
        await update.message.reply_text(
            t("insufficient_credit", lang,
              need=fmt_money(product.price_cents), have=fmt_money(bal)))
        return
    try:
        s = shop.subs.subscribe(uid, pid, lang)
    except Exception:
        await update.message.reply_text(t("unknown_product", lang))
        return
    product = shop.catalog.get(s.product_id)
    await update.message.reply_text(
        t("subscribed", lang, name=product.name,
          price=fmt_money(product.price_cents), days=product.billing_days,
          date=s.renews_at))


async def mysubs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    subs = shop.subs.mysubs(update.effective_user.id)
    if not subs:
        await update.message.reply_text(t("mysubs_empty", lang))
        return
    lines = [t("mysubs_title", lang)]
    for s in subs:
        p = shop.catalog.get(s.product_id)
        lines.append(t("sub_line", lang, id=s.id, name=p.name if p else "?",
                       status=s.status, date=s.renews_at))
    await update.message.reply_text("\n".join(lines))


# -- admin commands ---------------------------------------------------
@_admin_only
async def review(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    items = shop.review.open_with_orders()
    if not items:
        await update.message.reply_text(t("review_empty", lang))
        return
    lines = [t("review_title", lang, n=len(items))]
    lines += [t("review_line", lang, id=i["id"], order=i["order_id"],
                total=fmt_money(i["total_cents"]), risk=i["risk_score"],
                reason=i["reason"]) for i in items]
    await update.message.reply_text("\n".join(lines))


@_admin_only
async def approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            t("bad_args", lang, usage="/approve <review_id>"))
        return
    try:
        item = shop.review.approve(int(ctx.args[0]))
    except Exception:
        await update.message.reply_text(t("review_empty", lang))
        return
    await update.message.reply_text(
        t("review_approved", lang, order=item.order_id))


@_admin_only
async def refund(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            t("bad_args", lang, usage="/refund <review_id>"))
        return
    try:
        item = shop.review.refund(int(ctx.args[0]))
    except Exception:
        await update.message.reply_text(t("review_empty", lang))
        return
    await update.message.reply_text(
        t("review_refunded", lang, order=item.order_id))


@_admin_only
async def ignore(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text(
            t("bad_args", lang, usage="/ignore <review_id>"))
        return
    try:
        item = shop.review.ignore(int(ctx.args[0]))
    except Exception:
        await update.message.reply_text(t("review_empty", lang))
        return
    await update.message.reply_text(
        t("review_ignored", lang, order=item.order_id))


@_admin_only
async def grant(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if len(ctx.args) < 2 or not ctx.args[0].isdigit():
        await update.message.reply_text(
            t("bad_args", lang, usage="/grant <user_id> <amount_usdt>"))
        return
    try:
        cents = int(float(ctx.args[1]) * 100)
    except ValueError:
        await update.message.reply_text(
            t("bad_args", lang, usage="/grant <user_id> <amount_usdt>"))
        return
    bal = shop.credit.grant(int(ctx.args[0]), cents, reason="admin top-up",
                            admin=str(update.effective_user.id))
    await update.message.reply_text(
        t("credit_granted", lang, amount=fmt_money(cents))
        + f" (balance now {fmt_money(bal)} USDT)")


@_admin_only
async def addproduct(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    # /addproduct <name> | <price_usdt> | [once|sub:<days>] | [description]
    parts = " ".join(ctx.args).split("|")
    if len(parts) < 2:
        await update.message.reply_text(
            t("bad_args", lang,
              usage="/addproduct <name> | <price_usdt> | [once|sub:<days>]"))
        return
    try:
        price_cents = int(float(parts[1].strip()) * 100)
    except ValueError:
        await update.message.reply_text(t("bad_args", lang, usage="price"))
        return
    kind, billing = "once", 0
    if len(parts) > 2 and parts[2].strip().startswith("sub:"):
        kind = "subscription"
        billing = int(parts[2].strip().split(":")[1])
    desc = parts[3].strip() if len(parts) > 3 else ""
    try:
        p = shop.catalog.add_product(parts[0].strip(), desc, price_cents,
                                     kind=kind, billing_days=billing)
    except Exception as e:
        await update.message.reply_text(str(e))
        return
    await update.message.reply_text(
        t("added_product", lang, id=p.id, name=p.name,
          price=fmt_money(p.price_cents)))


@_admin_only
async def price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    shop, lang = _shop(ctx), _lang(update, _config(ctx))
    if len(ctx.args) < 2:
        await update.message.reply_text(
            t("bad_args", lang, usage="/price <product_id> <new_price_usdt>"))
        return
    try:
        res = shop.set_product_price(int(ctx.args[0]),
                                     int(float(ctx.args[1]) * 100), lang)
    except Exception as e:
        await update.message.reply_text(str(e))
        return
    p = res["product"]
    await update.message.reply_text(
        f"#{p.id} {p.name}: {fmt_money(res['old_cents'])} -> "
        f"{fmt_money(p.price_cents)} USDT "
        f"({res['notified']} watchers notified)")


# -- periodic jobs -----------------------------------------------------
async def _renewal_job(ctx: ContextTypes.DEFAULT_TYPE):
    """Hourly: charge due subscriptions, deliver pending alerts."""
    shop: Shop = ctx.application.bot_data["shop"]
    for sub in shop.subs.renewals_due():
        shop.subs.renew(sub.id)
        await _deliver_alerts(ctx, sub.user_id)


async def _deliver_alerts(ctx: ContextTypes.DEFAULT_TYPE, user_id: int):
    shop: Shop = ctx.application.bot_data["shop"]
    for alert in shop.alerts_for(user_id):
        try:
            await ctx.bot.send_message(chat_id=user_id, text=alert.text)
        except Exception as e:  # user blocked the bot etc.
            log.warning("alert to %s failed: %s", user_id, e)
            break
    shop.mark_alerts_read(user_id)


def build_app(config: ShopConfig, shop: Shop) -> Application:
    app = Application.builder().token(os.environ["BOT_TOKEN"]).build()
    app.bot_data["shop"] = shop
    app.bot_data["config"] = config
    handlers = [start, help_cmd, lang_cmd, catalog, buy, pay, myorders,
                balance, watch, unwatch, wishlist, sub, mysubs,
                review, approve, refund, ignore, grant, addproduct, price]
    for fn in handlers:
        name = {"help_cmd": "help", "lang_cmd": "lang"}.get(
            fn.__name__, fn.__name__)
        app.add_handler(CommandHandler(name, fn))
    if app.job_queue:
        app.job_queue.run_repeating(_renewal_job, interval=3600, first=60)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        raise SystemExit("BOT_TOKEN is required (see .env.example)")
    config = ShopConfig.from_env()
    db_path = os.getenv("SHOP_DB", "shop.db")
    shop = Shop(connect(db_path), config)
    if not shop.catalog.list_active():
        shop.seed_demo_catalog()
        log.info("seeded demo catalog")
    build_app(config, shop).run_polling()


if __name__ == "__main__":
    main()
