import pytest

from src.payments import (CryptoBotClient, CryptoBotError, DuplicateTxidError,
                          InvalidTxidError, PaymentError)
from src.orders import PAYMENT_SUBMITTED


def _order(shop, candle, buyer=1001):
    return shop.orders.create_order(buyer, "Mei", candle.id, qty=1)


def test_submit_ok_creates_review_item(shop, candle):
    order = _order(shop, candle)
    res = shop.submit_usdt_payment(order.id, "TXNABCDEF123456", 2500)
    assert res["risk_score"] == 0
    assert res["flags"] == []
    assert shop.orders.get(order.id).status == PAYMENT_SUBMITTED
    assert len(shop.review.list_open()) == 1


def test_submit_bad_txid(shop, candle):
    order = _order(shop, candle)
    with pytest.raises(InvalidTxidError):
        shop.submit_usdt_payment(order.id, "short", 2500)
    with pytest.raises(InvalidTxidError):
        shop.submit_usdt_payment(order.id, "has space!!", 2500)


def test_submit_duplicate_txid(shop, candle):
    o1 = _order(shop, candle)
    o2 = _order(shop, candle)
    shop.submit_usdt_payment(o1.id, "TXNABCDEF123456", 2500)
    with pytest.raises(DuplicateTxidError):
        shop.submit_usdt_payment(o2.id, "TXNABCDEF123456", 2500)


def test_submit_twice_same_order_raises(shop, candle):
    order = _order(shop, candle)
    shop.submit_usdt_payment(order.id, "TXNABCDEF123456", 2500)
    with pytest.raises(PaymentError):
        shop.submit_usdt_payment(order.id, "TXNZZZZZZ999999", 2500)


def test_amount_mismatch_flagged(shop, candle):
    order = _order(shop, candle)
    res = shop.submit_usdt_payment(order.id, "TXNABCDEF123456", 2000)
    assert "amount_mismatch" in res["flags"]
    assert res["risk_score"] == 40


def test_first_big_order_flagged(shop, big_item):
    order = shop.orders.create_order(1001, "Leo", big_item.id)  # 9900 >= 5000
    res = shop.submit_usdt_payment(order.id, "TXNBIGORDER00001", 9900)
    assert "first_big_order" in res["flags"]
    assert res["risk_score"] == 20


def test_first_big_order_not_flagged_for_regulars(shop, big_item):
    # buyer with a completed purchase is no longer "first"
    first = shop.orders.create_order(1001, "Leo", big_item.id,
                                     pay_method="credit")
    shop.credit.grant(1001, 20000)
    shop.orders.pay_with_credit(first.id)
    second = shop.orders.create_order(1001, "Leo", big_item.id)
    res = shop.submit_usdt_payment(second.id, "TXNSECOND0000001", 9900)
    assert "first_big_order" not in res["flags"]


def test_prior_refund_flagged(shop, candle):
    o1 = _order(shop, candle)
    shop.submit_usdt_payment(o1.id, "TXNREFUND00000001", 2500)
    item = shop.review.list_open()[0]
    shop.review.refund(item.id, reason="test")
    o2 = _order(shop, candle)
    res = shop.submit_usdt_payment(o2.id, "TXNREFUND00000002", 2500)
    assert "prior_refund" in res["flags"]
    assert res["risk_score"] == 30


def test_cryptobot_payload_builder_no_network():
    client = CryptoBotClient(token="dummy")
    payload = client.build_invoice_payload("19.99", payload="order:1",
                                           description="Candle")
    assert payload == {"asset": "USDT", "amount": "19.99",
                       "payload": "order:1", "description": "Candle"}


def test_cryptobot_requires_token():
    with pytest.raises(CryptoBotError):
        CryptoBotClient(token="")
