import pytest

from src.credit import InsufficientCredit


def test_grant_and_balance(shop):
    assert shop.credit.balance(1001) == 0
    shop.credit.grant(1001, 2000, reason="welcome")
    assert shop.credit.balance(1001) == 2000
    shop.credit.grant(1001, 500, reason="bonus")
    assert shop.credit.balance(1001) == 2500


def test_grant_nonpositive_raises(shop):
    with pytest.raises(ValueError):
        shop.credit.grant(1001, 0)
    with pytest.raises(ValueError):
        shop.credit.grant(1001, -100)


def test_deduct_ok(shop):
    shop.credit.grant(1001, 2000)
    bal = shop.credit.deduct(1001, 1500, reason="order #1")
    assert bal == 500


def test_deduct_insufficient_raises(shop):
    shop.credit.grant(1001, 100)
    with pytest.raises(InsufficientCredit):
        shop.credit.deduct(1001, 200)
    assert shop.credit.balance(1001) == 100  # untouched


def test_ledger_records_reasons(shop):
    shop.credit.grant(1001, 2000, reason="welcome bonus")
    shop.credit.deduct(1001, 500, reason="order #7")
    entries = shop.credit.ledger(1001)
    assert [e["delta_cents"] for e in entries] == [2000, -500]
    assert entries[0]["reason"] == "welcome bonus"


def test_balances_are_per_user(shop):
    shop.credit.grant(1001, 2000)
    assert shop.credit.balance(1002) == 0
