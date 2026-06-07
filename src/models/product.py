"""Data transfer objects used between scraping and persistence layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


@dataclass
class ProductDTO:
    """Carry scraped product metadata until it is flattened for database writes."""

    code: str
    url: Optional[str] = None
    brand: str = "Razer"
    title: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    sellers: list[dict[str, str | float]] = field(default_factory=list)

    def to_db_rows(self) -> list[dict[str, Any]]:
        """Return one database row per seller, or one nullable seller row."""
        today = date.today().strftime("%Y-%m-%d")

        base: dict[str, Any] = {
            "brand": self.brand,
            "product_code": self.code,
            "product_category": self.category,
            "product_name": self.title,
            "product_url": self.url,
            "scraped_at": today,
        }

        if not self.sellers:
            row = base.copy()
            row["marketplace"] = None
            row["price"] = self.price if self.price else None
            return [row]

        rows: list[dict[str, Any]] = []
        for seller in self.sellers:
            row = base.copy()
            row["marketplace"] = seller.get("name")
            row["price"] = seller.get("price")
            rows.append(row)

        return rows
