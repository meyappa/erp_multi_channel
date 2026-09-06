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


class EbayAdapter(MarketplaceAdapter):
    code = "ebay"
    display_name = "eBay"
    default_rate_limit_rpm = 40
    fee_rate = Decimal("0.129")

    async def fetch_inventory(self, credentials: dict[str, str]) -> list[RemoteInventory]:
        _ = credentials
        return inventories_for(self.code)

    async def push_inventory(
        self, credentials: dict[str, str], sku: str, quantity: int, warehouse_code: str = "DEFAULT"
    ) -> PushResult:
        _ = credentials, warehouse_code
        return PushResult(ok=True, external_id=f"eby-{sku}", message=f"eBay qty set to {quantity}")

    async def fetch_orders(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemoteOrder]:
        _ = credentials, since
        return orders_for(self.code, "eby")

    async def fetch_listings(self, credentials: dict[str, str]) -> list[RemoteListing]:
        _ = credentials
        return listings_for(self.code)

    async def push_listing(self, credentials: dict[str, str], listing: dict[str, Any]) -> PushResult:
        _ = credentials
        return PushResult(ok=True, external_id=f"eby-{listing.get('sku')}", message="Listing upserted on eBay")

    async def fetch_payouts(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemotePayout]:
        _ = credentials, since
        orders = orders_for(self.code, "eby")
        return payouts_for(self.code, "eby", orders)
