from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.inventory import InventoryMovement, SyncEvent, Warehouse
from app.models.marketplace import Channel
from app.models.tenant import User
from app.schemas import InventoryAdjustIn
from app.services import inventory as inv
from app.services.ai import run_forecasts

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("/warehouses")
async def warehouses(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (await db.execute(select(Warehouse).where(Warehouse.tenant_id == user.tenant_id))).scalars().all()
    return [{"id": w.id, "code": w.code, "name": w.name, "country": w.country, "is_default": w.is_default} for w in rows]


@router.get("/balances")
async def balances(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await inv.inventory_matrix(db, user.tenant_id)


@router.post("/adjust")
async def adjust(
    body: InventoryAdjustIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    bal = await inv.apply_movement(
        db,
        tenant_id=user.tenant_id,
        variant_id=body.variant_id,
        warehouse_id=body.warehouse_id,
        quantity_delta=body.quantity_delta,
        reason=body.reason,
        reference_type="manual",
        note=body.note,
    )
    await db.commit()
    return {"on_hand": bal.on_hand, "reserved": bal.reserved, "available": bal.available, "version": bal.version}


@router.post("/sync")
async def sync_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    channels = (
        await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id, Channel.is_active.is_(True)))
    ).scalars().all()
    results = []
    for ch in channels:
        results.append(await inv.sync_channel_inventory(db, ch))
    return {"results": results}


@router.post("/sync/{channel_id}")
async def sync_one(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    ch = await db.get(Channel, channel_id)
    if not ch or ch.tenant_id != user.tenant_id:
        raise HTTPException(404, "Channel not found")
    return await inv.sync_channel_inventory(db, ch)


@router.get("/sync-events")
async def sync_events(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(SyncEvent).where(SyncEvent.tenant_id == user.tenant_id).order_by(SyncEvent.id.desc()).limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": e.id,
            "channel_id": e.channel_id,
            "direction": e.direction,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "status": e.status,
            "conflict_policy": e.conflict_policy,
            "payload": e.payload,
            "result": e.result,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


@router.get("/movements")
async def movements(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(InventoryMovement)
            .where(InventoryMovement.tenant_id == user.tenant_id)
            .order_by(InventoryMovement.id.desc())
            .limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": m.id,
            "variant_id": m.variant_id,
            "warehouse_id": m.warehouse_id,
            "quantity_delta": m.quantity_delta,
            "reason": m.reason,
            "reference_type": m.reference_type,
            "reference_id": m.reference_id,
            "note": m.note,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


@router.post("/forecast")
async def forecast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    return {"forecasts": await run_forecasts(db, user.tenant_id)}
