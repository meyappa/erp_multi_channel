"""Marketplace adapter plugin registry."""

from app.adapters.base import MarketplaceAdapter, AdapterRegistry
from app.adapters.amazon import AmazonAdapter
from app.adapters.shopee import ShopeeAdapter
from app.adapters.lazada import LazadaAdapter
from app.adapters.tiktok import TikTokShopAdapter
from app.adapters.shopify import ShopifyAdapter
from app.adapters.ebay import EbayAdapter

registry = AdapterRegistry()
registry.register(AmazonAdapter())
registry.register(ShopeeAdapter())
registry.register(LazadaAdapter())
registry.register(TikTokShopAdapter())
registry.register(ShopifyAdapter())
registry.register(EbayAdapter())

__all__ = ["MarketplaceAdapter", "AdapterRegistry", "registry"]
