from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.adapters.base import (
    MarketplaceAdapter,
    PushResult,
    RemoteInventory,
    RemoteListing,
    RemoteOrder,
    RemotePayout,
)
from app.adapters.mock_store import inventories_for, listings_for, orders_for, payouts_for


class TikTokShopAdapter(MarketplaceAdapter):
    code = "tiktok"
    display_name = "TikTok Shop"
    default_rate_limit_rpm = 100
    fee_rate = Decimal("0.06")

    async def fetch_inventory(self, credentials: dict[str, str]) -> list[RemoteInventory]:
        _ = credentials
        return inventories_for(self.code)

    async def push_inventory(
        self, credentials: dict[str, str], sku: str, quantity: int, warehouse_code: str = "DEFAULT"
    ) -> PushResult:
        _ = credentials, warehouse_code
        return PushResult(ok=True, external_id=f"tts-{sku}", message=f"TikTok Shop qty set to {quantity}")

    async def fetch_orders(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemoteOrder]:
        _ = credentials, since
        return orders_for(self.code, "tts")

    async def fetch_listings(self, credentials: dict[str, str]) -> list[RemoteListing]:
        _ = credentials
        return listings_for(self.code)

    async def push_listing(self, credentials: dict[str, str], listing: dict[str, Any]) -> PushResult:
        _ = credentials
        return PushResult(ok=True, external_id=f"tts-{listing.get('sku')}", message="Listing upserted on TikTok Shop")

    async def fetch_payouts(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemotePayout]:
        _ = credentials, since
        orders = orders_for(self.code, "tts")
        return payouts_for(self.code, "tts", orders)
