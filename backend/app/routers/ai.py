from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.ai import AiAutomationLog, AnomalyAlert
from app.models.catalog import Product
from app.models.finance import Discrepancy
from app.models.inventory import InventoryBalance, Warehouse
from app.models.order import ReturnRequest
from app.models.tenant import User
from app.schemas import ChatIn
from app.services.ai import JOB_LABELS, chat_answer, detect_anomalies, log_automation, suggest_listing_copy
from app.services.profit import profit_report

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
async def chat(body: ChatIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    report = await profit_report(db, user.tenant_id)
    sku_count = (await db.execute(select(func.count(Product.id)).where(Product.tenant_id == user.tenant_id))).scalar() or 0
    wh_count = (await db.execute(select(func.count(Warehouse.id)).where(Warehouse.tenant_id == user.tenant_id))).scalar() or 0
    open_r = (
        await db.execute(
            select(func.count(ReturnRequest.id)).where(
                ReturnRequest.tenant_id == user.tenant_id, ReturnRequest.status == "requested"
            )
        )
    ).scalar() or 0
    open_d = (
        await db.execute(
            select(func.count(Discrepancy.id)).where(Discrepancy.tenant_id == user.tenant_id, Discrepancy.status == "open")
        )
    ).scalar() or 0
    bals = (await db.execute(select(InventoryBalance).where(InventoryBalance.tenant_id == user.tenant_id))).scalars().all()
    low = [str(b.variant_id) for b in bals if b.on_hand <= b.safety_stock]
    ctx = {
        "gross_profit": report["totals"]["gross_profit"],
        "margin_pct": report["margin_pct"],
        "formula": report["formula"],
        "sku_count": sku_count,
        "warehouse_count": wh_count,
        "open_returns": open_r,
        "open_discrepancies": open_d,
        "low_stock": ", ".join(low[:8]) or "none",
        "top_return_reason": "listing",
    }
    reply = chat_answer(body.message, ctx)
    await log_automation(
        db,
        tenant_id=user.tenant_id,
        job_type="chat",
        trigger="user",
        actor=user.email,
        summary=f"Chat: {body.message[:120]}",
        entity_type="chat",
        input_data={"message": body.message},
        output_data={"reply": reply},
        commit=True,
    )
    return {"reply": reply, "context": ctx}


@router.get("/logs")
async def automation_logs(
    job_type: str | None = Query(None),
    trigger: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(AiAutomationLog)
        .where(AiAutomationLog.tenant_id == user.tenant_id)
        .order_by(AiAutomationLog.id.desc())
        .limit(limit)
    )
    if job_type:
        stmt = stmt.where(AiAutomationLog.job_type == job_type)
    if trigger:
        stmt = stmt.where(AiAutomationLog.trigger == trigger)
    if status:
        stmt = stmt.where(AiAutomationLog.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    counts_rows = (
        await db.execute(
            select(AiAutomationLog.job_type, func.count(AiAutomationLog.id))
            .where(AiAutomationLog.tenant_id == user.tenant_id)
            .group_by(AiAutomationLog.job_type)
        )
    ).all()
    return {
        "labels": JOB_LABELS,
        "counts": {k: int(v) for k, v in counts_rows},
        "total": sum(int(v) for _, v in counts_rows),
        "items": [
            {
                "id": r.id,
                "job_type": r.job_type,
                "label": JOB_LABELS.get(r.job_type, r.job_type),
                "trigger": r.trigger,
                "actor": r.actor,
                "status": r.status,
                "summary": r.summary,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "model": r.model,
                "tokens_used": r.tokens_used,
                "duration_ms": r.duration_ms,
                "input_json": r.input_json,
                "output_json": r.output_json,
                "error": r.error,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.post("/anomalies")
async def anomalies(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    created = await detect_anomalies(db, user.tenant_id)
    existing = (
        await db.execute(
            select(AnomalyAlert).where(AnomalyAlert.tenant_id == user.tenant_id).order_by(AnomalyAlert.id.desc()).limit(50)
        )
    ).scalars().all()
    return {
        "created": len(created),
        "alerts": [
            {
                "id": a.id,
                "kind": a.kind,
                "severity": a.severity,
                "title": a.title,
                "detail": a.detail,
                "status": a.status,
            }
            for a in existing
        ],
    }


@router.post("/listings/{listing_id}/optimize")
async def optimize(listing_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return await suggest_listing_copy(db, user.tenant_id, listing_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
