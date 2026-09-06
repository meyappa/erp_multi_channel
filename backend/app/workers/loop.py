"""In-process polling loop used when Redis/Celery is unavailable (dev & preview)."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models.marketplace import Channel
from app.services.ai import detect_anomalies, log_automation
from app.services.inventory import sync_channel_inventory
from app.services.orders import ingest_channel_orders

log = logging.getLogger("channelforge.sync")
_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def _tick() -> None:
    settings = get_settings()
    async with SessionLocal() as db:
        channels = (
            await db.execute(select(Channel).where(Channel.is_active.is_(True)))
        ).scalars().all()
        for ch in channels:
            try:
                await ingest_channel_orders(db, ch)
                await sync_channel_inventory(db, ch)
            except Exception as exc:
                log.warning("sync failed for %s: %s", ch.code, exc)
        tenants = {ch.tenant_id for ch in channels}
        for tid in tenants:
            try:
                alerts = await detect_anomalies(db, tid, trigger="agent", actor="sync-health-agent")
                _ = alerts
            except Exception as exc:
                log.warning("anomaly scan failed: %s", exc)
                try:
                    await log_automation(
                        db,
                        tenant_id=tid,
                        job_type="sync_health",
                        trigger="agent",
                        actor="sync-health-agent",
                        status="failed",
                        summary=f"Background anomaly scan failed: {exc}",
                        error=str(exc),
                        commit=True,
                    )
                except Exception:
                    pass
    await asyncio.sleep(max(settings.sync_poll_interval_seconds, 15))


async def _run() -> None:
    while not _stop.is_set():
        try:
            await _tick()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.warning("background tick failed: %s", exc)
            await asyncio.sleep(10)


async def start_background_sync() -> None:
    global _task
    _stop.clear()
    if _task is None or _task.done():
        _task = asyncio.create_task(_run())


async def stop_background_sync() -> None:
    global _task
    _stop.set()
    if _task:
        _task.cancel()
        _task = None
