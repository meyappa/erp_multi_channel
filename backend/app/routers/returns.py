from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.order import ReturnRequest
from app.models.tenant import User
from app.schemas import ReturnCreateIn, ReturnDecideIn
from app.services.returns import create_return, decide_return

router = APIRouter(prefix="/api/returns", tags=["returns"])


@router.get("")
async def list_returns(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(
            select(ReturnRequest)
            .options(selectinload(ReturnRequest.items), selectinload(ReturnRequest.order))
            .where(ReturnRequest.tenant_id == user.tenant_id)
            .order_by(ReturnRequest.id.desc())
        )
    ).scalars().unique().all()
    return [
        {
            "id": r.id,
            "rma_number": r.rma_number,
            "status": r.status,
            "reason_code": r.reason_code,
            "reason_text": r.reason_text,
            "ai_category": r.ai_category,
            "suggested_resolution": r.suggested_resolution,
            "refund_amount": str(r.refund_amount),
            "restock": r.restock,
            "order_number": r.order.order_number if r.order else "",
            "items": [{"sku": i.sku, "quantity": i.quantity, "condition": i.condition} for i in r.items],
        }
        for r in rows
    ]


@router.post("")
async def open_return(
    body: ReturnCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    try:
        rr = await create_return(
            db,
            tenant_id=user.tenant_id,
            order_id=body.order_id,
            reason_code=body.reason_code,
            reason_text=body.reason_text,
            items=body.items,
            refund_amount=body.refund_amount,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"id": rr.id, "rma_number": rr.rma_number, "ai_category": rr.ai_category}


@router.post("/{return_id}/decide")
async def decide(
    return_id: int,
    body: ReturnDecideIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager", "warehouse")),
):
    try:
        rr = await decide_return(db, user.tenant_id, return_id, body.action, body.restock)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"id": rr.id, "status": rr.status, "restock": rr.restock}
