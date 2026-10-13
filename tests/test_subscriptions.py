import pytest

from src.subscriptions import SubscriptionError

DAY = 86400.0


def test_subscribe_active(shop, sub_product):
    shop.credit.grant(1001, 5000)
    sub = shop.subs.subscribe(1001, sub_product.id)
    assert sub.status == "active"
    assert sub.renews_at == sub.started_at + 30 * DAY
    assert shop.credit.balance(1001) == 3500  # 1500 charged


def test_subscribe_non_subscription_raises(shop, candle):
    shop.credit.grant(1001, 5000)
    with pytest.raises(SubscriptionError):
        shop.subs.subscribe(1001, candle.id)


def test_subscribe_insufficient_credit_raises(shop, sub_product):
    with pytest.raises(SubscriptionError):
        shop.subs.subscribe(1001, sub_product.id)


def test_renewals_due_and_renew(shop, sub_product, clock):
    shop.credit.grant(1001, 10000)
    sub = shop.subs.subscribe(1001, sub_product.id)
    assert shop.subs.renewals_due() == []
    clock[0] += 31 * DAY
    due = shop.subs.renewals_due()
    assert [s.id for s in due] == [sub.id]
    renewed = shop.subs.renew(sub.id)
    assert renewed.status == "active"
    assert renewed.renews_at > sub.renews_at
    assert shop.credit.balance(1001) == 10000 - 1500 * 2
    alerts = shop.alerts_for(1001)
    assert any(a.kind == "renewal" for a in alerts)


def test_renew_insufficient_credit_goes_past_due(shop, sub_product, clock):
    shop.credit.grant(1001, 1500)  # exactly one period
    sub = shop.subs.subscribe(1001, sub_product.id)
    clock[0] += 31 * DAY
    renewed = shop.subs.renew(sub.id)
    assert renewed.status == "past_due"
    alerts = shop.alerts_for(1001)
    assert any("renew" in a.text.lower() or a.kind == "renewal"
               for a in alerts)


def test_cancel_and_mysubs(shop, sub_product):
    shop.credit.grant(1001, 5000)
    sub = shop.subs.subscribe(1001, sub_product.id)
    assert len(shop.subs.mysubs(1001)) == 1
    shop.subs.cancel(sub.id, 1001)
    assert shop.subs.mysubs(1001) == []
    assert shop.subs.get(sub.id).status == "cancelled"


def test_cancel_other_users_sub_raises(shop, sub_product):
    shop.credit.grant(1001, 5000)
    sub = shop.subs.subscribe(1001, sub_product.id)
    with pytest.raises(SubscriptionError):
        shop.subs.cancel(sub.id, 1002)
