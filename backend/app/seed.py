"""Deterministic demo tenant, catalog, channels, orders, and finance data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import AccountingConnection, MappingRule
from app.models.ai import AiAutomationLog
from app.models.catalog import BundleItem, Listing, ListingTemplate, Product, ProductImage, ProductVariant
from app.models.finance import OrderCost
from app.models.inventory import InventoryBalance, Warehouse
from app.models.marketplace import Channel
from app.models.order import Order, OrderItem, ReturnItem, ReturnRequest
from app.models.tenant import Tenant, User
from app.security import encrypt_secret, hash_password
from app.services.orders import ingest_channel_orders
from app.services.reconciliation import ingest_payouts

NOW = datetime.now(timezone.utc)


async def seed_if_empty(db: AsyncSession) -> None:
    existing = (await db.execute(select(Tenant))).scalar_one_or_none()
    if existing:
        await seed_ai_logs_if_empty(db, existing.id)
        return
    await seed_all(db)


async def seed_ai_logs_if_empty(db: AsyncSession, tenant_id: int) -> None:
    existing = (await db.execute(select(AiAutomationLog.id).limit(1))).scalar_one_or_none()
    if existing:
        return
    await _insert_demo_ai_logs(db, tenant_id)
    await db.commit()


async def _insert_demo_ai_logs(db: AsyncSession, tenant_id: int) -> None:
    samples = [
        ("forecast", "user", "marco.lee@forge.example", "success", "30-day demand forecast for 12 SKU/warehouse rows", "forecast", "", {"horizon_days": 30}, {"rows": 12, "replenish_skus": 4}, 18),
        ("listing_optimize", "user", "marco.lee@forge.example", "success", "Optimized listing #1: Forge Chrono Watch — Black | Official Stock", "listing", "1", {"listing_id": 1}, {"title": "Forge Chrono Watch — Black | Official Stock | Fast Ship"}, 42),
        ("anomaly_scan", "user", "sofia.ng@forge.example", "success", "Anomaly scan raised 4 alert(s)", "anomaly_alert", "", {"open_discrepancies": 13}, {"alerts": 4, "kinds": ["fee_anomaly", "stock_mismatch"]}, 31),
        ("chat", "user", "ava.chen@forge.example", "success", "Chat: What is our margin this period?", "chat", "", {"message": "What is our margin this period?"}, {"reply": "Gross profit this period is 992.1260 (37.5593% margin)."}, 9),
        ("return_categorize", "user", "diego.ruiz@forge.example", "success", "RMA RMA-10001 categorized as listing → update_listing_copy", "return", "1", {"reason_code": "not_as_described"}, {"category": "listing", "resolution": "update_listing_copy"}, 7),
        ("sync_health", "agent", "sync-health-agent", "success", "Background monitor: 6 channels healthy, 1 fee anomaly open", "channel", "", {"channels": 6}, {"healthy": 6, "alerts": 1}, 55),
        ("profit_alert", "agent", "profit-agent", "success", "TikTok Shop margin dropped below 20% on CF-CABLE-USB", "sku", "CF-CABLE-USB", {"threshold": 20}, {"channel": "tiktok", "margin_pct": 18.4}, 12),
        ("order_routing", "agent", "routing-agent", "success", "Routed AMZ-2044 to Singapore Hub (MAIN) based on stock + SLA", "order", "1", {"order": "AMZ-2044"}, {"warehouse": "MAIN", "reason": "highest_available"}, 6),
        ("forecast", "agent", "forecast-agent", "success", "Nightly replenishment: suggested PO for 3 SKUs", "forecast", "", {"schedule": "nightly"}, {"suggested_replenish": 3}, 22),
        ("listing_optimize", "user", "ava.chen@forge.example", "failed", "Listing optimization failed: listing not found", "listing", "999", {"listing_id": 999}, {}, 3),
    ]
    for i, (job, trigger, actor, status, summary, etype, eid, inp, out, ms) in enumerate(samples):
        db.add(
            AiAutomationLog(
                tenant_id=tenant_id,
                job_type=job,
                trigger=trigger,
                actor=actor,
                status=status,
                summary=summary,
                entity_type=etype,
                entity_id=eid,
                model="heuristic",
                tokens_used=0,
                duration_ms=ms,
                input_json=json.dumps(inp),
                output_json=json.dumps(out),
                error="Listing not found" if status == "failed" else None,
                created_at=NOW - timedelta(hours=len(samples) - i),
            )
        )


async def seed_all(db: AsyncSession) -> Tenant:
    tenant = Tenant(name="Forge Commerce Co.", slug="forge", timezone="Asia/Singapore", currency="USD")
    db.add(tenant)
    await db.flush()

    users = [
        ("ava.chen@forge.example", "Ava Chen", "admin", "admin123"),
        ("marco.lee@forge.example", "Marco Lee", "manager", "manager123"),
        ("sofia.ng@forge.example", "Sofia Ng", "accountant", "account123"),
        ("diego.ruiz@forge.example", "Diego Ruiz", "warehouse", "warehouse123"),
        ("viewer@forge.example", "Riley Park", "viewer", "viewer123"),
    ]
    for email, name, role, pw in users:
        db.add(
            User(
                tenant_id=tenant.id,
                email=email,
                full_name=name,
                hashed_password=hash_password(pw),
                role=role,
            )
        )

    warehouses = [
        Warehouse(tenant_id=tenant.id, code="MAIN", name="Singapore Hub", country="SG", is_default=True),
        Warehouse(tenant_id=tenant.id, code="USW", name="Los Angeles West", country="US"),
        Warehouse(tenant_id=tenant.id, code="EU1", name="Amsterdam FC", country="NL"),
    ]
    for w in warehouses:
        db.add(w)
    await db.flush()
    wh_main = warehouses[0]
    wh_us = warehouses[1]

    catalog = [
        {
            "sku": "CF-WATCH-BLK",
            "title": "Forge Chrono Watch — Black",
            "desc": "Sapphire crystal chronograph with 10ATM water resistance.",
            "brand": "Forge",
            "category": "Watches",
            "cogs": "72.00",
            "price": "189.00",
            "type": "variable",
            "options": [("Black", "CF-WATCH-BLK"), ("Silver", "CF-WATCH-SLV")],
        },
        {
            "sku": "CF-STRAP-22",
            "title": "Leather Strap 22mm",
            "desc": "Full-grain leather strap, quick-release spring bars.",
            "brand": "Forge",
            "category": "Accessories",
            "cogs": "6.40",
            "price": "29.00",
            "type": "simple",
            "options": [("Default", "CF-STRAP-22")],
        },
        {
            "sku": "CF-CABLE-USB",
            "title": "USB-C Fast Cable 1.2m",
            "desc": "60W braided USB-C cable.",
            "brand": "Forge",
            "category": "Electronics",
            "cogs": "1.80",
            "price": "9.90",
            "type": "simple",
            "options": [("Default", "CF-CABLE-USB")],
        },
        {
            "sku": "CF-CASE-AIR",
            "title": "AirCase Protective Sleeve",
            "desc": "Shock-absorbing TPU sleeve.",
            "brand": "Forge",
            "category": "Accessories",
            "cogs": "3.10",
            "price": "14.50",
            "type": "simple",
            "options": [("Default", "CF-CASE-AIR")],
        },
        {
            "sku": "CF-BUNDLE-SET",
            "title": "Watch + Strap Bundle",
            "desc": "Chrono watch with extra leather strap.",
            "brand": "Forge",
            "category": "Bundles",
            "cogs": "78.40",
            "price": "209.00",
            "type": "bundle",
            "options": [("Default", "CF-BUNDLE-SET")],
        },
    ]

    variants_by_sku: dict[str, ProductVariant] = {}
    products_by_sku: dict[str, Product] = {}
    for row in catalog:
        p = Product(
            tenant_id=tenant.id,
            sku=row["sku"],
            title=row["title"],
            description=row["desc"],
            brand=row["brand"],
            category=row["category"],
            product_type=row["type"],
            cogs=Decimal(row["cogs"]),
            status="active",
            weight_g=180,
        )
        db.add(p)
        await db.flush()
        products_by_sku[row["sku"]] = p
        db.add(ProductImage(product_id=p.id, url=f"/images/{row['sku'].lower()}.svg", alt=row["title"], is_primary=True))
        for opt, sku in row["options"]:
            if sku in variants_by_sku:
                continue
            cogs = Decimal("75.00") if sku == "CF-WATCH-SLV" else Decimal(row["cogs"])
            price = Decimal("199.00") if sku == "CF-WATCH-SLV" else Decimal(row["price"])
            v = ProductVariant(
                product_id=p.id,
                sku=sku,
                title=f"{row['title']} / {opt}" if opt != "Default" else row["title"],
                option1=opt,
                cogs=cogs,
                price=price,
            )
            db.add(v)
            await db.flush()
            variants_by_sku[sku] = v

    silver = Product(
        tenant_id=tenant.id,
        sku="CF-WATCH-SLV-P",
        title="Forge Chrono Watch — Silver",
        description="Silver-case sibling of the Chrono line.",
        brand="Forge",
        category="Watches",
        product_type="simple",
        cogs=Decimal("75.00"),
        status="active",
    )
    if "CF-WATCH-SLV" not in variants_by_sku:
        db.add(silver)
        await db.flush()
        v = ProductVariant(
            product_id=silver.id,
            sku="CF-WATCH-SLV",
            title=silver.title,
            option1="Silver",
            cogs=Decimal("75.00"),
            price=Decimal("199.00"),
        )
        db.add(v)
        await db.flush()
        variants_by_sku["CF-WATCH-SLV"] = v
        products_by_sku["CF-WATCH-SLV"] = silver

    if "CF-WATCH-BLK" in variants_by_sku and "CF-STRAP-22" in variants_by_sku:
        db.add(BundleItem(parent_product_id=products_by_sku["CF-BUNDLE-SET"].id, child_variant_id=variants_by_sku["CF-WATCH-BLK"].id, quantity=1))
        db.add(BundleItem(parent_product_id=products_by_sku["CF-BUNDLE-SET"].id, child_variant_id=variants_by_sku["CF-STRAP-22"].id, quantity=1))

    stock = {
        "CF-WATCH-BLK": (48, 8, 12),
        "CF-WATCH-SLV": (36, 6, 10),
        "CF-STRAP-22": (160, 20, 40),
        "CF-CABLE-USB": (400, 30, 80),
        "CF-CASE-AIR": (90, 10, 24),
        "CF-BUNDLE-SET": (12, 2, 6),
    }
    for sku, (main, us, safety) in stock.items():
        v = variants_by_sku[sku]
        db.add(InventoryBalance(tenant_id=tenant.id, variant_id=v.id, warehouse_id=wh_main.id, on_hand=main, reserved=2, inbound=10, safety_stock=safety))
        db.add(InventoryBalance(tenant_id=tenant.id, variant_id=v.id, warehouse_id=wh_us.id, on_hand=us, reserved=0, inbound=0, safety_stock=max(safety // 3, 2)))

    markets = [
        ("amazon-us", "Amazon US", "amazon", "US", 30),
        ("shopee-sg", "Shopee Singapore", "shopee", "SG", 80),
        ("lazada-my", "Lazada Malaysia", "lazada", "MY", 60),
        ("tiktok-us", "TikTok Shop US", "tiktok", "US", 100),
        ("shopify-dtc", "Shopify DTC", "shopify", "US", 120),
        ("ebay-us", "eBay US", "ebay", "US", 40),
    ]
    channels: list[Channel] = []
    for code, name, mp, region, rpm in markets:
        ch = Channel(
            tenant_id=tenant.id,
            code=code,
            name=name,
            marketplace=mp,
            region=region,
            status="connected",
            rate_limit_rpm=rpm,
            last_synced_at=NOW - timedelta(minutes=12),
        )
        db.add(ch)
        channels.append(ch)
    await db.flush()

    tpl = ListingTemplate(
        tenant_id=tenant.id,
        name="Global Premium",
        marketplace="amazon",
        title_pattern="{title} | Official",
        price_rule="markup_pct",
        price_modifier=Decimal("0"),
        attribute_map_json=json.dumps({"brand": "brand", "color": "option1"}),
    )
    db.add(tpl)
    await db.flush()

    sku_product = {sku: v.product_id for sku, v in variants_by_sku.items()}
    listing_plan = [
        ("amazon-us", "CF-WATCH-BLK", "active", "189.00"),
        ("amazon-us", "CF-WATCH-SLV", "active", "199.00"),
        ("amazon-us", "CF-STRAP-22", "active", "29.00"),
        ("shopee-sg", "CF-WATCH-BLK", "active", "189.00"),
        ("shopee-sg", "CF-CABLE-USB", "active", "9.90"),
        ("lazada-my", "CF-WATCH-SLV", "paused", "199.00"),
        ("lazada-my", "CF-CASE-AIR", "active", "14.50"),
        ("tiktok-us", "CF-CABLE-USB", "active", "8.90"),
        ("tiktok-us", "CF-STRAP-22", "active", "24.90"),
        ("shopify-dtc", "CF-WATCH-BLK", "active", "189.00"),
        ("shopify-dtc", "CF-WATCH-SLV", "active", "199.00"),
        ("shopify-dtc", "CF-BUNDLE-SET", "draft", "209.00"),
        ("ebay-us", "CF-CASE-AIR", "active", "13.99"),
        ("ebay-us", "CF-STRAP-22", "out-of-stock", "27.50"),
    ]
    ch_by_code = {c.code: c for c in channels}
    for ch_code, sku, status, price in listing_plan:
        ch = ch_by_code[ch_code]
        v = variants_by_sku[sku]
        db.add(
            Listing(
                tenant_id=tenant.id,
                product_id=v.product_id,
                variant_id=v.id,
                channel_id=ch.id,
                template_id=tpl.id,
                external_id=f"{ch.marketplace}-{sku}",
                title=v.title,
                description=products_by_sku.get(sku, products_by_sku.get("CF-WATCH-BLK")).description
                if sku in products_by_sku or True
                else "",
                price=Decimal(price),
                status=status,
                quantity_pushed=stock.get(sku, (0, 0, 0))[0],
                category_external="Watches" if "WATCH" in sku else "Accessories",
            )
        )

    conn = AccountingConnection(
        tenant_id=tenant.id,
        provider="xero",
        name="Xero — Forge Commerce",
        status="connected",
        encrypted_credentials=encrypt_secret("demo-xero-token"),
        chart_of_accounts_json=json.dumps(
            [
                {"code": "4000", "name": "Marketplace Sales", "type": "income"},
                {"code": "5000", "name": "COGS", "type": "cogs"},
                {"code": "6100", "name": "Marketplace Fees", "type": "expense"},
                {"code": "6200", "name": "Shipping Expense", "type": "expense"},
                {"code": "6300", "name": "Advertising", "type": "expense"},
                {"code": "1100", "name": "Undeposited Funds", "type": "asset"},
            ]
        ),
        last_synced_at=NOW - timedelta(hours=6),
    )
    db.add(conn)
    await db.flush()
    for src, acct, name in (
        ("sale", "4000", "Marketplace Sales"),
        ("cogs", "5000", "COGS"),
        ("marketplace_fee", "6100", "Marketplace Fees"),
        ("shipping_cost", "6200", "Shipping Expense"),
        ("ads", "6300", "Advertising"),
    ):
        db.add(
            MappingRule(
                tenant_id=tenant.id,
                connection_id=conn.id,
                source_type="order_cost" if src != "sale" else "order",
                source_code=src,
                target_account=acct,
                target_account_name=name,
            )
        )

    extra_order = Order(
        tenant_id=tenant.id,
        channel_id=ch_by_code["amazon-us"].id,
        warehouse_id=wh_main.id,
        external_id="amz-manual-1",
        order_number="AMZ-2044",
        status="shipped",
        fulfillment_status="fulfilled",
        financial_status="paid",
        currency="USD",
        subtotal=Decimal("189.00"),
        shipping_charged=Decimal("4.99"),
        tax=Decimal("15.12"),
        total=Decimal("209.11"),
        customer_name="Jordan Hale",
        customer_email="jordan@example.com",
        shipping_country="US",
        placed_at=NOW - timedelta(days=3),
    )
    db.add(extra_order)
    await db.flush()
    db.add(
        OrderItem(
            order_id=extra_order.id,
            variant_id=variants_by_sku["CF-WATCH-BLK"].id,
            sku="CF-WATCH-BLK",
            title="Forge Chrono Watch — Black",
            quantity=1,
            unit_price=Decimal("189.00"),
            cogs_at_sale=Decimal("72.00"),
            marketplace_fee=Decimal("28.35"),
        )
    )
    db.add(OrderCost(tenant_id=tenant.id, order_id=extra_order.id, cost_type="marketplace_fee", amount=Decimal("28.35"), source="amazon"))
    db.add(OrderCost(tenant_id=tenant.id, order_id=extra_order.id, cost_type="shipping_cost", amount=Decimal("6.40"), source="ups"))
    db.add(OrderCost(tenant_id=tenant.id, order_id=extra_order.id, cost_type="ads", amount=Decimal("12.00"), source="amazon_ads"))

    rr = ReturnRequest(
        tenant_id=tenant.id,
        order_id=extra_order.id,
        channel_id=extra_order.channel_id,
        rma_number="RMA-10001",
        status="requested",
        reason_code="not_as_described",
        reason_text="Color looks darker than the listing photos",
        ai_category="listing",
        suggested_resolution="update_listing_copy",
        refund_amount=Decimal("189.00"),
    )
    db.add(rr)
    await db.flush()
    db.add(ReturnItem(return_id=rr.id, sku="CF-WATCH-BLK", quantity=1, condition="opened"))
    await _insert_demo_ai_logs(db, tenant.id)

    await db.commit()

    for ch in channels:
        await ingest_channel_orders(db, ch)
        await ingest_payouts(db, ch)

    return tenant
