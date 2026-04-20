# -- Scraper Orchestration Unit Tests --
# Validates the three-tier fallback strategy (Direct URL -> Internal Search -> Google)
# and ensures correct delegation to extraction sub-components.

import unittest
from unittest.mock import MagicMock, patch
from src.services.scraper_service import ScraperService
from src.models.product import ProductDTO

class TestScraperService(unittest.TestCase):

    def setUp(self):
        
        self.mock_driver = MagicMock()
        self.mock_driver.current_url = "https://www.akakce.com"
        self.mock_driver.page_source = "<html>TEST-001</html>"
        
        self.mock_search = MagicMock()
        self.mock_detail = MagicMock()
        self.mock_seller = MagicMock()

        self.service = ScraperService(
            self.mock_driver,
            self.mock_search,
            self.mock_detail,
            self.mock_seller
        )

    def test_direct_url_success(self):
        dto = ProductDTO(code="T001", url="https://www.akakce.com/p.html")
        self.mock_detail.scrape.return_value = True

        result = self.service.process_product(dto)

        # Strategy 1 Success: Direct URL parse completes gracefully without search
        self.assertIsNotNone(result.url)
        self.mock_detail.scrape.assert_called_once()

    def test_direct_url_fail_triggers_search(self):
        dto = ProductDTO(code="T002", url="https://www.akakce.com/fail.html")
        self.mock_detail.scrape.return_value = False
        self.mock_search.search_internal.return_value = False
        self.mock_search.search_google.return_value = []

        # Strategy 2 Fallback: If URL fails, it should pivot to internal search
        self.service.process_product(dto)

        self.mock_search.search_internal.assert_called_once()

    def test_no_url_goes_to_search(self):
        dto = ProductDTO(code="T003")
        self.mock_search.search_internal.return_value = False
        self.mock_search.search_google.return_value = []

        # Strategy 2 Native: Items with no URL go directly to internal search
        self.service.process_product(dto)

        self.mock_search.search_internal.assert_called_once()

    def test_analyze_internal_results_card(self):
        self.mock_search.get_result_items.return_value = [MagicMock()]
        self.mock_search.get_result_items.return_value[0].get_attribute.return_value = "n-p"

        with patch.object(self.service, "_handle_card_result") as mock_handler:
            self.service._analyze_internal_results("CODE", ProductDTO(code="CODE"))
            mock_handler.assert_called_once()

    def test_analyze_internal_results_detail(self):
        self.mock_search.get_result_items.return_value = [MagicMock()]
        self.mock_search.get_result_items.return_value[0].get_attribute.return_value = ""

        with patch.object(self.service, "_handle_detail_result") as mock_handler:
            self.service._analyze_internal_results("CODE", ProductDTO(code="CODE"))
            mock_handler.assert_called_once()

    def test_handle_detail_result_success(self):
        dto = ProductDTO(code="D1")
        mock_el = MagicMock()
        with patch.object(self.service, "_scrape_and_extract", return_value=True):
            result = self.service._handle_detail_result(mock_el, dto, "D1")
            self.assertTrue(result)

    def test_try_google_search_success(self):
        dto = ProductDTO(code="G1")
        self.service.search.search_google.return_value = ["http://akakce.com/1"]
        # Strategy 3 Success: External Google search correctly navigates to matched product
        with patch.object(self.service, "_scrape_and_extract", return_value=True):
            self.service._try_google_search(dto)
            self.assertIsNotNone(dto.url)

    def test_try_google_search_fail(self):
        dto = ProductDTO(code="G2")
        self.service.search.search_google.return_value = ["http://akakce.com/fail"]
        with patch.object(self.service, "_scrape_and_extract", return_value=False):
            self.service._try_google_search(dto)

    def test_process_product_returns_dto(self):
        dto = ProductDTO(code="T010")
        self.mock_search.search_internal.return_value = False
        self.mock_search.search_google.return_value = []

        result = self.service.process_product(dto)
        self.assertIsInstance(result, ProductDTO)
        self.assertEqual(result.code, "T010")

if __name__ == "__main__":
    unittest.main()
