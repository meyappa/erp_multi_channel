"""Celery tasks wrapping the same services used by the in-process loop."""

from __future__ import annotations

import asyncio

from app.database import SessionLocal
from app.models.marketplace import Channel
from app.services.ai import detect_anomalies, run_forecasts
from app.services.inventory import sync_channel_inventory
from app.services.orders import ingest_channel_orders
from app.services.reconciliation import ingest_payouts
from app.workers.celery_app import celery
from sqlalchemy import select


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _all_channels():
    async with SessionLocal() as db:
        return list((await db.execute(select(Channel).where(Channel.is_active.is_(True)))).scalars().all())


@celery.task(name="app.workers.tasks.sync_all_inventory")
def sync_all_inventory() -> str:
    async def _go():
        async with SessionLocal() as db:
            channels = (await db.execute(select(Channel).where(Channel.is_active.is_(True)))).scalars().all()
            for ch in channels:
                await sync_channel_inventory(db, ch)
        return "ok"

    return _run(_go())


@celery.task(name="app.workers.tasks.ingest_all_orders")
def ingest_all_orders() -> str:
    async def _go():
        async with SessionLocal() as db:
            channels = (await db.execute(select(Channel).where(Channel.is_active.is_(True)))).scalars().all()
            for ch in channels:
                await ingest_channel_orders(db, ch)
        return "ok"

    return _run(_go())


@celery.task(name="app.workers.tasks.scan_anomalies")
def scan_anomalies() -> str:
    async def _go():
        async with SessionLocal() as db:
            channels = (await db.execute(select(Channel))).scalars().all()
            for tid in {c.tenant_id for c in channels}:
                await detect_anomalies(db, tid)
                await run_forecasts(db, tid)
        return "ok"

    return _run(_go())


@celery.task(name="app.workers.tasks.reconcile_payouts")
def reconcile_payouts() -> str:
    async def _go():
        async with SessionLocal() as db:
            channels = (await db.execute(select(Channel).where(Channel.is_active.is_(True)))).scalars().all()
            for ch in channels:
                await ingest_payouts(db, ch)
        return "ok"

    return _run(_go())
