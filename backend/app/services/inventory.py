"""Inventory mutations, conflict resolution, and bi-directional marketplace sync."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters import registry
from app.config import get_settings
from app.models.catalog import ProductVariant
from app.models.inventory import InventoryBalance, InventoryMovement, SyncEvent, Warehouse
from app.models.marketplace import Channel

settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_or_create_balance(
    db: AsyncSession, tenant_id: int, variant_id: int, warehouse_id: int
) -> InventoryBalance:
    stmt = select(InventoryBalance).where(
        InventoryBalance.tenant_id == tenant_id,
        InventoryBalance.variant_id == variant_id,
        InventoryBalance.warehouse_id == warehouse_id,
    )
    bal = (await db.execute(stmt)).scalar_one_or_none()
    if bal is None:
        bal = InventoryBalance(
            tenant_id=tenant_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            on_hand=0,
            reserved=0,
            inbound=0,
            safety_stock=0,
        )
        db.add(bal)
        await db.flush()
    return bal


async def apply_movement(
    db: AsyncSession,
    *,
    tenant_id: int,
    variant_id: int,
    warehouse_id: int,
    quantity_delta: int,
    reason: str,
    reference_type: str = "",
    reference_id: str = "",
    note: str = "",
) -> InventoryBalance:
    bal = await get_or_create_balance(db, tenant_id, variant_id, warehouse_id)
    if reason == "reserve":
        bal.reserved = max(bal.reserved + quantity_delta, 0)
    elif reason == "release":
        bal.reserved = max(bal.reserved - abs(quantity_delta), 0)
    elif reason == "inbound":
        bal.inbound = max(bal.inbound + quantity_delta, 0)
        if quantity_delta < 0:
            bal.on_hand += abs(quantity_delta)
            bal.inbound = max(bal.inbound + quantity_delta, 0)
    else:
        new_on_hand = bal.on_hand + quantity_delta
        if new_on_hand < 0:
            new_on_hand = 0
        bal.on_hand = new_on_hand
    bal.version += 1
    db.add(
        InventoryMovement(
            tenant_id=tenant_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            quantity_delta=quantity_delta,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
        )
    )
    await db.flush()
    return bal


def resolve_conflict(erp_qty: int, market_qty: int, policy: str, erp_newer: bool) -> tuple[int, str]:
    if erp_qty == market_qty:
        return erp_qty, "no_conflict"
    if policy == "erp_wins":
        return erp_qty, "erp_wins"
    if policy == "marketplace_wins":
        return market_qty, "marketplace_wins"
    return (erp_qty if erp_newer else market_qty), "newest_wins"


async def variant_by_sku(db: AsyncSession, tenant_id: int, sku: str) -> ProductVariant | None:
    from app.models.catalog import Product

    stmt = (
        select(ProductVariant)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(ProductVariant.sku == sku, Product.tenant_id == tenant_id)
    )
    return (await db.execute(stmt)).scalars().first()


async def default_warehouse(db: AsyncSession, tenant_id: int) -> Warehouse:
    stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id, Warehouse.is_default.is_(True))
    wh = (await db.execute(stmt)).scalar_one_or_none()
    if wh:
        return wh
    stmt = select(Warehouse).where(Warehouse.tenant_id == tenant_id)
    wh = (await db.execute(stmt)).scalars().first()
    if not wh:
        raise RuntimeError("No warehouse configured")
    return wh


async def sync_channel_inventory(db: AsyncSession, channel: Channel) -> dict[str, Any]:
    adapter = registry.get(channel.marketplace)
    remote = await adapter.fetch_inventory({})
    wh = await default_warehouse(db, channel.tenant_id)
    policy = settings.inventory_conflict_policy
    pushed = 0
    pulled = 0
    conflicts = 0

    for item in remote:
        variant = await variant_by_sku(db, channel.tenant_id, item.sku)
        if not variant:
            event = SyncEvent(
                tenant_id=channel.tenant_id,
                channel_id=channel.id,
                direction="inbound",
                entity_type="inventory",
                entity_id=item.sku,
                status="skipped",
                payload=json.dumps({"sku": item.sku, "qty": item.quantity}),
                result=json.dumps({"reason": "sku_not_in_catalog"}),
            )
            db.add(event)
            continue
        bal = await get_or_create_balance(db, channel.tenant_id, variant.id, wh.id)
        winner, rule = resolve_conflict(bal.available, item.quantity, policy, True)
        if rule != "no_conflict":
            conflicts += 1
        if winner != bal.on_hand and rule in ("marketplace_wins", "newest_wins"):
            delta = winner - bal.on_hand
            await apply_movement(
                db,
                tenant_id=channel.tenant_id,
                variant_id=variant.id,
                warehouse_id=wh.id,
                quantity_delta=delta,
                reason="sync_in",
                reference_type="channel",
                reference_id=str(channel.id),
                note=f"conflict={rule}",
            )
            pulled += 1
        result = await adapter.push_inventory({}, item.sku, winner, wh.code)
        pushed += 1 if result.ok else 0
        db.add(
            SyncEvent(
                tenant_id=channel.tenant_id,
                channel_id=channel.id,
                direction="bidirectional",
                entity_type="inventory",
                entity_id=item.sku,
                status="success" if result.ok else "failed",
                conflict_policy=policy,
                payload=json.dumps({"erp": bal.available, "market": item.quantity, "winner": winner, "rule": rule}),
                result=json.dumps({"ok": result.ok, "message": result.message}),
                error=None if result.ok else result.message,
            )
        )

    channel.last_synced_at = utcnow()
    await db.commit()
    return {
        "channel": channel.code,
        "marketplace": channel.marketplace,
        "remote_skus": len(remote),
        "pushed": pushed,
        "pulled": pulled,
        "conflicts": conflicts,
        "policy": policy,
        "synced_at": channel.last_synced_at.isoformat(),
    }


async def inventory_matrix(db: AsyncSession, tenant_id: int) -> list[dict[str, Any]]:
    stmt = (
        select(InventoryBalance)
        .options(selectinload(InventoryBalance.variant), selectinload(InventoryBalance.warehouse))
        .where(InventoryBalance.tenant_id == tenant_id)
    )
    rows = (await db.execute(stmt)).scalars().all()
    out = []
    for b in rows:
        out.append(
            {
                "id": b.id,
                "sku": b.variant.sku if b.variant else "",
                "title": b.variant.title if b.variant else "",
                "warehouse": b.warehouse.code if b.warehouse else "",
                "warehouse_name": b.warehouse.name if b.warehouse else "",
                "on_hand": b.on_hand,
                "reserved": b.reserved,
                "inbound": b.inbound,
                "available": b.available,
                "safety_stock": b.safety_stock,
                "version": b.version,
            }
        )
    return out
