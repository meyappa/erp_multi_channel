"""Accounting system connections, mapping rules, and journal entries."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class AccountingConnection(Base, TimestampMixin):
    __tablename__ = "accounting_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), default="connected")
    encrypted_credentials: Mapped[str] = mapped_column(Text, default="")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    chart_of_accounts_json: Mapped[str] = mapped_column(Text, default="[]")


class MappingRule(Base, TimestampMixin):
    __tablename__ = "mapping_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("accounting_connections.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40))
    source_code: Mapped[str] = mapped_column(String(80))
    target_account: Mapped[str] = mapped_column(String(80))
    target_account_name: Mapped[str] = mapped_column(String(200), default="")
    tax_code: Mapped[str] = mapped_column(String(40), default="")


class JournalEntry(Base, TimestampMixin):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("accounting_connections.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(120), default="")
    entry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    memo: Mapped[str] = mapped_column(String(400), default="")
    debit_account: Mapped[str] = mapped_column(String(80))
    credit_account: Mapped[str] = mapped_column(String(80))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    source_type: Mapped[str] = mapped_column(String(40), default="")
    source_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(24), default="draft")
