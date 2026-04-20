# -- Main Entrypoint Unit Tests --
# Ensures the application bootstrap initializes services correctly
# and handles fatal runtime exceptions gracefully.

import unittest
from unittest.mock import MagicMock, patch
from src.main import main

class TestMain(unittest.TestCase):

    @patch("src.main.BatchProcessor")
    @patch("src.main.ScraperService")
    @patch("src.main.SellerExtractor")
    @patch("src.main.DetailScraper")
    @patch("src.main.SearchService")
    @patch("src.main.WebDriverWait")
    @patch("src.main.BrowserEngine")
    @patch("src.main.DatabaseService")
    @patch("src.main.Config")
    @patch("src.main.Logger")
    def test_main_normal_flow(self, mock_logger_cls, mock_config,
                               mock_db_cls, mock_browser_cls, mock_wait_cls,
                               mock_search_cls, mock_detail_cls, mock_seller_cls,
                               mock_scraper_cls, mock_batch_cls):
        
        mock_logger = MagicMock()
        mock_logger_cls.get_logger.return_value = mock_logger

        mock_config_inst = MagicMock()
        mock_config.return_value = mock_config_inst
        mock_config_inst.get.return_value = "2.0.0"

        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        mock_browser = MagicMock()
        mock_browser_cls.return_value = mock_browser
        mock_browser.start.return_value = MagicMock()

        mock_processor = MagicMock()
        mock_batch_cls.return_value = mock_processor

        main()

        # Verify normal flow sets up processor and starts the run loop with retries
        mock_batch_cls.assert_called_once()
        mock_processor.run.assert_called_once_with(max_retries=3)

    @patch("src.main.Config")
    @patch("src.main.Logger")
    def test_main_fatal_error(self, mock_logger_cls, mock_config):
        
        mock_logger = MagicMock()
        mock_logger_cls.get_logger.return_value = mock_logger

        mock_config_inst = MagicMock()
        mock_config.return_value = mock_config_inst
        mock_config_inst.get.return_value = "2.0.0"

        # Ensure a critical module crash forces a clean sys.exit instead of hanging
        with patch("src.main.DatabaseService", side_effect=Exception("Database crash")):
            with self.assertRaises(SystemExit) as cm:
                main()

        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
