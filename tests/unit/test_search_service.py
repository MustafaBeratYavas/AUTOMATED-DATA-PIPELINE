# -- Search Service Unit Tests --
# Evaluates internal marketplace search resolution, Google fallback querying,
# and "No Results" page detection algorithms.

import unittest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import TimeoutException
from src.services.search_service import SearchService
from src.core.exceptions import NetworkError

class TestSearchService(unittest.TestCase):

    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_wait = MagicMock()
        with patch("src.services.search_service.Config"),             patch("src.services.search_service.Logger"):
            self.service = SearchService(self.mock_driver, self.mock_wait)
            self.service.config = MagicMock()
            self.service.logger = MagicMock()

    def _mock_config_get(self, *keys, **kwargs):
        mapping = {
            ("selectors", "search_input"): "textarea[name='q']",
            ("selectors", "search_no_result"): "div.search_v8",
            ("selectors", "search_result_item"): "ul#APL li",
            ("selectors", "google", "result_link"): "div.g a",
            ("urls", "base"): "https://www.akakce.com",
            ("urls", "search"): "https://www.google.com",
            ("scraping", "google_query_format"): 'site:akakce.com {brand} "{code}"',
            ("delays", "typing"): [0.01, 0.02],
            ("delays", "pre_enter"): [0.01, 0.02],
            ("delays", "post_search"): [0.01, 0.02],
        }
        return mapping.get(keys, kwargs.get("default"))

    def test_type_human_like(self):
        self.service.config.get = self._mock_config_get
        mock_element = MagicMock()
        with patch("src.services.search_service.time_utils"):
            self.service._type_human_like(mock_element, "ABC")
        # Emulate human typing delays to bypass basic bot-detection scripts
        mock_element.clear.assert_called_once()
        self.assertEqual(mock_element.send_keys.call_count, 3)

    def test_find_search_box_success(self):
        mock_element = MagicMock()
        self.mock_wait.until.return_value = mock_element
        result = self.service._find_search_box("input[name='q']")
        self.assertEqual(result, mock_element)

    def test_find_search_box_timeout(self):
        self.mock_wait.until.side_effect = TimeoutException()
        # Strict timeout enforcement when core search inputs are missing
        with self.assertRaises(NetworkError):
            self.service._find_search_box("input[name='q']")

    def test_check_no_result_found(self):
        self.service.config.get = self._mock_config_get
        mock_el = MagicMock()
        mock_el.text = "Aradığınız ürün bulunamadı"
        self.mock_driver.find_elements.return_value = [mock_el]
        self.assertTrue(self.service.check_no_result())

    def test_check_no_result_not_found(self):
        self.service.config.get = self._mock_config_get
        self.mock_driver.find_elements.return_value = []
        self.assertFalse(self.service.check_no_result())

    def test_check_no_result_interest(self):
        self.service.config.get = self._mock_config_get
        mock_el = MagicMock()
        mock_el.text = "ilginizi çekebilir"
        self.mock_driver.find_elements.return_value = [mock_el]
        # Must accurately classify suggestion pages as soft failures ("ilginizi çekebilir")
        self.assertTrue(self.service.check_no_result())

    def test_check_no_result_exception(self):
        self.service.config.get = self._mock_config_get
        self.mock_driver.find_elements.side_effect = Exception("fail")
        self.assertFalse(self.service.check_no_result())

    @patch("src.services.search_service.time_utils")
    def test_search_internal_success(self, mock_time):
        self.service.config.get = self._mock_config_get
        self.mock_driver.current_url = "https://www.akakce.com"
        mock_box = MagicMock()
        self.mock_wait.until.return_value = mock_box
        self.mock_driver.find_elements.return_value = []

        result = self.service.search_internal("TEST-001")
        # Normal routing validates internal URL navigation when not on Akakce
        self.assertTrue(result)

    @patch("src.services.search_service.time_utils")
    def test_search_internal_no_result(self, mock_time):
        self.service.config.get = self._mock_config_get
        self.mock_driver.current_url = "https://www.akakce.com"
        mock_box = MagicMock()
        self.mock_wait.until.return_value = mock_box

        mock_el = MagicMock()
        mock_el.text = "bulunamadı"
        self.mock_driver.find_elements.return_value = [mock_el]

        result = self.service.search_internal("NOTFOUND")
        self.assertFalse(result)

    @patch("src.services.search_service.time_utils")
    def test_search_internal_navigates_to_akakce(self, mock_time):
        self.service.config.get = self._mock_config_get
        self.mock_driver.current_url = "https://www.google.com"
        mock_box = MagicMock()
        self.mock_wait.until.return_value = mock_box
        self.mock_driver.find_elements.return_value = []

        self.service.search_internal("TEST-001")
        self.mock_driver.get.assert_called_with("https://www.akakce.com")

    @patch("src.services.search_service.time_utils")
    def test_search_internal_search_box_not_found(self, mock_time):
        self.service.config.get = self._mock_config_get
        self.mock_driver.current_url = "https://www.akakce.com"
        self.mock_wait.until.side_effect = TimeoutException()

        result = self.service.search_internal("TEST-001")
        self.assertFalse(result)

    @patch("src.services.search_service.time_utils")
    def test_search_google_returns_urls(self, mock_time):
        self.service.config.get = self._mock_config_get
        mock_box = MagicMock()
        self.mock_wait.until.return_value = mock_box

        mock_link1 = MagicMock()
        mock_link1.get_attribute.return_value = "https://www.akakce.com/product1.html"
        mock_link2 = MagicMock()
        mock_link2.get_attribute.return_value = "https://www.google.com/search"
        mock_link3 = MagicMock()
        mock_link3.get_attribute.return_value = "https://www.akakce.com/product2.html"
        self.mock_driver.find_elements.return_value = [mock_link1, mock_link2, mock_link3]

        urls = self.service.search_google("TEST-001")
        # Google fallback should parse and return valid candidate URLs only
        self.assertEqual(len(urls), 2)
        self.assertIn("https://www.akakce.com/product1.html", urls)

    @patch("src.services.search_service.time_utils")
    def test_search_google_no_box(self, mock_time):
        self.service.config.get = self._mock_config_get
        self.mock_wait.until.side_effect = TimeoutException()

        urls = self.service.search_google("TEST-001")
        self.assertEqual(urls, [])

    def test_get_result_items(self):
        self.service.config.get = self._mock_config_get
        mock_items = [MagicMock(), MagicMock()]
        self.mock_driver.find_elements.return_value = mock_items

        result = self.service.get_result_items()
        self.assertEqual(len(result), 2)

if __name__ == "__main__":
    unittest.main()
