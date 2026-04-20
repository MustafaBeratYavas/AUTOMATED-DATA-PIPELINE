# -- Batch Processor Unit Tests --
# Validates the queue management and sequential processing logic
# of the BatchProcessor loop, including retry mechanisms and error handling.

import unittest
from unittest.mock import MagicMock, patch
from src.engine.batch_processor import BatchProcessor
from src.models.product import ProductDTO
from src.core.exceptions import DatabaseError

class TestBatchProcessor(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_scraper = MagicMock()

        # Isolate the processor from actual DB and Scraping implementations
        with patch("src.engine.batch_processor.Logger"):
            self.processor = BatchProcessor(self.mock_db, self.mock_scraper)
            self.processor.logger = MagicMock()

    def test_run_success(self):
        self.mock_db.get_pending_product.side_effect = [
            {"id": 1, "product_code": "T001", "error_count": 0},
            None
        ]
        
        result_dto = ProductDTO(code="T001", brand="Razer", title="Test Product")
        self.mock_scraper.process_product.return_value = result_dto

        self.processor.run()

        # Verify standard success flow: process -> insert -> update status
        self.mock_scraper.process_product.assert_called_once()
        self.mock_db.insert_products.assert_called_once()
        self.mock_db.update_target_status.assert_called_once_with(1, "COMPLETED", 0)

    def test_run_multiple_codes(self):
        self.mock_db.get_pending_product.side_effect = [
            {"id": 1, "product_code": "T001", "error_count": 0},
            {"id": 2, "product_code": "T002", "error_count": 0},
            None
        ]

        self.processor.run()

        self.assertEqual(self.mock_scraper.process_product.call_count, 2)
        self.assertEqual(self.mock_db.insert_products.call_count, 2)
        self.assertEqual(self.mock_db.update_target_status.call_count, 2)

    def test_run_scraper_exception_pending_retry(self):
        self.mock_db.get_pending_product.side_effect = [
            {"id": 1, "product_code": "T001", "error_count": 0},
            None
        ]
        self.mock_scraper.process_product.side_effect = Exception("Crash")

        self.processor.run(max_retries=3)

        # Verify error count increments and status returns to PENDING for retry
        self.mock_db.update_target_status.assert_called_once_with(1, "PENDING", 1)

    def test_run_scraper_exception_max_retries_fail(self):
        self.mock_db.get_pending_product.side_effect = [
            {"id": 1, "product_code": "T001", "error_count": 2},
            None
        ]
        self.mock_scraper.process_product.side_effect = Exception("Crash")

        self.processor.run(max_retries=3)

        # Verify job is marked as FAILED once max retries limit is exceeded
        self.mock_db.update_target_status.assert_called_once_with(1, "FAILED", 3)

    def test_run_database_error_continues(self):
        self.mock_db.get_pending_product.side_effect = [
            {"id": 1, "product_code": "T001", "error_count": 0},
            None
        ]
        self.mock_db.insert_products.side_effect = DatabaseError("DB crash")

        self.processor.run()

        self.mock_db.update_target_status.assert_called_once_with(1, "PENDING", 1)

    def test_run_empty_queue(self):
        self.mock_db.get_pending_product.return_value = None

        self.processor.run()

        self.mock_scraper.process_product.assert_not_called()
        self.mock_db.insert_products.assert_not_called()

if __name__ == "__main__":
    unittest.main()
