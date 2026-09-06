"""SQLAlchemy models for ChannelForge ERP."""

from app.models.accounting import AccountingConnection, JournalEntry, MappingRule
from app.models.ai import AiAutomationLog, AiJob, AnomalyAlert, Forecast, ListingSuggestion
from app.models.catalog import (
    BundleItem,
    CategoryMapping,
    Listing,
    ListingTemplate,
    Product,
    ProductImage,
    ProductVariant,
)
from app.models.finance import (
    Discrepancy,
    GrossProfitSnapshot,
    OrderCost,
    Payout,
    PayoutMatch,
)
from app.models.inventory import (
    InventoryBalance,
    InventoryMovement,
    SyncEvent,
    Warehouse,
)
from app.models.marketplace import Channel, ChannelCredential, WebhookInbox
from app.models.order import Order, OrderItem, ReturnItem, ReturnRequest
from app.models.tenant import AuditLog, Role, Tenant, User

__all__ = [
    "AccountingConnection",
    "AiAutomationLog",
    "AiJob",
    "AnomalyAlert",
    "AuditLog",
    "BundleItem",
    "CategoryMapping",
    "Channel",
    "ChannelCredential",
    "Discrepancy",
    "Forecast",
    "GrossProfitSnapshot",
    "InventoryBalance",
    "InventoryMovement",
    "JournalEntry",
    "Listing",
    "ListingSuggestion",
    "ListingTemplate",
    "MappingRule",
    "Order",
    "OrderCost",
    "OrderItem",
    "Payout",
    "PayoutMatch",
    "Product",
    "ProductImage",
    "ProductVariant",
    "ReturnItem",
    "ReturnRequest",
    "Role",
    "SyncEvent",
    "Tenant",
    "User",
    "Warehouse",
    "WebhookInbox",
]
