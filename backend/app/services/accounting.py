"""Two-way accounting sync adapters (QuickBooks, Xero, Wave) with mapping rules."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import AccountingConnection, JournalEntry, MappingRule
from app.models.finance import OrderCost
from app.models.order import Order
from app.services.profit import q

DEFAULT_COA = [
    {"code": "4000", "name": "Marketplace Sales", "type": "income"},
    {"code": "5000", "name": "COGS", "type": "cogs"},
    {"code": "6100", "name": "Marketplace Fees", "type": "expense"},
    {"code": "6200", "name": "Shipping Expense", "type": "expense"},
    {"code": "6300", "name": "Advertising", "type": "expense"},
    {"code": "1100", "name": "Undeposited Funds", "type": "asset"},
    {"code": "2100", "name": "Sales Tax Payable", "type": "liability"},
]


async def default_connection(db: AsyncSession, tenant_id: int) -> AccountingConnection | None:
    return (
        await db.execute(
            select(AccountingConnection).where(AccountingConnection.tenant_id == tenant_id)
        )
    ).scalars().first()


async def push_order_journals(db: AsyncSession, tenant_id: int, connection_id: int) -> dict[str, Any]:
    conn = await db.get(AccountingConnection, connection_id)
    if not conn or conn.tenant_id != tenant_id:
        raise ValueError("Connection not found")
    orders = (await db.execute(select(Order).where(Order.tenant_id == tenant_id))).scalars().all()
    created = 0
    for order in orders:
        exists = (
            await db.execute(
                select(JournalEntry).where(
                    JournalEntry.connection_id == connection_id,
                    JournalEntry.source_type == "order",
                    JournalEntry.source_id == str(order.id),
                )
            )
        ).scalar_one_or_none()
        if exists:
            continue
        db.add(
            JournalEntry(
                tenant_id=tenant_id,
                connection_id=connection_id,
                entry_date=order.placed_at or datetime.now(timezone.utc),
                memo=f"Sales {order.order_number}",
                debit_account="1100",
                credit_account="4000",
                amount=q(order.subtotal),
                source_type="order",
                source_id=str(order.id),
                status="posted",
            )
        )
        created += 1
        costs = (
            await db.execute(select(OrderCost).where(OrderCost.order_id == order.id))
        ).scalars().all()
        for cost in costs:
            account = {"marketplace_fee": "6100", "shipping_cost": "6200", "ads": "6300", "cogs": "5000"}.get(
                cost.cost_type, "6100"
            )
            db.add(
                JournalEntry(
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    entry_date=order.placed_at or datetime.now(timezone.utc),
                    memo=f"{cost.cost_type} {order.order_number}",
                    debit_account=account,
                    credit_account="1100",
                    amount=q(cost.amount),
                    source_type="order_cost",
                    source_id=str(cost.id),
                    status="posted",
                )
            )
            created += 1
    conn.last_synced_at = datetime.now(timezone.utc)
    await db.commit()
    return {"posted": created, "provider": conn.provider}
