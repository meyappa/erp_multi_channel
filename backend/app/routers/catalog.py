import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters import registry
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.catalog import Listing, ListingTemplate, Product, ProductVariant
from app.models.marketplace import Channel
from app.models.tenant import User
from app.schemas import BulkListingStatusIn, ListingPushIn, ProductIn, VariantIn

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/products")
async def list_products(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Product)
        .options(selectinload(Product.variants), selectinload(Product.images), selectinload(Product.listings))
        .where(Product.tenant_id == user.tenant_id)
        .order_by(Product.id)
    )
    products = (await db.execute(stmt)).scalars().unique().all()
    out = []
    for p in products:
        if q and q.lower() not in (p.sku + p.title).lower():
            continue
        out.append(
            {
                "id": p.id,
                "sku": p.sku,
                "title": p.title,
                "description": p.description,
                "brand": p.brand,
                "category": p.category,
                "product_type": p.product_type,
                "status": p.status,
                "cogs": str(p.cogs),
                "variants": [
                    {
                        "id": v.id,
                        "sku": v.sku,
                        "title": v.title,
                        "option1": v.option1,
                        "cogs": str(v.cogs),
                        "price": str(v.price),
                    }
                    for v in p.variants
                ],
                "listings_count": len(p.listings),
            }
        )
    return out


@router.post("/products")
async def create_product(
    body: ProductIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    p = Product(tenant_id=user.tenant_id, **body.model_dump())
    db.add(p)
    await db.flush()
    v = ProductVariant(product_id=p.id, sku=p.sku, title=p.title, cogs=p.cogs, price=Decimal("0"))
    db.add(v)
    await db.commit()
    return {"id": p.id, "sku": p.sku}


@router.post("/products/{product_id}/variants")
async def add_variant(
    product_id: int,
    body: VariantIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    p = await db.get(Product, product_id)
    if not p or p.tenant_id != user.tenant_id:
        raise HTTPException(404, "Product not found")
    v = ProductVariant(product_id=p.id, **body.model_dump())
    db.add(v)
    await db.commit()
    return {"id": v.id}


@router.get("/listings")
async def list_listings(
    status: str | None = Query(None),
    channel_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(Listing)
        .options(selectinload(Listing.channel), selectinload(Listing.product))
        .where(Listing.tenant_id == user.tenant_id)
        .order_by(Listing.id.desc())
    )
    if status:
        stmt = stmt.where(Listing.status == status)
    if channel_id:
        stmt = stmt.where(Listing.channel_id == channel_id)
    rows = (await db.execute(stmt)).scalars().unique().all()
    return [
        {
            "id": l.id,
            "title": l.title,
            "sku": l.product.sku if l.product else "",
            "channel": l.channel.name if l.channel else "",
            "marketplace": l.channel.marketplace if l.channel else "",
            "price": str(l.price),
            "promo_price": str(l.promo_price) if l.promo_price is not None else None,
            "status": l.status,
            "quantity_pushed": l.quantity_pushed,
            "external_id": l.external_id,
            "category_external": l.category_external,
        }
        for l in rows
    ]


@router.post("/listings/push")
async def push_listings(
    body: ListingPushIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    product = await db.get(Product, body.product_id)
    if not product or product.tenant_id != user.tenant_id:
        raise HTTPException(404, "Product not found")
    created = []
    for cid in body.channel_ids:
        ch = await db.get(Channel, cid)
        if not ch or ch.tenant_id != user.tenant_id:
            continue
        adapter = registry.get(ch.marketplace)
        price = body.price if body.price is not None else Decimal("0")
        result = await adapter.push_listing({}, {"sku": product.sku, "title": product.title, "price": str(price)})
        listing = Listing(
            tenant_id=user.tenant_id,
            product_id=product.id,
            channel_id=ch.id,
            template_id=body.template_id,
            external_id=result.external_id,
            title=product.title,
            description=product.description,
            price=price,
            status="active" if result.ok else "draft",
            last_error=None if result.ok else result.message,
        )
        db.add(listing)
        created.append({"channel": ch.code, "ok": result.ok, "external_id": result.external_id})
    await db.commit()
    return {"created": created}


@router.post("/listings/bulk-status")
async def bulk_status(
    body: BulkListingStatusIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "manager")),
):
    updated = 0
    for lid in body.listing_ids:
        listing = await db.get(Listing, lid)
        if listing and listing.tenant_id == user.tenant_id:
            listing.status = body.status
            updated += 1
    await db.commit()
    return {"updated": updated}


@router.get("/templates")
async def templates(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        await db.execute(select(ListingTemplate).where(ListingTemplate.tenant_id == user.tenant_id))
    ).scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "marketplace": t.marketplace,
            "title_pattern": t.title_pattern,
            "price_rule": t.price_rule,
        }
        for t in rows
    ]
