"""SQLite repository for dashboard-ready product rows."""

from __future__ import annotations

import os
import sqlite3
from typing import Iterable

from src.core.config import Config
from src.definitions import ROOT_DIR
from src.web.schemas import ProductPriceRow


class ProductRepository:
    """Read normalized product rows without coupling the web layer to scraper internals."""

    _SELECT_PRODUCTS_SQL = """
        SELECT
            product_code,
            product_name,
            product_category,
            marketplace,
            price,
            product_url,
            scraped_at
        FROM products
        ORDER BY scraped_at DESC, product_code ASC, marketplace ASC;
    """

    def __init__(self, db_path: str | None = None, config: Config | None = None) -> None:
        self.config = config or Config()
        self.db_path = db_path or self._resolve_db_path()

    def _resolve_db_path(self) -> str:
        configured_path = self.config.get("paths", "database", default="database/scraper.db")
        if os.path.isabs(configured_path):
            return configured_path
        return os.path.join(ROOT_DIR, configured_path)

    def fetch_product_rows(self) -> list[ProductPriceRow]:
        connection = sqlite3.connect(self.db_path)
        try:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(self._SELECT_PRODUCTS_SQL).fetchall()
        finally:
            connection.close()
        return [self._to_product_price_row(row) for row in rows]

    @staticmethod
    def _to_product_price_row(row: sqlite3.Row) -> ProductPriceRow:
        return ProductPriceRow(
            product_code=row["product_code"],
            product_name=row["product_name"],
            product_category=row["product_category"],
            marketplace=row["marketplace"],
            price=row["price"],
            product_url=row["product_url"],
            scraped_at=row["scraped_at"],
        )

    @staticmethod
    def available_categories(rows: Iterable[ProductPriceRow]) -> list[str]:
        return sorted({row.product_category.strip() for row in rows if row.product_category and row.product_category.strip()})
