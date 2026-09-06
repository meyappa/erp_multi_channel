from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.catalog import Listing, Product
from app.models.finance import Discrepancy
from app.models.inventory import InventoryBalance, SyncEvent
from app.models.marketplace import Channel
from app.models.order import Order, ReturnRequest
from app.models.tenant import User
from app.services.profit import profit_report

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def overview(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tid = user.tenant_id
    orders_n = (await db.execute(select(func.count(Order.id)).where(Order.tenant_id == tid))).scalar() or 0
    products_n = (await db.execute(select(func.count(Product.id)).where(Product.tenant_id == tid))).scalar() or 0
    listings_n = (await db.execute(select(func.count(Listing.id)).where(Listing.tenant_id == tid))).scalar() or 0
    open_r = (
        await db.execute(
            select(func.count(ReturnRequest.id)).where(ReturnRequest.tenant_id == tid, ReturnRequest.status == "requested")
        )
    ).scalar() or 0
    open_d = (
        await db.execute(
            select(func.count(Discrepancy.id)).where(Discrepancy.tenant_id == tid, Discrepancy.status == "open")
        )
    ).scalar() or 0
    channels = (await db.execute(select(Channel).where(Channel.tenant_id == tid))).scalars().all()
    bals = (await db.execute(select(InventoryBalance).where(InventoryBalance.tenant_id == tid))).scalars().all()
    units = sum(b.on_hand for b in bals)
    report = await profit_report(db, tid)
    events = (
        await db.execute(select(SyncEvent).where(SyncEvent.tenant_id == tid).order_by(SyncEvent.id.desc()).limit(8))
    ).scalars().all()
    return {
        "kpis": {
            "orders": orders_n,
            "products": products_n,
            "listings": listings_n,
            "open_returns": open_r,
            "open_discrepancies": open_d,
            "units_on_hand": units,
            "gross_profit": report["totals"]["gross_profit"],
            "margin_pct": report["margin_pct"],
            "revenue": report["totals"]["selling_price"],
        },
        "channels": [
            {
                "id": c.id,
                "name": c.name,
                "marketplace": c.marketplace,
                "status": c.status,
                "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            }
            for c in channels
        ],
        "profit_by_channel": report["by_channel"],
        "profit_by_period": report["by_period"],
        "recent_sync": [
            {"id": e.id, "entity_id": e.entity_id, "status": e.status, "direction": e.direction} for e in events
        ],
        "formula": report["formula"],
    }
