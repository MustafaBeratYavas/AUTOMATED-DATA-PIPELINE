"""Unit tests for scraper orchestration and fallback routing."""

import unittest
from unittest.mock import MagicMock, patch
from src.services.scraper_service import ScraperService
from src.models.product import ProductDTO

class TestScraperService(unittest.TestCase):
    """Validate direct URL, internal search, and Google fallback behavior."""

    def setUp(self):
        """Create a ScraperService with mocked collaborators."""
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
        self.mock_driver.current_url = "https://www.akakce.com/razer-t001.html"
        self.mock_detail.scrape.side_effect = lambda product: setattr(product, "title", "Razer T001") or True

        result = self.service.process_product(dto)


        self.assertIsNotNone(result.url)
        self.mock_detail.scrape.assert_called_once()

    def test_direct_url_fail_triggers_search(self):
        dto = ProductDTO(code="T002", url="https://www.akakce.com/fail.html")
        self.mock_detail.scrape.return_value = False
        self.mock_search.search_internal.return_value = False
        self.mock_search.search_google.return_value = []


        self.service.process_product(dto)

        self.mock_search.search_internal.assert_called_once()

    def test_no_url_goes_to_search(self):
        dto = ProductDTO(code="T003")
        self.mock_search.search_internal.return_value = False
        self.mock_search.search_google.return_value = []


        self.service.process_product(dto)

        self.mock_search.search_internal.assert_called_once()

    def test_analyze_internal_results_detail(self):
        title_element = MagicMock()
        title_element.text = "Razer CODE Gaming Mouse"
        link_element = MagicMock()
        link_element.get_attribute.return_value = "https://www.akakce.com/razer-code.html"

        item = MagicMock()
        item.find_element.side_effect = [title_element, link_element]
        self.mock_search.get_result_items.return_value = [item]

        with patch.object(self.service, "_handle_detail_result") as mock_handler:
            self.service._analyze_internal_results("CODE", ProductDTO(code="CODE"))
            mock_handler.assert_called_once()

    def test_analyze_internal_results_rejects_embedded_code(self):
        title_element = MagicMock()
        title_element.text = "Razer XCODE Gaming Mouse"
        link_element = MagicMock()
        link_element.get_attribute.return_value = "https://www.akakce.com/razer-xcode.html"

        item = MagicMock()
        item.find_element.side_effect = [title_element, link_element]
        self.mock_search.get_result_items.return_value = [item]

        with patch.object(self.service, "_handle_detail_result") as mock_handler:
            result = self.service._analyze_internal_results("CODE", ProductDTO(code="CODE"))

        self.assertFalse(result)
        mock_handler.assert_not_called()

    def test_handle_detail_result_success(self):
        dto = ProductDTO(code="D1")
        self.mock_driver.current_url = "https://www.akakce.com/d1.html"
        mock_el = MagicMock()
        with patch.object(self.service, "_scrape_and_extract", return_value=True):
            result = self.service._handle_detail_result(mock_el, dto, "D1")
            self.assertTrue(result)

    def test_handle_detail_result_rejects_external_redirect(self):
        dto = ProductDTO(code="D1")
        self.mock_driver.current_url = "https://external.example/d1.html"
        mock_el = MagicMock()

        with patch.object(self.service, "_scrape_and_extract") as mock_scrape:
            result = self.service._handle_detail_result(mock_el, dto, "D1")

        self.assertFalse(result)
        self.assertIsNone(dto.url)
        mock_scrape.assert_not_called()

    def test_try_google_search_success(self):
        dto = ProductDTO(code="G1")
        self.service.search.search_google.return_value = ["http://akakce.com/1"]
        self.mock_driver.current_url = "http://akakce.com/g1.html"

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

    def test_is_internal_product_href_rejects_suffix_trap(self):
        self.assertFalse(self.service._is_internal_product_href("https://fakeakakce.com/p.html"))
        self.assertTrue(self.service._is_internal_product_href("https://www.akakce.com/p.html"))

    def test_is_internal_product_href_rejects_search_pages(self):
        self.assertFalse(self.service._is_internal_product_href("https://www.akakce.com/c/?q=CODE"))

    def test_scrape_and_extract_rejects_detail_code_mismatch(self):
        dto = ProductDTO(code="CODE")
        self.mock_driver.current_url = "https://www.akakce.com/other-product.html"
        self.mock_detail.scrape.side_effect = lambda product: setattr(product, "title", "Other Product") or True

        result = self.service._scrape_and_extract(dto)

        self.assertFalse(result)
        self.mock_seller.extract_from_detail_page.assert_not_called()

if __name__ == "__main__":
    unittest.main()
