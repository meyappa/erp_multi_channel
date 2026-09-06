from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.accounting import AccountingConnection, JournalEntry, MappingRule
from app.models.tenant import User
from app.schemas import MappingRuleIn
from app.services.accounting import DEFAULT_COA, push_order_journals

router = APIRouter(prefix="/api/accounting", tags=["accounting"])


@router.get("/connections")
async def connections(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(select(AccountingConnection).where(AccountingConnection.tenant_id == user.tenant_id))
    ).scalars().all()
    return [
        {
            "id": c.id,
            "provider": c.provider,
            "name": c.name,
            "status": c.status,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "chart_of_accounts": DEFAULT_COA,
        }
        for c in rows
    ]


@router.get("/mappings")
async def mappings(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (await db.execute(select(MappingRule).where(MappingRule.tenant_id == user.tenant_id))).scalars().all()
    return [
        {
            "id": r.id,
            "connection_id": r.connection_id,
            "source_type": r.source_type,
            "source_code": r.source_code,
            "target_account": r.target_account,
            "target_account_name": r.target_account_name,
        }
        for r in rows
    ]


@router.post("/mappings")
async def add_mapping(
    body: MappingRuleIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant")),
):
    r = MappingRule(tenant_id=user.tenant_id, **body.model_dump())
    db.add(r)
    await db.commit()
    return {"id": r.id}


@router.get("/journals")
async def journals(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(JournalEntry).where(JournalEntry.tenant_id == user.tenant_id).order_by(JournalEntry.id.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": j.id,
            "memo": j.memo,
            "debit_account": j.debit_account,
            "credit_account": j.credit_account,
            "amount": str(j.amount),
            "source_type": j.source_type,
            "status": j.status,
            "entry_date": j.entry_date.isoformat() if j.entry_date else None,
        }
        for j in rows
    ]


@router.post("/sync/{connection_id}")
async def sync(
    connection_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "accountant")),
):
    try:
        return await push_order_journals(db, user.tenant_id, connection_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
