"""Marketplace payout matching and discrepancy detection."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import registry
from app.models.finance import Discrepancy, Payout, PayoutMatch
from app.models.marketplace import Channel
from app.models.order import Order
from app.services.profit import q

ZERO = Decimal("0")


async def ingest_payouts(db: AsyncSession, channel: Channel) -> dict[str, Any]:
    adapter = registry.get(channel.marketplace)
    remotes = await adapter.fetch_payouts({})
    created = 0
    for remote in remotes:
        exists = (
            await db.execute(
                select(Payout).where(Payout.tenant_id == channel.tenant_id, Payout.external_id == remote.external_id)
            )
        ).scalar_one_or_none()
        if exists:
            continue
        payout = Payout(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            external_id=remote.external_id,
            amount=remote.amount,
            currency=remote.currency,
            status="paid" if remote.paid_at else "pending",
            paid_at=remote.paid_at,
            fee_total=remote.fee_total,
            expected_amount=ZERO,
            raw_payload=str(remote.raw),
        )
        db.add(payout)
        await db.flush()
        matched_total = ZERO
        for ext_id in remote.order_external_ids:
            order = (
                await db.execute(
                    select(Order).where(Order.tenant_id == channel.tenant_id, Order.external_id == ext_id)
                )
            ).scalar_one_or_none()
            if not order:
                db.add(
                    Discrepancy(
                        tenant_id=channel.tenant_id,
                        channel_id=channel.id,
                        payout_id=payout.id,
                        kind="unmatched_payout_line",
                        severity="medium",
                        amount=ZERO,
                        description=f"Payout {remote.external_id} references unknown order {ext_id}",
                        suggested_action="Import missing order or unlink the payout line",
                    )
                )
                continue
            db.add(
                PayoutMatch(
                    payout_id=payout.id,
                    order_id=order.id,
                    matched_amount=order.total,
                    match_confidence=Decimal("0.95"),
                    method="external_id",
                )
            )
            matched_total += q(order.total)
        payout.expected_amount = matched_total
        created += 1
        await _flag_amount_gap(db, channel, payout, matched_total)
    await _flag_missing_payouts(db, channel)
    await db.commit()
    return {"channel": channel.code, "payouts": created}


async def _flag_amount_gap(db: AsyncSession, channel: Channel, payout: Payout, matched_total: Decimal) -> None:
    gap = q(matched_total - q(payout.amount) - q(payout.fee_total))
    if abs(gap) < Decimal("0.05"):
        return
    kind = "underpaid" if gap > 0 else "overpaid"
    db.add(
        Discrepancy(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            payout_id=payout.id,
            kind=kind,
            severity="high" if abs(gap) > 10 else "medium",
            amount=abs(gap),
            description=f"Payout {payout.external_id}: expected {matched_total}, received {payout.amount} (fees {payout.fee_total})",
            suggested_action="Open a case with the marketplace or adjust fee mapping",
        )
    )


async def _flag_missing_payouts(db: AsyncSession, channel: Channel) -> None:
    orders = (
        await db.execute(
            select(Order).where(
                Order.tenant_id == channel.tenant_id,
                Order.channel_id == channel.id,
                Order.financial_status == "paid",
            )
        )
    ).scalars().all()
    matched_ids = set(
        (
            await db.execute(select(PayoutMatch.order_id))
        ).scalars().all()
    )
    for order in orders:
        if order.id in matched_ids:
            continue
        existing = (
            await db.execute(
                select(Discrepancy).where(
                    Discrepancy.tenant_id == channel.tenant_id,
                    Discrepancy.order_id == order.id,
                    Discrepancy.kind == "missing_payout",
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(
            Discrepancy(
                tenant_id=channel.tenant_id,
                channel_id=channel.id,
                order_id=order.id,
                kind="missing_payout",
                severity="high",
                amount=order.total,
                description=f"Order {order.order_number} is paid but has no matching payout",
                suggested_action="Wait for next settlement cycle or file a payment inquiry",
            )
        )


async def list_discrepancies(db: AsyncSession, tenant_id: int, status: str | None = None) -> list[Discrepancy]:
    stmt = select(Discrepancy).where(Discrepancy.tenant_id == tenant_id).order_by(Discrepancy.id.desc())
    if status:
        stmt = stmt.where(Discrepancy.status == status)
    return list((await db.execute(stmt)).scalars().all())
