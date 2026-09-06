"""Adapter interface so new marketplaces can be plugged in without touching core ERP."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional


@dataclass
class RemoteInventory:
    sku: str
    quantity: int
    warehouse_code: str = "DEFAULT"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    external_id: str = ""


@dataclass
class RemoteOrderItem:
    sku: str
    title: str
    quantity: int
    unit_price: Decimal
    marketplace_fee: Decimal = Decimal("0")


@dataclass
class RemoteOrder:
    external_id: str
    order_number: str
    status: str
    financial_status: str
    currency: str
    subtotal: Decimal
    shipping_charged: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    customer_name: str
    customer_email: str
    shipping_country: str
    placed_at: datetime
    items: list[RemoteOrderItem]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteListing:
    external_id: str
    sku: str
    title: str
    price: Decimal
    quantity: int
    status: str
    category: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemotePayout:
    external_id: str
    amount: Decimal
    currency: str
    paid_at: Optional[datetime]
    fee_total: Decimal
    order_external_ids: list[str]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PushResult:
    ok: bool
    external_id: str = ""
    message: str = ""
    retryable: bool = False


class MarketplaceAdapter(ABC):
    code: str
    display_name: str
    default_rate_limit_rpm: int = 60
    supports_webhooks: bool = True
    fee_rate: Decimal = Decimal("0.15")

    @abstractmethod
    async def fetch_inventory(self, credentials: dict[str, str]) -> list[RemoteInventory]:
        ...

    @abstractmethod
    async def push_inventory(
        self, credentials: dict[str, str], sku: str, quantity: int, warehouse_code: str = "DEFAULT"
    ) -> PushResult:
        ...

    @abstractmethod
    async def fetch_orders(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemoteOrder]:
        ...

    @abstractmethod
    async def fetch_listings(self, credentials: dict[str, str]) -> list[RemoteListing]:
        ...

    @abstractmethod
    async def push_listing(
        self, credentials: dict[str, str], listing: dict[str, Any]
    ) -> PushResult:
        ...

    @abstractmethod
    async def fetch_payouts(
        self, credentials: dict[str, str], since: Optional[datetime] = None
    ) -> list[RemotePayout]:
        ...

    async def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"event": payload.get("event") or payload.get("type") or "unknown", "payload": payload}

    def estimate_fee(self, selling_price: Decimal) -> Decimal:
        return (selling_price * self.fee_rate).quantize(Decimal("0.0001"))


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, MarketplaceAdapter] = {}

    def register(self, adapter: MarketplaceAdapter) -> None:
        self._adapters[adapter.code] = adapter

    def get(self, code: str) -> MarketplaceAdapter:
        if code not in self._adapters:
            raise KeyError(f"Unknown marketplace adapter: {code}")
        return self._adapters[code]

    def all(self) -> list[MarketplaceAdapter]:
        return list(self._adapters.values())

    def codes(self) -> list[str]:
        return list(self._adapters.keys())
