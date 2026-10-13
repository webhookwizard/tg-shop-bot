"""tg-shop-bot: Telegram shop bot with USDT payments.

Core business logic lives in pure-Python services (no network, no API keys)
so it can be unit-tested and demoed offline. ``bot.py`` is the only module
that talks to Telegram.
"""

from .shop import Shop
from .config import ShopConfig

__all__ = ["Shop", "ShopConfig"]
__version__ = "1.0.0"
