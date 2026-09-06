from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.marketplace import Channel
from app.models.order import Order
from app.models.tenant import User
from app.services.orders import ingest_channel_orders, list_orders
from app.services.profit import calculate_order_profit

router = APIRouter(prefix="/api/orders", tags=["orders"])


def serialize_order(o: Order, channel_name: str = "") -> dict:
    return {
        "id": o.id,
        "order_number": o.order_number,
        "external_id": o.external_id,
        "channel_id": o.channel_id,
        "channel": channel_name,
        "status": o.status,
        "fulfillment_status": o.fulfillment_status,
        "financial_status": o.financial_status,
        "currency": o.currency,
        "subtotal": str(o.subtotal),
        "shipping_charged": str(o.shipping_charged),
        "tax": str(o.tax),
        "total": str(o.total),
        "customer_name": o.customer_name,
        "customer_email": o.customer_email,
        "shipping_country": o.shipping_country,
        "placed_at": o.placed_at.isoformat() if o.placed_at else None,
        "items": [
            {
                "id": it.id,
                "sku": it.sku,
                "title": it.title,
                "quantity": it.quantity,
                "unit_price": str(it.unit_price),
                "cogs_at_sale": str(it.cogs_at_sale),
                "marketplace_fee": str(it.marketplace_fee),
            }
            for it in (o.items or [])
        ],
    }


@router.get("")
async def get_orders(
    status: str | None = Query(None),
    channel_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    orders = await list_orders(db, user.tenant_id, status=status, channel_id=channel_id)
    channels = {
        c.id: c.name
        for c in (await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id))).scalars().all()
    }
    return [serialize_order(o, channels.get(o.channel_id, "")) for o in orders]


@router.get("/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    o = (
        await db.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.costs), selectinload(Order.returns))
            .where(Order.id == order_id, Order.tenant_id == user.tenant_id)
        )
    ).scalar_one_or_none()
    if not o:
        raise HTTPException(404, "Order not found")
    ch = await db.get(Channel, o.channel_id)
    profit = await calculate_order_profit(db, o, persist=False)
    data = serialize_order(o, ch.name if ch else "")
    data["profit"] = profit
    data["costs"] = [
        {"type": c.cost_type, "amount": str(c.amount), "source": c.source, "note": c.note} for c in (o.costs or [])
    ]
    return data


@router.post("/ingest")
async def ingest(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    channels = (
        await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id, Channel.is_active.is_(True)))
    ).scalars().all()
    results = []
    for ch in channels:
        results.append(await ingest_channel_orders(db, ch))
    return {"results": results}
