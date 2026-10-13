def test_add_remove_list(shop, candle):
    assert shop.wishlist.add(1001, candle.id) is True
    items = shop.wishlist.list_for(1001)
    assert [p.id for p in items] == [candle.id]
    assert shop.wishlist.remove(1001, candle.id) is True
    assert shop.wishlist.list_for(1001) == []


def test_add_idempotent(shop, candle):
    assert shop.wishlist.add(1001, candle.id) is True
    assert shop.wishlist.add(1001, candle.id) is False
    assert len(shop.wishlist.list_for(1001)) == 1


def test_price_drop_creates_alert(shop, candle):
    shop.wishlist.add(1001, candle.id)
    shop.wishlist.add(1002, candle.id)
    res = shop.set_product_price(candle.id, 1999, lang="en")
    assert res["notified"] == 2
    alerts = shop.alerts_for(1001)
    assert len(alerts) == 1
    assert alerts[0].kind == "price_drop"
    assert "19.99" in alerts[0].text and "25.00" in alerts[0].text


def test_price_rise_no_alert(shop, candle):
    shop.wishlist.add(1001, candle.id)
    res = shop.set_product_price(candle.id, 2999, lang="en")
    assert res["notified"] == 0
    assert shop.alerts_for(1001) == []


def test_inactive_product_hidden_from_wishlist(shop, candle):
    shop.wishlist.add(1001, candle.id)
    shop.catalog.set_active(candle.id, False)
    assert shop.wishlist.list_for(1001) == []
