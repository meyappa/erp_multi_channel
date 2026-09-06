"""Centralized RMA workflow with inventory restock and AI reason tagging."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, ReturnItem, ReturnRequest
from app.services.inventory import apply_movement
from app.services.ai import categorize_return_reason, log_automation

REASON_MAP = {
    "defective": "quality",
    "damaged": "quality",
    "not_as_described": "listing",
    "wrong_item": "fulfillment",
    "changed_mind": "buyer",
    "late_delivery": "logistics",
    "other": "unclassified",
}


def next_rma(n: int) -> str:
    return f"RMA-{10000 + n}"


async def create_return(
    db: AsyncSession,
    *,
    tenant_id: int,
    order_id: int,
    reason_code: str,
    reason_text: str,
    items: list[dict[str, Any]],
    refund_amount: Decimal,
) -> ReturnRequest:
    order = await db.get(Order, order_id)
    if not order or order.tenant_id != tenant_id:
        raise ValueError("Order not found")
    count = (await db.execute(select(ReturnRequest.id))).scalars().all()
    ai = categorize_return_reason(reason_code, reason_text)
    rr = ReturnRequest(
        tenant_id=tenant_id,
        order_id=order.id,
        channel_id=order.channel_id,
        rma_number=next_rma(len(count) + 1),
        status="requested",
        reason_code=reason_code,
        reason_text=reason_text,
        ai_category=ai["category"],
        suggested_resolution=ai["resolution"],
        refund_amount=refund_amount,
        restock=False,
    )
    db.add(rr)
    await db.flush()
    for it in items:
        db.add(
            ReturnItem(
                return_id=rr.id,
                sku=it.get("sku", ""),
                quantity=int(it.get("quantity", 1)),
                condition=it.get("condition", "unopened"),
            )
        )
    await log_automation(
        db,
        tenant_id=tenant_id,
        job_type="return_categorize",
        trigger="user",
        actor="returns-agent",
        summary=f"RMA {rr.rma_number} categorized as {ai['category']} → {ai['resolution']}",
        entity_type="return",
        entity_id=str(rr.id),
        input_data={"reason_code": reason_code, "reason_text": reason_text},
        output_data=ai,
    )
    await db.commit()
    await db.refresh(rr)
    return rr


async def decide_return(db: AsyncSession, tenant_id: int, return_id: int, action: str, restock: bool) -> ReturnRequest:
    rr = (
        await db.execute(
            select(ReturnRequest)
            .options(selectinload(ReturnRequest.items), selectinload(ReturnRequest.order))
            .where(ReturnRequest.id == return_id, ReturnRequest.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if not rr:
        raise ValueError("Return not found")
    if action == "approve":
        rr.status = "approved"
        rr.restock = restock
        rr.approved_at = datetime.now(timezone.utc)
        if restock and rr.order and rr.order.warehouse_id:
            from app.services.inventory import variant_by_sku

            for item in rr.items:
                variant = await variant_by_sku(db, tenant_id, item.sku)
                if not variant:
                    continue
                await apply_movement(
                    db,
                    tenant_id=tenant_id,
                    variant_id=variant.id,
                    warehouse_id=rr.order.warehouse_id,
                    quantity_delta=item.quantity,
                    reason="return_restock",
                    reference_type="rma",
                    reference_id=rr.rma_number,
                )
    elif action == "reject":
        rr.status = "rejected"
    elif action == "refund":
        rr.status = "refunded"
    await db.commit()
    await db.refresh(rr)
    return rr
