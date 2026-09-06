"""In-memory marketplace simulation used by demo adapters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.adapters.base import RemoteInventory, RemoteListing, RemoteOrder, RemoteOrderItem, RemotePayout


def _now() -> datetime:
    return datetime.now(timezone.utc)


DEMO_CATALOG: dict[str, list[dict[str, Any]]] = {
    "amazon": [
        {"sku": "CF-WATCH-BLK", "qty": 42, "title": "Forge Chrono Watch — Black", "price": "189.00"},
        {"sku": "CF-WATCH-SLV", "qty": 28, "title": "Forge Chrono Watch — Silver", "price": "199.00"},
        {"sku": "CF-STRAP-22", "qty": 120, "title": "Leather Strap 22mm", "price": "29.00"},
    ],
    "shopee": [
        {"sku": "CF-WATCH-BLK", "qty": 18, "title": "Forge Chrono Watch Black", "price": "189.00"},
        {"sku": "CF-CABLE-USB", "qty": 340, "title": "USB-C Fast Cable 1.2m", "price": "9.90"},
    ],
    "lazada": [
        {"sku": "CF-WATCH-SLV", "qty": 11, "title": "Forge Chrono Silver", "price": "199.00"},
        {"sku": "CF-CASE-AIR", "qty": 76, "title": "AirCase Protective Sleeve", "price": "14.50"},
    ],
    "tiktok": [
        {"sku": "CF-CABLE-USB", "qty": 90, "title": "USB-C Fast Cable", "price": "8.90"},
        {"sku": "CF-STRAP-22", "qty": 55, "title": "Leather Strap 22mm", "price": "24.90"},
    ],
    "shopify": [
        {"sku": "CF-WATCH-BLK", "qty": 15, "title": "Forge Chrono Watch — Black", "price": "189.00"},
        {"sku": "CF-WATCH-SLV", "qty": 12, "title": "Forge Chrono Watch — Silver", "price": "199.00"},
        {"sku": "CF-BUNDLE-SET", "qty": 8, "title": "Watch + Strap Bundle", "price": "209.00"},
    ],
    "ebay": [
        {"sku": "CF-CASE-AIR", "qty": 40, "title": "AirCase Protective Sleeve", "price": "13.99"},
        {"sku": "CF-STRAP-22", "qty": 33, "title": "Leather Strap 22mm", "price": "27.50"},
    ],
}


def inventories_for(code: str) -> list[RemoteInventory]:
    rows = DEMO_CATALOG.get(code, [])
    return [
        RemoteInventory(sku=r["sku"], quantity=int(r["qty"]), warehouse_code="MAIN", external_id=f"{code}-{r['sku']}")
        for r in rows
    ]


def listings_for(code: str) -> list[RemoteListing]:
    rows = DEMO_CATALOG.get(code, [])
    return [
        RemoteListing(
            external_id=f"{code}-{r['sku']}",
            sku=r["sku"],
            title=r["title"],
            price=Decimal(r["price"]),
            quantity=int(r["qty"]),
            status="active",
        )
        for r in rows
    ]


def orders_for(code: str, prefix: str) -> list[RemoteOrder]:
    now = _now()
    catalog = DEMO_CATALOG.get(code, [])
    orders: list[RemoteOrder] = []
    for i, row in enumerate(catalog[:3], start=1):
        price = Decimal(row["price"])
        qty = 1 if i == 1 else i
        fee = (price * Decimal("0.12")).quantize(Decimal("0.01"))
        subtotal = price * qty
        shipping = Decimal("4.99") if i % 2 else Decimal("0")
        orders.append(
            RemoteOrder(
                external_id=f"{prefix}-{1000 + i}",
                order_number=f"{prefix.upper()}-{1000 + i}",
                status="processing" if i == 1 else "shipped",
                financial_status="paid",
                currency="USD",
                subtotal=subtotal,
                shipping_charged=shipping,
                tax=(subtotal * Decimal("0.08")).quantize(Decimal("0.01")),
                discount=Decimal("0"),
                total=subtotal + shipping + (subtotal * Decimal("0.08")).quantize(Decimal("0.01")),
                customer_name=f"Customer {i}",
                customer_email=f"buyer{i}@example.com",
                shipping_country="US" if i % 2 else "SG",
                placed_at=now - timedelta(hours=i * 6),
                items=[
                    RemoteOrderItem(
                        sku=row["sku"],
                        title=row["title"],
                        quantity=qty,
                        unit_price=price,
                        marketplace_fee=fee * qty,
                    )
                ],
                raw={"source": code, "demo": True},
            )
        )
    return orders


def payouts_for(code: str, prefix: str, orders: list[RemoteOrder]) -> list[RemotePayout]:
    if not orders:
        return []
    amount = sum((o.total for o in orders), Decimal("0"))
    fees = sum((sum((it.marketplace_fee for it in o.items), Decimal("0")) for o in orders), Decimal("0"))
    return [
        RemotePayout(
            external_id=f"{prefix}-payout-1",
            amount=amount - fees,
            currency="USD",
            paid_at=_now() - timedelta(days=1),
            fee_total=fees,
            order_external_ids=[o.external_id for o in orders[:-1]],
            raw={"partial": True},
        )
    ]
