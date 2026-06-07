"""Typed records used by the local dashboard services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProductPriceRow:
    """One normalized priced marketplace listing from the products table."""

    product_code: str
    product_name: Optional[str]
    product_category: Optional[str]
    marketplace: Optional[str]
    price: Optional[float]
    product_url: Optional[str]
    scraped_at: str
