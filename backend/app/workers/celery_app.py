"""Celery app for production deployments with Redis."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "channelforge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery.conf.beat_schedule = {
    "sync-inventory": {"task": "app.workers.tasks.sync_all_inventory", "schedule": 60.0},
    "ingest-orders": {"task": "app.workers.tasks.ingest_all_orders", "schedule": 45.0},
    "anomaly-scan": {"task": "app.workers.tasks.scan_anomalies", "schedule": 120.0},
}
celery.conf.timezone = "UTC"
