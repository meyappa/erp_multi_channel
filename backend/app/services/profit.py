"""Gross profit engine.

Formula (auditable, reproducible):
    gross_profit = selling_price - cogs - marketplace_fees - shipping_cost - returns_refunds - ads

Every calculation writes a GrossProfitSnapshot so finance teams can replay history.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finance import GrossProfitSnapshot, OrderCost
from app.models.marketplace import Channel
from app.models.order import Order, OrderItem, ReturnRequest

Q = Decimal("0.0001")
ZERO = Decimal("0")

FORMULA = "selling_price - cogs - marketplace_fees - shipping_cost - returns_refunds - ads"


def q(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Q, rounding=ROUND_HALF_UP)


def compute_line(
    selling_price: Decimal,
    cogs: Decimal,
    marketplace_fees: Decimal,
    shipping_cost: Decimal = ZERO,
    returns_refunds: Decimal = ZERO,
    ads: Decimal = ZERO,
) -> dict[str, Decimal]:
    selling = q(selling_price)
    cost_cogs = q(cogs)
    fees = q(marketplace_fees)
    ship = q(shipping_cost)
    refunds = q(returns_refunds)
    ad = q(ads)
    profit = q(selling - cost_cogs - fees - ship - refunds - ad)
    margin = q((profit / selling) * Decimal("100")) if selling else ZERO
    return {
        "selling_price": selling,
        "cogs": cost_cogs,
        "marketplace_fees": fees,
        "shipping_cost": ship,
        "returns_refunds": refunds,
        "ads": ad,
        "gross_profit": profit,
        "margin_pct": margin,
    }


def costs_by_type(costs: list[OrderCost]) -> dict[str, Decimal]:
    buckets: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for c in costs:
        buckets[c.cost_type] += q(c.amount)
    return buckets


async def calculate_order_profit(db: AsyncSession, order: Order, persist: bool = True) -> dict[str, Any]:
    if order.items is None:
        await db.refresh(order, attribute_names=["items", "costs", "returns"])

    selling = q(order.subtotal)
    cogs = q(sum((q(it.cogs_at_sale) * it.quantity for it in order.items), ZERO))
    buckets = costs_by_type(list(order.costs or []))
    fees = buckets.get("marketplace_fee", ZERO) + q(
        sum((q(it.marketplace_fee) for it in order.items), ZERO)
    )
    shipping = buckets.get("shipping_cost", ZERO)
    ads = buckets.get("ads", ZERO)
    refunds = q(sum((q(r.refund_amount) for r in (order.returns or []) if r.status in ("approved", "refunded")), ZERO))
    refunds += buckets.get("return_refund", ZERO)

    result = compute_line(selling, cogs, fees, shipping, refunds, ads)
    channel = await db.get(Channel, order.channel_id)
    channel_code = channel.code if channel else ""

    sku = order.items[0].sku if order.items else ""
    snapshot = GrossProfitSnapshot(
        tenant_id=order.tenant_id,
        order_id=order.id,
        sku=sku,
        channel_code=channel_code,
        selling_price=result["selling_price"],
        cogs=result["cogs"],
        marketplace_fees=result["marketplace_fees"],
        shipping_cost=result["shipping_cost"],
        returns_refunds=result["returns_refunds"],
        ads=result["ads"],
        gross_profit=result["gross_profit"],
        margin_pct=result["margin_pct"],
        formula=FORMULA,
        period=(order.placed_at.strftime("%Y-%m") if order.placed_at else ""),
    )
    if persist:
        db.add(snapshot)
        await db.flush()

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "channel": channel_code,
        "sku": sku,
        "currency": order.currency,
        **{k: str(v) for k, v in result.items()},
        "formula": FORMULA,
        "snapshot_id": snapshot.id if persist else None,
        "items": [
            {
                "sku": it.sku,
                "qty": it.quantity,
                "unit_price": str(q(it.unit_price)),
                "cogs": str(q(it.cogs_at_sale)),
                "fee": str(q(it.marketplace_fee)),
            }
            for it in order.items
        ],
    }


async def profit_report(
    db: AsyncSession,
    tenant_id: int,
    channel_id: int | None = None,
    sku: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    stmt = (
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.costs), selectinload(Order.returns))
        .where(Order.tenant_id == tenant_id)
    )
    if channel_id:
        stmt = stmt.where(Order.channel_id == channel_id)
    orders = (await db.execute(stmt)).scalars().unique().all()

    rows: list[dict[str, Any]] = []
    by_channel: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_sku: dict[str, Decimal] = defaultdict(lambda: ZERO)
    by_period: dict[str, Decimal] = defaultdict(lambda: ZERO)
    totals = {k: ZERO for k in ("selling_price", "cogs", "marketplace_fees", "shipping_cost", "returns_refunds", "ads", "gross_profit")}

    for order in orders:
        calc = await calculate_order_profit(db, order, persist=False)
        if sku and calc["sku"] != sku:
            continue
        p = order.placed_at.strftime("%Y-%m") if order.placed_at else ""
        if period and p != period:
            continue
        rows.append(calc)
        gp = q(calc["gross_profit"])
        by_channel[calc["channel"]] += gp
        by_sku[calc["sku"]] += gp
        by_period[p] += gp
        for k in totals:
            totals[k] += q(calc[k])

    selling = totals["selling_price"]
    return {
        "totals": {k: str(q(v)) for k, v in totals.items()},
        "margin_pct": str(q((totals["gross_profit"] / selling) * Decimal("100")) if selling else ZERO),
        "formula": FORMULA,
        "by_channel": {k: str(q(v)) for k, v in by_channel.items()},
        "by_sku": {k: str(q(v)) for k, v in by_sku.items()},
        "by_period": {k: str(q(v)) for k, v in sorted(by_period.items())},
        "orders": rows,
        "count": len(rows),
    }
