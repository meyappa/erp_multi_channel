"""Marketplace channels, encrypted credentials, and webhook inbox."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120))
    marketplace: Mapped[str] = mapped_column(String(40), index=True)
    region: Mapped[str] = mapped_column(String(16), default="US")
    status: Mapped[str] = mapped_column(String(24), default="connected")
    sync_mode: Mapped[str] = mapped_column(String(24), default="webhook_plus_poll")
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="channels")  # noqa: F821
    credentials: Mapped[list["ChannelCredential"]] = relationship(back_populates="channel")
    listings: Mapped[list["Listing"]] = relationship(back_populates="channel")  # noqa: F821


class ChannelCredential(Base, TimestampMixin):
    __tablename__ = "channel_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    key_name: Mapped[str] = mapped_column(String(80))
    encrypted_value: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    channel: Mapped[Channel] = relationship(back_populates="credentials")


class WebhookInbox(Base, TimestampMixin):
    __tablename__ = "webhook_inbox"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    channel_id: Mapped[Optional[int]] = mapped_column(ForeignKey("channels.id"), nullable=True)
    marketplace: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(String(255), default="")
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
