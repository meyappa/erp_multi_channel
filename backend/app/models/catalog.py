"""Central catalog, variants, listings, templates, and images."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    brand: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(200), default="")
    product_type: Mapped[str] = mapped_column(String(32), default="simple")
    status: Mapped[str] = mapped_column(String(24), default="active")
    cogs: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    weight_g: Mapped[int] = mapped_column(Integer, default=0)
    hs_code: Mapped[str] = mapped_column(String(32), default="")
    compliance_json: Mapped[str] = mapped_column(Text, default="{}")

    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product")
    listings: Mapped[list["Listing"]] = relationship(back_populates="product")
    bundle_items: Mapped[list["BundleItem"]] = relationship(
        back_populates="parent",
        foreign_keys="BundleItem.parent_product_id",
    )


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(300))
    option1: Mapped[str] = mapped_column(String(80), default="")
    option2: Mapped[str] = mapped_column(String(80), default="")
    option3: Mapped[str] = mapped_column(String(80), default="")
    barcode: Mapped[str] = mapped_column(String(64), default="")
    cogs: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped[Product] = relationship(back_populates="variants")
    balances: Mapped[list["InventoryBalance"]] = relationship(back_populates="variant")  # noqa: F821


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    alt: Mapped[str] = mapped_column(String(255), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    product: Mapped[Product] = relationship(back_populates="images")


class BundleItem(Base, TimestampMixin):
    __tablename__ = "bundle_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    child_variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    parent: Mapped[Product] = relationship(back_populates="bundle_items", foreign_keys=[parent_product_id])


class ListingTemplate(Base, TimestampMixin):
    __tablename__ = "listing_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    marketplace: Mapped[str] = mapped_column(String(40), index=True)
    title_pattern: Mapped[str] = mapped_column(String(500), default="{title}")
    description_pattern: Mapped[str] = mapped_column(Text, default="{description}")
    price_rule: Mapped[str] = mapped_column(String(80), default="base")
    price_modifier: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    attribute_map_json: Mapped[str] = mapped_column(Text, default="{}")


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    variant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)
    template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("listing_templates.id"), nullable=True)
    external_id: Mapped[str] = mapped_column(String(120), default="", index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    promo_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    quantity_pushed: Mapped[int] = mapped_column(Integer, default=0)
    category_external: Mapped[str] = mapped_column(String(200), default="")
    attributes_json: Mapped[str] = mapped_column(Text, default="{}")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    product: Mapped[Product] = relationship(back_populates="listings")
    channel: Mapped["Channel"] = relationship(back_populates="listings")  # noqa: F821


class CategoryMapping(Base, TimestampMixin):
    __tablename__ = "category_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    internal_category: Mapped[str] = mapped_column(String(200), index=True)
    marketplace: Mapped[str] = mapped_column(String(40), index=True)
    external_category_id: Mapped[str] = mapped_column(String(120))
    external_category_name: Mapped[str] = mapped_column(String(300), default="")
