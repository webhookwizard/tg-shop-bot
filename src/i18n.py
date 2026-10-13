"""English / Chinese strings for every user-facing message.

The bot never hard-codes copy: every reply goes through ``t()`` so a
seller can serve both English- and Chinese-speaking buyers.
"""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "Welcome to {shop}! Browse the catalog with /catalog, "
            "then buy with /buy <id>. Pay in USDT — no account needed."
        ),
        "help": (
            "Commands:\n"
            "/catalog - browse products\n"
            "/buy <id> [qty] - place an order\n"
            "/pay <order_id> <TXID> - submit your USDT payment\n"
            "/myorders - your orders\n"
            "/balance - your store credit\n"
            "/watch <id> - price-drop alerts\n"
            "/wishlist - your watched items\n"
            "/sub <id> - subscribe (paid from credit)\n"
            "/mysubs - your subscriptions\n"
            "/lang - switch English / 中文"
        ),
        "catalog_title": "Catalog — {shop}",
        "catalog_empty": "The catalog is empty right now. Check back soon!",
        "product_line": "#{id} {name} — {price} USDT{kind}\n  {desc}",
        "kind_sub": " / {days} days",
        "order_created": "Order #{id}: {qty} x {name} = {total} USDT.",
        "pay_how_usdt": (
            "Send exactly {total} USDT ({network}) to:\n{address}\n"
            "Then submit your payment:\n/pay {order_id} <your TXID>"
        ),
        "pay_how_credit": "Paid from your store credit. Done!",
        "txid_received": (
            "TXID received for order #{id}. The seller will confirm it "
            "and your order completes — usually within a few hours."
        ),
        "order_paid": "Order #{id} is paid. Thank you!",
        "order_completed": "Order #{id} is complete. Enjoy!",
        "order_refunded": "Order #{id} was refunded ({reason}).",
        "order_cancelled": "Order #{id} cancelled.",
        "balance_line": "Your store credit: {amount} USDT.",
        "credit_granted": "Admin added {amount} USDT to your credit.",
        "insufficient_credit": (
            "Not enough credit (need {need} USDT, have {have} USDT). "
            "Ask the seller to top you up, or pay with USDT."
        ),
        "wishlist_added": "Watching #{id} {name}. I'll ping you if the price drops.",
        "wishlist_removed": "Stopped watching #{id}.",
        "wishlist_title": "Your watchlist:",
        "wishlist_empty": "Your watchlist is empty. Use /watch <id>.",
        "wishlist_line": "#{id} {name} — {price} USDT",
        "price_drop": "Price drop: {name} is now {new} USDT (was {old}).",
        "subscribed": "Subscribed to {name} ({price} USDT / {days} days). Renews {date}.",
        "renewed": "Renewed {name} for {price} USDT. Next renewal {date}.",
        "renew_failed": (
            "Could not renew {name}: not enough credit. "
            "Top up or it will stay paused."
        ),
        "sub_cancelled": "Subscription #{id} cancelled.",
        "mysubs_title": "Your subscriptions:",
        "mysubs_empty": "No subscriptions. Use /sub <id> on a subscription product.",
        "sub_line": "#{id} {name} — {status}, renews {date}",
        "myorders_title": "Your orders:",
        "myorders_empty": "No orders yet. Browse with /catalog.",
        "order_line": "#{id} {name} x{qty} — {total} USDT [{status}]",
        "review_title": "Review queue ({n} open):",
        "review_empty": "Review queue is clear.",
        "review_line": "#{id} order #{order} {total} USDT risk={risk} ({reason})",
        "review_approved": "Approved. Order #{order} marked paid.",
        "review_refunded": "Refunded. Order #{order} marked refunded.",
        "review_ignored": "Dismissed. Order #{order} sent back to awaiting payment.",
        "not_admin": "That command is for the shop admin.",
        "added_product": "Product #{id} added: {name} — {price} USDT.",
        "lang_set": "Language: English.",
        "bad_txid": "That TXID doesn't look right (8-128 letters/digits). Try again.",
        "dup_txid": "This TXID was already used for another order.",
        "no_such_order": "No such order.",
        "not_your_order": "That's not your order.",
        "wrong_state": "Order #{id} can't take that action right now.",
        "unknown_product": "No such product. See /catalog.",
        "bad_args": "Usage: {usage}",
    },
    "cn": {
        "welcome": "欢迎来到 {shop}！用 /catalog 看商品，用 /buy <编号> 下单，USDT 付款，不用注册。",
        "help": (
            "命令：\n"
            "/catalog - 看商品\n"
            "/buy <编号> [数量] - 下单\n"
            "/pay <订单号> <TXID> - 提交 USDT 付款\n"
            "/myorders - 我的订单\n"
            "/balance - 我的余额\n"
            "/watch <编号> - 降价提醒\n"
            "/wishlist - 我的关注\n"
            "/sub <编号> - 订阅（从余额扣）\n"
            "/mysubs - 我的订阅\n"
            "/lang - 切换 English / 中文"
        ),
        "catalog_title": "商品目录 — {shop}",
        "catalog_empty": "暂时没有商品，过阵子再来看看！",
        "product_line": "#{id} {name} — {price} USDT{kind}\n  {desc}",
        "kind_sub": " / {days} 天",
        "order_created": "订单 #{id}：{name} x{qty}，共 {total} USDT。",
        "pay_how_usdt": "请转 {total} USDT（{network}）到：\n{address}\n然后提交付款：\n/pay {order_id} <你的 TXID>",
        "pay_how_credit": "已从余额扣款，完成！",
        "txid_received": "订单 #{id} 的 TXID 已收到，卖家确认后订单即完成，一般几小时内。",
        "order_paid": "订单 #{id} 已付款，谢谢！",
        "order_completed": "订单 #{id} 已完成，请查收！",
        "order_refunded": "订单 #{id} 已退款（{reason}）。",
        "order_cancelled": "订单 #{id} 已取消。",
        "balance_line": "你的余额：{amount} USDT。",
        "credit_granted": "管理员给你充值了 {amount} USDT。",
        "insufficient_credit": "余额不足（需要 {need} USDT，现有 {have} USDT），请让卖家充值或用 USDT 付款。",
        "wishlist_added": "已关注 #{id} {name}，降价了我通知你。",
        "wishlist_removed": "已取消关注 #{id}。",
        "wishlist_title": "我的关注：",
        "wishlist_empty": "还没关注任何商品，用 /watch <编号>。",
        "wishlist_line": "#{id} {name} — {price} USDT",
        "price_drop": "降价了：{name} 现在 {new} USDT（原价 {old}）。",
        "subscribed": "已订阅 {name}（{price} USDT / {days} 天），{date} 续费。",
        "renewed": "{name} 已续费 {price} USDT，下次 {date}。",
        "renew_failed": "{name} 续费失败：余额不足，请充值，否则订阅会暂停。",
        "sub_cancelled": "订阅 #{id} 已取消。",
        "mysubs_title": "我的订阅：",
        "mysubs_empty": "还没有订阅，在订阅制商品上用 /sub <编号>。",
        "sub_line": "#{id} {name} — {status}，{date} 续费",
        "myorders_title": "我的订单：",
        "myorders_empty": "还没有订单，用 /catalog 看看。",
        "order_line": "#{id} {name} x{qty} — {total} USDT [{status}]",
        "review_title": "待审核（{n}）：",
        "review_empty": "没有待审核的订单。",
        "review_line": "#{id} 订单 #{order} {total} USDT 风险={risk}（{reason}）",
        "review_approved": "已通过，订单 #{order} 标记为已付款。",
        "review_refunded": "已退款，订单 #{order} 标记为已退款。",
        "review_ignored": "已忽略，订单 #{order} 退回待付款。",
        "not_admin": "这是管理员命令。",
        "added_product": "商品 #{id} 已上架：{name} — {price} USDT。",
        "lang_set": "语言：中文。",
        "bad_txid": "TXID 看起来不对（8-128 位字母/数字），再试一次。",
        "dup_txid": "这个 TXID 已经用在别的订单上了。",
        "no_such_order": "没有这个订单。",
        "not_your_order": "这不是你的订单。",
        "wrong_state": "订单 #{id} 现在不能做这个操作。",
        "unknown_product": "没有这个商品，看 /catalog。",
        "bad_args": "用法：{usage}",
    },
}


def t(key: str, lang: str = "en", **kwargs: object) -> str:
    """Render a user-facing string. Falls back to English."""
    lang = "cn" if str(lang).lower() in ("cn", "zh", "chinese") else "en"
    template = STRINGS.get(lang, {}).get(key) or STRINGS["en"].get(key, key)
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def fmt_money(cents: int) -> str:
    """1_999 -> '19.99' (USDT has 2 displayed decimals for shop use)."""
    return f"{cents / 100:.2f}"
