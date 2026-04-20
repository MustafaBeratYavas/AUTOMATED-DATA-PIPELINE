# -- Product Data Transfer Object --
# Immutable domain model carrying scraped product metadata through the pipeline.
# The to_db_rows() method flattens the nested seller list into database-ready dicts,
# handling both single-seller and multi-seller scenarios for batch INSERT operations.

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Any

@dataclass
class ProductDTO:
    
    code: str
    url: Optional[str] = None
    brand: str = "Razer"
    title: Optional[str] = None
    category: Optional[str] = None
    price: float = 0.0
    sellers: list[dict[str, str | float]] = field(default_factory=list)

    def to_db_rows(self) -> list[dict[str, Any]]:
        # Flatten DTO into a list of normalised row dicts for SQLite insertion
        today = date.today().strftime("%Y-%m-%d")

        # Base record shared across all seller rows for this product
        base: dict[str, Any] = {
            "brand": self.brand,
            "product_code": self.code,
            "product_category": self.category,
            "product_name": self.title,
            "product_url": self.url,
            "scraped_at": today,
        }

        # When no sellers were extracted, persist a single row with nullable fields
        if not self.sellers:
            row = base.copy()
            row["marketplace"] = None
            row["price"] = self.price if self.price else None
            return [row]

        # Expand each seller into its own database row
        rows: list[dict[str, Any]] = []
        for seller in self.sellers:
            row = base.copy()
            row["marketplace"] = seller.get("name")
            row["price"] = seller.get("price")
            rows.append(row)

        return rows
