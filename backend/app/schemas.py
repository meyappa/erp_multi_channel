"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    tenant: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    tenant_id: int

    model_config = {"from_attributes": True}


class ProductIn(BaseModel):
    sku: str
    title: str
    description: str = ""
    brand: str = ""
    category: str = ""
    product_type: str = "simple"
    cogs: Decimal = Decimal("0")
    status: str = "active"


class VariantIn(BaseModel):
    sku: str
    title: str
    option1: str = ""
    option2: str = ""
    cogs: Decimal = Decimal("0")
    price: Decimal = Decimal("0")


class ListingPushIn(BaseModel):
    product_id: int
    channel_ids: list[int]
    template_id: Optional[int] = None
    price: Optional[Decimal] = None


class InventoryAdjustIn(BaseModel):
    variant_id: int
    warehouse_id: int
    quantity_delta: int
    reason: str = "adjustment"
    note: str = ""


class ReturnCreateIn(BaseModel):
    order_id: int
    reason_code: str = "other"
    reason_text: str = ""
    refund_amount: Decimal = Decimal("0")
    items: list[dict[str, Any]] = Field(default_factory=list)


class ReturnDecideIn(BaseModel):
    action: str
    restock: bool = False


class ChatIn(BaseModel):
    message: str


class BulkListingStatusIn(BaseModel):
    listing_ids: list[int]
    status: str


class MappingRuleIn(BaseModel):
    connection_id: int
    source_type: str
    source_code: str
    target_account: str
    target_account_name: str = ""
