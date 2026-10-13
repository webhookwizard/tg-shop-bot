import pytest

from src.config import ShopConfig
from src.db import connect
from src.shop import Shop


@pytest.fixture
def clock():
    return [1_700_000_000.0]


@pytest.fixture
def shop(clock):
    conn = connect(":memory:")
    cfg = ShopConfig(shop_name="Test Shop", admin_ids=(9001,))
    return Shop(conn, cfg, clock=lambda: clock[0])


@pytest.fixture
def candle(shop):
    return shop.catalog.add_product("Candle", "cedar & amber", 2500, stock=10)


@pytest.fixture
def big_item(shop):
    return shop.catalog.add_product("Daigou slot", "sneakers", 9900, stock=5)


@pytest.fixture
def sub_product(shop):
    return shop.catalog.add_product(
        "Deals channel", "daily alerts", 1500,
        kind="subscription", billing_days=30)
