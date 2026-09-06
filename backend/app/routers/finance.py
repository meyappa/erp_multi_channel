from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.finance import Payout, PayoutMatch
from app.models.marketplace import Channel
from app.models.tenant import User
from app.services.profit import profit_report
from app.services.reconciliation import ingest_payouts, list_discrepancies

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/profit")
async def profit(
    channel_id: int | None = Query(None),
    sku: str | None = Query(None),
    period: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await profit_report(db, user.tenant_id, channel_id=channel_id, sku=sku, period=period)


@router.get("/payouts")
async def payouts(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(select(Payout).where(Payout.tenant_id == user.tenant_id).order_by(Payout.id.desc()))
    ).scalars().all()
    channels = {
        c.id: c.name
        for c in (await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id))).scalars().all()
    }
    out = []
    for p in rows:
        matches = (await db.execute(select(PayoutMatch).where(PayoutMatch.payout_id == p.id))).scalars().all()
        out.append(
            {
                "id": p.id,
                "external_id": p.external_id,
                "channel": channels.get(p.channel_id, ""),
                "amount": str(p.amount),
                "expected_amount": str(p.expected_amount),
                "fee_total": str(p.fee_total),
                "currency": p.currency,
                "status": p.status,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "matches": len(matches),
            }
        )
    return out


@router.get("/discrepancies")
async def discrepancies(
    status: str | None = Query("open"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await list_discrepancies(db, user.tenant_id, status=status)
    return [
        {
            "id": d.id,
            "kind": d.kind,
            "severity": d.severity,
            "amount": str(d.amount),
            "description": d.description,
            "suggested_action": d.suggested_action,
            "status": d.status,
            "order_id": d.order_id,
            "payout_id": d.payout_id,
        }
        for d in rows
    ]


@router.post("/reconcile")
async def reconcile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant", "manager")),
):
    channels = (
        await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id, Channel.is_active.is_(True)))
    ).scalars().all()
    results = []
    for ch in channels:
        results.append(await ingest_payouts(db, ch))
    return {"results": results}


@router.post("/discrepancies/{disc_id}/resolve")
async def resolve_disc(
    disc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant")),
):
    from app.models.finance import Discrepancy

    d = await db.get(Discrepancy, disc_id)
    if d and d.tenant_id == user.tenant_id:
        d.status = "resolved"
        await db.commit()
    return {"ok": True}
