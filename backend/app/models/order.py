"""Orders, line items, and RMA / return workflow."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    order_number: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    fulfillment_status: Mapped[str] = mapped_column(String(32), default="unfulfilled")
    financial_status: Mapped[str] = mapped_column(String(32), default="paid")
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    shipping_charged: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    customer_name: Mapped[str] = mapped_column(String(200), default="")
    customer_email: Mapped[str] = mapped_column(String(255), default="")
    shipping_country: Mapped[str] = mapped_column(String(8), default="")
    placed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text, default="{}")

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    costs: Mapped[list["OrderCost"]] = relationship(back_populates="order")  # noqa: F821
    returns: Mapped[list["ReturnRequest"]] = relationship(back_populates="order")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(400))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    cogs_at_sale: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    marketplace_fee: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))

    order: Mapped[Order] = relationship(back_populates="items")


class ReturnRequest(Base, TimestampMixin):
    __tablename__ = "return_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    rma_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="requested", index=True)
    reason_code: Mapped[str] = mapped_column(String(64), default="other")
    reason_text: Mapped[str] = mapped_column(Text, default="")
    ai_category: Mapped[str] = mapped_column(String(64), default="")
    suggested_resolution: Mapped[str] = mapped_column(String(80), default="")
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    restock: Mapped[bool] = mapped_column(default=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped[Order] = relationship(back_populates="returns")
    items: Mapped[list["ReturnItem"]] = relationship(back_populates="return_request")


class ReturnItem(Base, TimestampMixin):
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("return_requests.id"), index=True)
    order_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("order_items.id"), nullable=True)
    sku: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    condition: Mapped[str] = mapped_column(String(32), default="unopened")

    return_request: Mapped[ReturnRequest] = relationship(back_populates="items")
