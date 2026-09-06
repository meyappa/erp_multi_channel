"""Order ingestion from marketplace adapters and reservation of stock."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters import registry
from app.adapters.base import RemoteOrder
from app.models.catalog import ProductVariant
from app.models.finance import OrderCost
from app.models.marketplace import Channel
from app.models.order import Order, OrderItem
from app.services.inventory import apply_movement, default_warehouse, variant_by_sku
from app.services.profit import q


async def ingest_remote_order(db: AsyncSession, channel: Channel, remote: RemoteOrder) -> Order:
    existing = (
        await db.execute(
            select(Order).where(Order.tenant_id == channel.tenant_id, Order.external_id == remote.external_id)
        )
    ).scalar_one_or_none()
    if existing:
        existing.status = remote.status
        existing.financial_status = remote.financial_status
        return existing

    wh = await default_warehouse(db, channel.tenant_id)
    order = Order(
        tenant_id=channel.tenant_id,
        channel_id=channel.id,
        warehouse_id=wh.id,
        external_id=remote.external_id,
        order_number=remote.order_number,
        status=remote.status,
        fulfillment_status="unfulfilled" if remote.status != "shipped" else "fulfilled",
        financial_status=remote.financial_status,
        currency=remote.currency,
        subtotal=remote.subtotal,
        shipping_charged=remote.shipping_charged,
        tax=remote.tax,
        discount=remote.discount,
        total=remote.total,
        customer_name=remote.customer_name,
        customer_email=remote.customer_email,
        shipping_country=remote.shipping_country,
        placed_at=remote.placed_at,
        raw_payload=json.dumps(remote.raw, default=str),
    )
    db.add(order)
    await db.flush()

    fee_total = Decimal("0")
    for item in remote.items:
        variant = await variant_by_sku(db, channel.tenant_id, item.sku)
        cogs = q(variant.cogs) if variant else Decimal("0")
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=variant.id if variant else None,
                sku=item.sku,
                title=item.title,
                quantity=item.quantity,
                unit_price=item.unit_price,
                cogs_at_sale=cogs,
                marketplace_fee=item.marketplace_fee,
            )
        )
        fee_total += q(item.marketplace_fee)
        if variant:
            await apply_movement(
                db,
                tenant_id=channel.tenant_id,
                variant_id=variant.id,
                warehouse_id=wh.id,
                quantity_delta=item.quantity,
                reason="reserve",
                reference_type="order",
                reference_id=str(order.id),
                note=f"ingest {remote.order_number}",
            )
            if remote.status == "shipped":
                await apply_movement(
                    db,
                    tenant_id=channel.tenant_id,
                    variant_id=variant.id,
                    warehouse_id=wh.id,
                    quantity_delta=-item.quantity,
                    reason="sale",
                    reference_type="order",
                    reference_id=str(order.id),
                )
                await apply_movement(
                    db,
                    tenant_id=channel.tenant_id,
                    variant_id=variant.id,
                    warehouse_id=wh.id,
                    quantity_delta=item.quantity,
                    reason="release",
                    reference_type="order",
                    reference_id=str(order.id),
                )

    if fee_total:
        db.add(
            OrderCost(
                tenant_id=channel.tenant_id,
                order_id=order.id,
                cost_type="marketplace_fee",
                amount=fee_total,
                currency=remote.currency,
                source=channel.marketplace,
                note="ingested from marketplace",
            )
        )
    if remote.shipping_charged:
        estimated_ship_cost = q(remote.shipping_charged) * Decimal("0.7")
        db.add(
            OrderCost(
                tenant_id=channel.tenant_id,
                order_id=order.id,
                cost_type="shipping_cost",
                amount=estimated_ship_cost,
                currency=remote.currency,
                source="estimate",
                note="70% of charged shipping as fulfillment cost estimate",
            )
        )
    await db.flush()
    return order


async def ingest_channel_orders(db: AsyncSession, channel: Channel) -> dict[str, Any]:
    adapter = registry.get(channel.marketplace)
    remotes = await adapter.fetch_orders({})
    created = 0
    updated = 0
    for remote in remotes:
        before = (
            await db.execute(
                select(Order.id).where(Order.tenant_id == channel.tenant_id, Order.external_id == remote.external_id)
            )
        ).scalar_one_or_none()
        await ingest_remote_order(db, channel, remote)
        if before:
            updated += 1
        else:
            created += 1
    await db.commit()
    return {"channel": channel.code, "fetched": len(remotes), "created": created, "updated": updated}


async def list_orders(
    db: AsyncSession,
    tenant_id: int,
    status: str | None = None,
    channel_id: int | None = None,
) -> list[Order]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.costs), selectinload(Order.returns))
        .where(Order.tenant_id == tenant_id)
        .order_by(Order.id.desc())
    )
    if status:
        stmt = stmt.where(Order.status == status)
    if channel_id:
        stmt = stmt.where(Order.channel_id == channel_id)
    return list((await db.execute(stmt)).scalars().unique().all())
