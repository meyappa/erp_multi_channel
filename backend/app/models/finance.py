"""Payouts, reconciliation, order-level costs, and profit snapshots."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class OrderCost(Base, TimestampMixin):
    """Every money line that affects gross profit. Must be auditable."""

    __tablename__ = "order_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    cost_type: Mapped[str] = mapped_column(String(40), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    source: Mapped[str] = mapped_column(String(40), default="system")
    note: Mapped[str] = mapped_column(Text, default="")

    order: Mapped["Order"] = relationship(back_populates="costs")  # noqa: F821


class Payout(Base, TimestampMixin):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    fee_total: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    raw_payload: Mapped[str] = mapped_column(Text, default="{}")

    matches: Mapped[list["PayoutMatch"]] = relationship(back_populates="payout")


class PayoutMatch(Base, TimestampMixin):
    __tablename__ = "payout_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    payout_id: Mapped[int] = mapped_column(ForeignKey("payouts.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    matched_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    match_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("1"))
    method: Mapped[str] = mapped_column(String(32), default="auto")

    payout: Mapped[Payout] = relationship(back_populates="matches")


class Discrepancy(Base, TimestampMixin):
    __tablename__ = "discrepancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("channels.id"), nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    payout_id: Mapped[Optional[int]] = mapped_column(ForeignKey("payouts.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    description: Mapped[str] = mapped_column(Text, default="")
    suggested_action: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)


class GrossProfitSnapshot(Base, TimestampMixin):
    """Immutable snapshot of a profit calculation for auditability."""

    __tablename__ = "gross_profit_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), default="", index=True)
    channel_code: Mapped[str] = mapped_column(String(40), default="")
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    cogs: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    marketplace_fees: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    returns_refunds: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    ads: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    formula: Mapped[str] = mapped_column(Text, default="")
    period: Mapped[str] = mapped_column(String(16), default="")
