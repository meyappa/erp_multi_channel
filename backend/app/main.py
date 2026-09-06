"""ChannelForge ERP API."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal, get_db, init_db
from app.deps import get_current_user
from app.models.inventory import SyncEvent
from app.models.marketplace import Channel, WebhookInbox
from app.models.tenant import User
from app.routers import accounting, ai, auth, catalog, channels, dashboard, finance, inventory, orders, returns
from app.seed import seed_if_empty
from app.services.inventory import sync_channel_inventory
from app.services.orders import ingest_channel_orders
from app.workers.loop import start_background_sync, stop_background_sync

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with SessionLocal() as db:
        await seed_if_empty(db)
    await start_background_sync()
    yield
    await stop_background_sync()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    description="Multi-channel ERP for Amazon, Shopee, Lazada, TikTok Shop, Shopify, and eBay.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(finance.router)
app.include_router(returns.router)
app.include_router(accounting.router)
app.include_router(ai.router)
app.include_router(channels.router)


@app.get("/api/health")
async def health():
    return {"ok": True, "service": settings.app_name, "time": datetime.now(timezone.utc).isoformat()}


@app.post("/api/webhooks/{marketplace}")
async def webhook(marketplace: str, request: Request):
    payload = await request.body()
    text = payload.decode("utf-8", errors="replace")
    async with SessionLocal() as db:
        inbox = WebhookInbox(
            tenant_id=1,
            marketplace=marketplace,
            event_type=request.headers.get("x-event-type", "unknown"),
            payload=text,
            signature=request.headers.get("x-signature", ""),
        )
        db.add(inbox)
        ch = (await db.execute(select(Channel).where(Channel.marketplace == marketplace))).scalars().first()
        if ch:
            try:
                data = json.loads(text or "{}")
            except json.JSONDecodeError:
                data = {}
            event_kind = str(data.get("event") or data.get("type") or "")
            if "order" in event_kind:
                await ingest_channel_orders(db, ch)
            else:
                await sync_channel_inventory(db, ch)
            inbox.processed = True
            inbox.processed_at = datetime.now(timezone.utc)
        await db.commit()
    return {"accepted": True}


@app.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            async with SessionLocal() as db:
                events = (
                    await db.execute(select(SyncEvent).order_by(SyncEvent.id.desc()).limit(5))
                ).scalars().all()
                await ws.send_json(
                    {
                        "type": "sync",
                        "at": datetime.now(timezone.utc).isoformat(),
                        "events": [{"id": e.id, "sku": e.entity_id, "status": e.status} for e in events],
                    }
                )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return


@app.get("/api/audit")
async def audit(user: User = Depends(get_current_user)):
    from app.models.tenant import AuditLog
    from sqlalchemy.ext.asyncio import AsyncSession

    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(AuditLog).where(AuditLog.tenant_id == user.tenant_id).order_by(AuditLog.id.desc()).limit(100)
            )
        ).scalars().all()
        return [{"id": a.id, "action": a.action, "entity_type": a.entity_type, "entity_id": a.entity_id} for a in rows]
