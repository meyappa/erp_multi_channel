from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters import registry
from app.database import get_db
from app.deps import get_current_user
from app.models.marketplace import Channel
from app.models.tenant import User

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("")
async def list_channels(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (await db.execute(select(Channel).where(Channel.tenant_id == user.tenant_id))).scalars().all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "marketplace": c.marketplace,
            "region": c.region,
            "status": c.status,
            "sync_mode": c.sync_mode,
            "rate_limit_rpm": c.rate_limit_rpm,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "is_active": c.is_active,
        }
        for c in rows
    ]


@router.get("/adapters")
async def adapters(user: User = Depends(get_current_user)):
    _ = user
    return [
        {
            "code": a.code,
            "display_name": a.display_name,
            "rate_limit_rpm": a.default_rate_limit_rpm,
            "supports_webhooks": a.supports_webhooks,
            "fee_rate": str(a.fee_rate),
        }
        for a in registry.all()
    ]
