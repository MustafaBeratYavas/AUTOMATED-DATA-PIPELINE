# -- Database Service Unit Tests --
# Ensures reliable singleton execution, queue synchronization handling,
# and in-memory SQLite state management.

import unittest
import sqlite3
from unittest.mock import patch
from src.services.database import DatabaseService

class TestDatabaseService(unittest.TestCase):
    
    def setUp(self):
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
        self.db._connection.execute(DatabaseService._CREATE_TABLE_SQL)
        self.db._connection.execute(DatabaseService._CREATE_TARGETS_TABLE_SQL)
        self.db._connection.commit()

    def tearDown(self):
        if self.db._connection:
            self.db._connection.close()
        DatabaseService.reset_instance()
        self.config_patcher.stop()
        self.logger_patcher.stop()

    def _sample_row(self, **overrides):
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
        # Should persist the exact batch length provided
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

        # Database queue should process items sequentially as PENDING
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
        # Verify the queue properly returns None when fully exhausted
        self.assertIsNone(empty)

    def test_singleton_pattern(self):
        db2 = DatabaseService()
        self.assertIs(self.db, db2)

    def test_ensure_connection_reconnects_after_close(self):
        
        self.db.close()
        self.assertIsNone(self.db._connection)

        original_connect = self.db._connect
        def mock_reconnect():
            self.db._connection = sqlite3.connect(":memory:")
            self.db._connection.execute(DatabaseService._CREATE_TABLE_SQL)
            self.db._connection.execute(DatabaseService._CREATE_TARGETS_TABLE_SQL)
            self.db._connection.commit()
        self.db._connect = mock_reconnect

        self.db._ensure_connection()
        # The singleton connection should transparently auto-recover
        self.assertIsNotNone(self.db._connection)

        self.db.insert_product(self._sample_row())
        cursor = self.db._connection.execute("SELECT COUNT(*) FROM products")
        self.assertEqual(cursor.fetchone()[0], 1)

        self.db._connect = original_connect

    def test_ensure_connection_noop_when_connected(self):
        
        conn_before = self.db._connection
        self.db._ensure_connection()
        self.assertIs(self.db._connection, conn_before)

if __name__ == "__main__":
    unittest.main()
