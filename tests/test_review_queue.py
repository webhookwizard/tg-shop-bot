import pytest

from src.orders import PAID, REFUNDED, AWAITING_PAYMENT
from src.review_queue import ReviewError


def _submitted(shop, candle, txid="TXNABCDEF123456", amount=2500, buyer=1001):
    order = shop.orders.create_order(buyer, "B", candle.id)
    return shop.submit_usdt_payment(order.id, txid, amount)


def test_list_open_ordered_by_risk(shop, candle):
    _submitted(shop, candle, txid="TXNCLEAN000000001", amount=2500)  # risk 0
    _submitted(shop, candle, txid="TXNRISKY000000001", amount=1000)  # risk 40
    items = shop.review.list_open()
    assert [i.risk_score for i in items] == [40, 0]


def test_approve_marks_order_paid(shop, candle):
    res = _submitted(shop, candle)
    item = shop.review.approve(res["review_item"].id)
    assert item.status == "approved"
    assert shop.orders.get(res["payment"].order_id).status == PAID
    payment = shop.payments.payment_for_order(res["payment"].order_id)
    assert payment.status == "confirmed"


def test_refund_marks_order_refunded(shop, candle):
    res = _submitted(shop, candle)
    item = shop.review.refund(res["review_item"].id, reason="no funds")
    assert item.status == "refunded"
    assert shop.orders.get(res["payment"].order_id).status == REFUNDED


def test_ignore_returns_order_to_awaiting(shop, candle):
    res = _submitted(shop, candle)
    item = shop.review.ignore(res["review_item"].id)
    assert item.status == "ignored"
    order = shop.orders.get(res["payment"].order_id)
    assert order.status == AWAITING_PAYMENT
    # buyer can resubmit with a fresh txid
    res2 = shop.submit_usdt_payment(order.id, "TXNRESUBMIT00001", 2500)
    assert res2["risk_score"] == 0


def test_double_decide_raises(shop, candle):
    res = _submitted(shop, candle)
    shop.review.approve(res["review_item"].id)
    with pytest.raises(ReviewError):
        shop.review.approve(res["review_item"].id)


def test_open_with_orders_joins_product(shop, candle):
    _submitted(shop, candle)
    rows = shop.review.open_with_orders()
    assert len(rows) == 1
    assert rows[0]["product_name"] == "Candle"
    assert rows[0]["total_cents"] == 2500
