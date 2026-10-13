import pytest

from src.catalog import CatalogError


def test_add_and_get(shop, candle):
    assert candle.id > 0
    assert candle.name == "Candle"
    assert candle.price_cents == 2500
    fetched = shop.catalog.get(candle.id)
    assert fetched.name == "Candle"


def test_add_invalid(shop):
    with pytest.raises(CatalogError):
        shop.catalog.add_product("", price_cents=100)
    with pytest.raises(CatalogError):
        shop.catalog.add_product("X", price_cents=-5)
    with pytest.raises(CatalogError):
        shop.catalog.add_product("X", price_cents=100, kind="weird")
    with pytest.raises(CatalogError):
        shop.catalog.add_product("X", price_cents=100,
                                 kind="subscription", billing_days=0)


def test_list_active_excludes_inactive(shop, candle):
    assert len(shop.catalog.list_active()) == 1
    shop.catalog.set_active(candle.id, False)
    assert shop.catalog.list_active() == []


def test_set_price_returns_old(shop, candle):
    product, old = shop.catalog.set_price(candle.id, 1999)
    assert old == 2500
    assert product.price_cents == 1999


def test_set_price_negative_raises(shop, candle):
    with pytest.raises(CatalogError):
        shop.catalog.set_price(candle.id, -1)


def test_set_price_unknown_raises(shop):
    with pytest.raises(CatalogError):
        shop.catalog.set_price(9999, 100)


def test_adjust_stock_floors_at_zero(shop, candle):
    p = shop.catalog.adjust_stock(candle.id, -4)
    assert p.stock == 6
    p = shop.catalog.adjust_stock(candle.id, -100)
    assert p.stock == 0


def test_unlimited_stock_untouched(shop):
    p = shop.catalog.add_product("Digital", price_cents=100)  # stock=-1
    p2 = shop.catalog.adjust_stock(p.id, -5)
    assert p2.stock == -1
