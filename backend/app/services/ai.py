"""Cost-controlled AI helpers with deterministic fallbacks (no live LLM required)."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.ai import AiAutomationLog, AnomalyAlert, Forecast, ListingSuggestion
from app.models.catalog import Listing, Product, ProductVariant
from app.models.finance import Discrepancy
from app.models.inventory import InventoryBalance
from app.models.order import OrderItem

settings = get_settings()

JOB_LABELS = {
    "forecast": "Inventory forecasting",
    "listing_optimize": "Listing optimization",
    "anomaly_scan": "Anomaly detection",
    "chat": "Natural language query",
    "return_categorize": "Return reason categorization",
    "sync_health": "Sync health monitor",
    "profit_alert": "Profitability alert",
    "order_routing": "Smart order routing",
}


async def log_automation(
    db: AsyncSession,
    *,
    tenant_id: int,
    job_type: str,
    summary: str,
    trigger: str = "user",
    actor: str = "system",
    status: str = "success",
    entity_type: str = "",
    entity_id: str = "",
    input_data: Any = None,
    output_data: Any = None,
    tokens_used: int = 0,
    duration_ms: int = 0,
    error: str | None = None,
    commit: bool = False,
) -> AiAutomationLog:
    started = datetime.now(timezone.utc)
    row = AiAutomationLog(
        tenant_id=tenant_id,
        job_type=job_type,
        trigger=trigger,
        actor=actor,
        status=status,
        summary=summary[:400],
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        model=settings.user_llm_model if settings.user_llm_api_key else "heuristic",
        tokens_used=tokens_used,
        duration_ms=duration_ms,
        input_json=json.dumps(input_data or {}, default=str)[:8000],
        output_json=json.dumps(output_data or {}, default=str)[:8000],
        error=error,
        created_at=started,
    )
    db.add(row)
    await db.flush()
    if commit:
        await db.commit()
        await db.refresh(row)
    return row


def categorize_return_reason(code: str, text: str) -> dict[str, str]:
    blob = f"{code} {text}".lower()
    rules = [
        (("broken", "defect", "quality", "not working"), "quality", "inspect_and_replace"),
        (("damage", "crushed", "wet"), "quality", "restock_if_sellable"),
        (("wrong", "incorrect", "mismatch"), "fulfillment", "reship_correct_sku"),
        (("late", "delay", "slow"), "logistics", "partial_refund_shipping"),
        (("mind", "want", " palitan", "change"), "buyer", "restock_and_refund"),
        (("photo", "describe", "listing"), "listing", "update_listing_copy"),
    ]
    for keys, cat, res in rules:
        if any(k in blob for k in keys):
            return {"category": cat, "resolution": res}
    return {"category": "unclassified", "resolution": "manual_review"}


def optimize_listing(title: str, description: str, marketplace: str) -> dict[str, str]:
    clean = " ".join(title.split())
    words = [w for w in clean.replace("—", " ").split() if w]
    bullets = [
        f"Premium build quality designed for {marketplace.title()} shoppers",
        "Fast dispatch from multi-warehouse network",
        "Compatible accessories and 12-month coverage",
        "Easy returns via ChannelForge RMA",
        "Bundle-ready SKU with accurate inventory sync",
    ]
    price_hint = "Hold price if conversion > 3%; test -5% promo for 7 days if aged stock."
    new_title = clean
    if len(new_title) < 40:
        new_title = f"{clean} | Official Stock | Fast Ship"
    return {
        "title": new_title[:200],
        "bullets": "\n".join(f"- {b}" for b in bullets),
        "description": (description or "Ready to ship from our bonded warehouses.")[:2000],
        "pricing": price_hint,
        "keywords": ", ".join(words[:8]),
    }


def chat_answer(question: str, context: dict[str, Any]) -> str:
    q = question.lower()
    if "profit" in q or "margin" in q:
        return (
            f"Gross profit this period is {context.get('gross_profit', 'n/a')} "
            f"({context.get('margin_pct', 'n/a')}% margin). Formula: {context.get('formula', '')}."
        )
    if "stock" in q or "inventory" in q or "sku" in q:
        return (
            f"Catalog has {context.get('sku_count', 0)} SKUs across "
            f"{context.get('warehouse_count', 0)} warehouses. Low-stock items: {context.get('low_stock', 'none')}."
        )
    if "return" in q or "rma" in q:
        return f"Open RMAs: {context.get('open_returns', 0)}. Top AI category: {context.get('top_return_reason', 'n/a')}."
    if "payout" in q or "reconcil" in q:
        return f"Open discrepancies: {context.get('open_discrepancies', 0)}. Review missing payouts first."
    if "forecast" in q or "replenish" in q:
        return "Run AI forecast from Inventory to get 30-day demand and replenishment suggestions."
    return (
        "I can help with profit, inventory, returns, payouts, and forecasts. "
        "Try: 'What is our margin by channel?' or 'Which SKUs need replenishment?'"
    )


async def run_forecasts(db: AsyncSession, tenant_id: int) -> list[dict[str, Any]]:
    items = (await db.execute(select(OrderItem))).scalars().all()
    sold: dict[int, int] = defaultdict(int)
    for it in items:
        if it.variant_id:
            sold[it.variant_id] += it.quantity
    bals = (
        await db.execute(select(InventoryBalance).where(InventoryBalance.tenant_id == tenant_id))
    ).scalars().all()
    out: list[dict[str, Any]] = []
    for bal in bals:
        history = sold.get(bal.variant_id, 0)
        daily = max(history / 30.0, 0.2)
        month = datetime.now(timezone.utc).month
        season = 1.0 + 0.15 * math.sin((month / 12) * math.pi * 2)
        predicted = int(round(daily * 30 * season))
        cover = max(int(bal.available / daily) if daily else 99, 0)
        suggested = max(predicted - bal.available + bal.safety_stock, 0)
        fc = Forecast(
            tenant_id=tenant_id,
            variant_id=bal.variant_id,
            warehouse_id=bal.warehouse_id,
            horizon_days=30,
            predicted_demand=predicted,
            suggested_replenish=suggested,
            seasonality_index=Decimal(str(round(season, 4))),
            method="seasonal_moving_average",
            confidence=Decimal("0.72"),
        )
        db.add(fc)
        out.append(
            {
                "variant_id": bal.variant_id,
                "available": bal.available,
                "predicted_demand_30d": predicted,
                "days_of_cover": cover,
                "suggested_replenish": suggested,
                "seasonality_index": float(round(season, 4)),
            }
        )
    await log_automation(
        db,
        tenant_id=tenant_id,
        job_type="forecast",
        trigger="user",
        actor="forecast-agent",
        summary=f"30-day demand forecast for {len(out)} SKU/warehouse rows",
        entity_type="forecast",
        input_data={"horizon_days": 30, "balances": len(bals)},
        output_data={"rows": len(out), "replenish_skus": sum(1 for r in out if r["suggested_replenish"] > 0)},
    )
    await db.commit()
    return out


async def detect_anomalies(
    db: AsyncSession, tenant_id: int, trigger: str = "user", actor: str = "anomaly-agent"
) -> list[AnomalyAlert]:
    alerts: list[AnomalyAlert] = []
    discs = (
        await db.execute(
            select(Discrepancy).where(Discrepancy.tenant_id == tenant_id, Discrepancy.status == "open")
        )
    ).scalars().all()
    if len(discs) >= 3:
        a = AnomalyAlert(
            tenant_id=tenant_id,
            kind="fee_anomaly",
            severity="high",
            title="Multiple open payout discrepancies",
            detail=f"{len(discs)} open discrepancies need finance review",
            entity_type="discrepancy",
        )
        db.add(a)
        alerts.append(a)
    bals = (
        await db.execute(select(InventoryBalance).where(InventoryBalance.tenant_id == tenant_id))
    ).scalars().all()
    for bal in bals:
        if bal.on_hand < bal.safety_stock:
            a = AnomalyAlert(
                tenant_id=tenant_id,
                kind="stock_mismatch",
                severity="medium",
                title=f"Safety stock breach on variant {bal.variant_id}",
                detail=f"on_hand={bal.on_hand} safety={bal.safety_stock}",
                entity_type="inventory",
                entity_id=str(bal.variant_id),
            )
            db.add(a)
            alerts.append(a)
    if trigger != "agent":
        await log_automation(
            db,
            tenant_id=tenant_id,
            job_type="anomaly_scan",
            trigger=trigger,
            actor=actor,
            summary=f"Anomaly scan raised {len(alerts)} alert(s)",
            entity_type="anomaly_alert",
            input_data={"open_discrepancies": len(discs), "balances": len(bals)},
            output_data={"alerts": len(alerts), "kinds": [a.kind for a in alerts]},
        )
    await db.commit()
    return alerts


async def suggest_listing_copy(db: AsyncSession, tenant_id: int, listing_id: int) -> dict[str, Any]:
    listing = await db.get(Listing, listing_id)
    if not listing or listing.tenant_id != tenant_id:
        raise ValueError("Listing not found")
    product = await db.get(Product, listing.product_id)
    opt = optimize_listing(listing.title, listing.description or (product.description if product else ""), "channel")
    for field, value in (("title", opt["title"]), ("description", opt["description"])):
        db.add(
            ListingSuggestion(
                tenant_id=tenant_id,
                listing_id=listing.id,
                field_name=field,
                current_value=listing.title if field == "title" else listing.description,
                suggested_value=value,
                rationale="Heuristic SEO + conversion template (LLM optional via USER_LLM_API_KEY)",
            )
        )
    await log_automation(
        db,
        tenant_id=tenant_id,
        job_type="listing_optimize",
        trigger="user",
        actor="listing-agent",
        summary=f"Optimized listing #{listing_id}: {opt['title'][:80]}",
        entity_type="listing",
        entity_id=str(listing_id),
        input_data={"listing_id": listing_id, "title": listing.title},
        output_data=opt,
    )
    await db.commit()
    return opt
