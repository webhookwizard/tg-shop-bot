"""Shop configuration.

Everything the bot needs to run comes from environment variables so the
same code can serve many sellers: one config per shop, zero code changes.
See .env.example for the full list.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _admin_ids(raw: str) -> tuple[int, ...]:
    ids: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return tuple(ids)


@dataclass
class ShopConfig:
    """Runtime configuration for one shop."""

    shop_name: str = "Demo Shop"
    # USDT receiving address shown to buyers on the manual payment path.
    usdt_address: str = "TXxxReplaceWithYourAddress"
    usdt_network: str = "TRC20"
    admin_ids: tuple[int, ...] = field(default_factory=tuple)
    default_lang: str = "en"  # "en" or "cn"
    # Optional: CryptoBot token enables hosted USDT invoices (auto-confirm).
    # Empty -> manual TXID + admin-confirm path (works with zero API keys).
    cryptobot_token: str | None = None

    @classmethod
    def from_env(cls) -> "ShopConfig":
        token = os.getenv("CRYPTOBOT_TOKEN", "").strip() or None
        return cls(
            shop_name=os.getenv("SHOP_NAME", "Demo Shop"),
            usdt_address=os.getenv("USDT_ADDRESS", "TXxxReplaceWithYourAddress"),
            usdt_network=os.getenv("USDT_NETWORK", "TRC20"),
            admin_ids=_admin_ids(os.getenv("ADMIN_IDS", "")),
            default_lang=os.getenv("DEFAULT_LANG", "en").lower(),
            cryptobot_token=token,
        )

    def is_admin(self, user_id: int) -> bool:
        return int(user_id) in self.admin_ids
