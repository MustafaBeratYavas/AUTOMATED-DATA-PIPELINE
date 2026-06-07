"""Unit tests for dashboard product repository."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.services.database import DatabaseService
from src.web.repositories.product_repository import ProductRepository


class TestProductRepository(unittest.TestCase):
    """Validate dashboard reads from an isolated SQLite database."""

    def test_fetch_product_rows_returns_typed_records(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dashboard.db"
            self._create_products_database(db_path)

            service = ProductRepository(db_path=str(db_path))
            rows = service.fetch_product_rows()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].product_code, "P1")
        self.assertEqual(rows[0].marketplace, "Amazon Türkiye")
        self.assertEqual(rows[0].price, 120.0)

    def test_available_categories_returns_sorted_non_empty_values(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "dashboard.db"
            self._create_products_database(db_path)

            service = ProductRepository(db_path=str(db_path))
            rows = service.fetch_product_rows()

        self.assertEqual(service.available_categories(rows), ["Kulaklık", "Mouse"])

    def _create_products_database(self, db_path: Path) -> None:
        """Create a small products table fixture."""
        connection = sqlite3.connect(db_path)
        try:
            connection.execute(DatabaseService._CREATE_TABLE_SQL)
            connection.executemany(
                """
                INSERT INTO products
                    (brand, product_code, product_category, product_name,
                     marketplace, price, product_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("Razer", "P1", "Mouse", "P1 Product", "Amazon Türkiye", 120.0, "https://a.test/p1", "2026-06-06"),
                    ("Razer", "P2", "Kulaklık", "P2 Product", "Trendyol", 200.0, "https://a.test/p2", "2026-06-06"),
                ],
            )
            connection.commit()
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
