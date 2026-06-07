"""Unit tests for SQLite persistence and target queue state transitions."""

import unittest
import sqlite3
from unittest.mock import patch
from src.services.database import DatabaseService

class TestDatabaseService(unittest.TestCase):
    """Validate DatabaseService using an isolated in-memory SQLite database."""

    def setUp(self):
        """Create a singleton database instance backed by in-memory SQLite."""
        DatabaseService.reset_instance()

        self.config_patcher = patch("src.services.database.Config")
        self.logger_patcher = patch("src.services.database.Logger")
        self.mock_config = self.config_patcher.start()
        self.mock_logger = self.logger_patcher.start()

        self.mock_config.return_value.get.return_value = ":memory:"

        with patch.object(DatabaseService, "_connect"):
            self.db = DatabaseService()

        self.db._connection = sqlite3.connect(":memory:")
        self.db._connection.execute("PRAGMA journal_mode=WAL;")
        self.db._connection.execute("PRAGMA foreign_keys=ON;")
        self.db._initialize_schema()
        self.db._connection.commit()

    def tearDown(self):
        """Close the database and reset singleton state after each test."""
        if self.db._connection:
            self.db._connection.close()
        DatabaseService.reset_instance()
        self.config_patcher.stop()
        self.logger_patcher.stop()

    def _sample_row(self, **overrides):
        """Return a database row fixture with optional field overrides."""
        row = {
            "brand": "Razer",
            "product_code": "RZ01-001",
            "product_category": "Kulaklık",
            "product_name": "Razer Barracuda X",
            "marketplace": "Trendyol",
            "price": 4990.0,
            "product_url": "https://www.akakce.com/test.html",
            "scraped_at": "2026-04-18",
        }
        row.update(overrides)
        return row

    def test_insert_single_product(self):
        row = self._sample_row()
        self.db.insert_product(row)

        cursor = self.db.conn.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)

    def test_insert_product_persists_data(self):
        row = self._sample_row(brand="MSI", product_code="MSI-123")
        self.db.insert_product(row)

        cursor = self.db.conn.execute(
            "SELECT brand, product_code FROM products WHERE product_code = ?",
            ("MSI-123",),
        )
        result = cursor.fetchone()
        self.assertEqual(result[0], "MSI")
        self.assertEqual(result[1], "MSI-123")

    def test_insert_products_batch(self):
        rows = [
            self._sample_row(marketplace="Amazon"),
            self._sample_row(marketplace="Trendyol"),
            self._sample_row(marketplace="Hepsiburada"),
        ]
        self.db.insert_products(rows)

        cursor = self.db.conn.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]

        self.assertEqual(count, 3)

    def test_insert_products_empty_list(self):
        self.db.insert_products([])

        cursor = self.db.conn.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)

    def test_insert_product_with_none_values(self):
        row = self._sample_row(brand=None, marketplace=None, price=None)
        self.db.insert_product(row)

        cursor = self.db.conn.execute("SELECT brand, marketplace, price FROM products")
        result = cursor.fetchone()
        self.assertIsNone(result[0])
        self.assertIsNone(result[1])
        self.assertIsNone(result[2])

    def test_scraped_at_format(self):
        row = self._sample_row(scraped_at="2026-04-18")
        self.db.insert_product(row)

        cursor = self.db.conn.execute("SELECT scraped_at FROM products")
        result = cursor.fetchone()[0]
        self.assertEqual(result, "2026-04-18")

    def test_context_manager(self):
        with self.db as db:
            db.insert_product(self._sample_row())

            cursor = db.conn.execute("SELECT COUNT(*) FROM products")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)

    def test_task_queue_operations(self):

        self.db.add_target_product("T-001")
        self.db.add_target_product("T-002")
        self.db.add_target_product("T-001")


        target1 = self.db.get_pending_product()
        self.assertIsNotNone(target1)
        self.assertEqual(target1["product_code"], "T-001")
        self.assertEqual(target1["error_count"], 0)

        self.db.update_target_status(target1["id"], "COMPLETED", 0)

        target2 = self.db.get_pending_product()
        self.assertIsNotNone(target2)
        self.assertEqual(target2["product_code"], "T-002")

        self.db.update_target_status(target2["id"], "PENDING", target2["error_count"] + 1)

        target3 = self.db.get_pending_product()
        self.assertIsNotNone(target3)
        self.assertEqual(target3["product_code"], "T-002")
        self.assertEqual(target3["error_count"], 1)

        self.db.update_target_status(target3["id"], "FAILED", 1)

        empty = self.db.get_pending_product()

        self.assertIsNone(empty)

    def test_singleton_pattern(self):
        db2 = DatabaseService()
        self.assertIs(self.db, db2)

    def test_ensure_connection_reconnects_after_close(self):

        self.db.close()
        self.assertIsNone(self.db._connection)

        original_connect = self.db._connect
        def mock_reconnect():
            """Recreate in-memory schema for singleton reconnect recovery."""
            self.db._connection = sqlite3.connect(":memory:")
            self.db._connection.execute("PRAGMA foreign_keys=ON;")
            self.db._initialize_schema()
            self.db._connection.commit()
        self.db._connect = mock_reconnect

        self.db._ensure_connection()

        self.assertIsNotNone(self.db._connection)

        self.db.insert_product(self._sample_row())
        cursor = self.db._connection.execute("SELECT COUNT(*) FROM products")
        self.assertEqual(cursor.fetchone()[0], 1)

        self.db._connect = original_connect

    def test_ensure_connection_noop_when_connected(self):

        conn_before = self.db._connection
        self.db._ensure_connection()
        self.assertIs(self.db._connection, conn_before)

    def test_insert_product_populates_relational_schema(self):
        row = self._sample_row()

        self.db.insert_product(row)

        catalog = self.db.conn.execute(
            "SELECT brand, product_code FROM product_catalog WHERE product_code = ?",
            ("RZ01-001",),
        ).fetchone()
        marketplace = self.db.conn.execute(
            "SELECT name FROM marketplaces WHERE name = ?",
            ("Trendyol",),
        ).fetchone()
        observation = self.db.conn.execute(
            """
            SELECT pc.product_code, m.name, po.price
            FROM price_observations AS po
            JOIN product_catalog AS pc ON pc.id = po.product_id
            JOIN marketplaces AS m ON m.id = po.marketplace_id
            """
        ).fetchone()

        self.assertEqual(catalog, ("Razer", "RZ01-001"))
        self.assertEqual(marketplace[0], "Trendyol")
        self.assertEqual(observation, ("RZ01-001", "Trendyol", 4990.0))

    def test_offer_history_view_joins_product_and_marketplace_dimensions(self):
        self.db.insert_product(self._sample_row())

        row = self.db.conn.execute(
            """
            SELECT product_code, brand, marketplace, price
            FROM v_product_offer_history
            WHERE product_code = ?
            """,
            ("RZ01-001",),
        ).fetchone()

        self.assertEqual(row, ("RZ01-001", "Razer", "Trendyol", 4990.0))

    def test_marketplace_summary_view_aggregates_prices(self):
        rows = [
            self._sample_row(product_code="P1", marketplace="Amazon", price=100.0),
            self._sample_row(product_code="P2", marketplace="Amazon", price=200.0),
            self._sample_row(product_code="P3", marketplace="Trendyol", price=150.0),
        ]

        self.db.insert_products(rows)

        summary = {
            row[0]: row[1:]
            for row in self.db.conn.execute(
                """
                SELECT marketplace, listing_count, product_count, min_price, average_price, max_price
                FROM v_marketplace_price_summary
                """
            ).fetchall()
        }

        self.assertEqual(summary["Amazon"], (2, 2, 100.0, 150.0, 200.0))
        self.assertEqual(summary["Trendyol"], (1, 1, 150.0, 150.0, 150.0))

    def test_target_status_history_trigger_records_queue_transitions(self):
        self.db.add_target_product("T-003")
        target = self.db.get_pending_product()
        assert target is not None

        self.db.update_target_status(target["id"], "COMPLETED", 0)

        history = self.db.conn.execute(
            """
            SELECT old_status, new_status, old_error_count, new_error_count
            FROM target_status_history
            WHERE product_code = ?
            ORDER BY id ASC
            """,
            ("T-003",),
        ).fetchall()

        self.assertEqual(
            history,
            [
                (None, "PENDING", None, 0),
                ("PENDING", "IN_PROGRESS", 0, 0),
                ("IN_PROGRESS", "COMPLETED", 0, 0),
            ],
        )

if __name__ == "__main__":
    unittest.main()
