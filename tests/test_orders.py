import pytest

from src.orders import OrderError


def test_create_computes_total(shop, candle):
    order = shop.orders.create_order(1001, "Mei", candle.id, qty=2)
    assert order.total_cents == 5000
    assert order.status == "awaiting_payment"


def test_create_inactive_product_raises(shop, candle):
    shop.catalog.set_active(candle.id, False)
    with pytest.raises(OrderError):
        shop.orders.create_order(1001, "Mei", candle.id)


def test_create_insufficient_stock_raises(shop, candle):
    with pytest.raises(OrderError):
        shop.orders.create_order(1001, "Mei", candle.id, qty=999)


def test_create_reserves_stock(shop, candle):
    shop.orders.create_order(1001, "Mei", candle.id, qty=3)
    assert shop.catalog.get(candle.id).stock == 7


def test_pay_with_credit(shop, candle):
    shop.credit.grant(1001, 5000)
    order = shop.orders.create_order(1001, "Mei", candle.id,
                                     qty=1, pay_method="credit")
    paid = shop.orders.pay_with_credit(order.id)
    assert paid.status == "paid"
    assert shop.credit.balance(1001) == 2500


def test_pay_with_credit_insufficient_raises(shop, candle):
    shop.credit.grant(1001, 100)
    order = shop.orders.create_order(1001, "Mei", candle.id,
                                     qty=1, pay_method="credit")
    with pytest.raises(OrderError):
        shop.orders.pay_with_credit(order.id)


def test_cancel_restocks_and_blocks_repay(shop, candle):
    order = shop.orders.create_order(1001, "Mei", candle.id, qty=2)
    shop.orders.cancel(order.id)
    assert shop.orders.get(order.id).status == "cancelled"
    assert shop.catalog.get(candle.id).stock == 10
    with pytest.raises(OrderError):
        shop.orders.cancel(order.id)


def test_list_for_buyer(shop, candle, big_item):
    shop.orders.create_order(1001, "Mei", candle.id)
    shop.orders.create_order(1002, "Leo", big_item.id)
    assert len(shop.orders.list_for_buyer(1001)) == 1
