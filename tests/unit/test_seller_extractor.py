# -- Seller Extractor Unit Tests --
# Checks seller identification, price parsing, and deduplication logic
# across both compact card layouts and full product detail pages.

import unittest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException

from src.services.seller_extractor import SellerExtractor
from src.models.product import ProductDTO

class TestSellerExtractor(unittest.TestCase):

    def setUp(self):
        self.mock_driver = MagicMock()
        with patch("src.services.seller_extractor.Config"),             patch("src.services.seller_extractor.Logger"):
            self.extractor = SellerExtractor(self.mock_driver)
            self.extractor.config = MagicMock()
            self.extractor.logger = MagicMock()

    def _mock_config_get(self, *keys, **kwargs):
        mapping = {
            ("selectors", "product"): {
                "sellers_list": "ul#PL",
                "sellers_list_item": "li",
                "sellers_alt_item": "li.w_v8",
                "seller_price": "span.pt_v8",
                "seller_name_wrapper": "span.v_v8",
            },
            ("selectors", "card", "sellers_container"): "div.p_w_v9",
            ("selectors", "card", "seller_link"): "a",
            ("selectors", "card", "seller_price"): "span.pt_v8",
            ("selectors", "card", "seller_name_img"): "span.l img",
            ("selectors", "card", "seller_name_text"): "span.l b",
            ("selectors", "search_result_price"): "span.pt_v8",
        }
        return mapping.get(keys, kwargs.get("default"))

    def test_extract_from_detail_page_with_sellers(self):
        self.extractor.config.get = self._mock_config_get

        mock_ul = MagicMock()
        mock_item = MagicMock()

        mock_price_el = MagicMock()
        mock_price_el.text = "1.500,00 TL"

        mock_name_wrapper = MagicMock()
        mock_name_wrapper.find_elements.side_effect = [
            [],
            [MagicMock(text="Trendyol")],
        ]

        def item_find_element(by, sel):
            if "pt_v8" in sel:
                return mock_price_el
            if "v_v8" in sel:
                return mock_name_wrapper
            raise NoSuchElementException()

        mock_item.find_element.side_effect = item_find_element
        mock_ul.find_elements.return_value = [mock_item]

        def driver_find_elements(by, sel):
            if "//*" in sel:
                return []
            if "ul#PL" in sel or "ul.pl_v9" in sel:
                return [mock_ul]
            if "li.w_v8" in sel:
                return []
            return []

        self.mock_driver.find_elements.side_effect = driver_find_elements

        dto = ProductDTO(code="T001")
        self.extractor.extract_from_detail_page(dto)

        # Should gracefully map multiple sellers to the DTO with normalized extraction
        self.assertEqual(len(dto.sellers), 1)
        self.assertEqual(dto.sellers[0]["name"], "Trendyol")
        self.assertGreater(dto.price, 0)
        self.assertEqual(dto.price, 1500.0)

    def test_extract_from_detail_page_no_sellers(self):
        self.extractor.config.get = self._mock_config_get
        self.mock_driver.find_elements.return_value = []

        dto = ProductDTO(code="T002")
        self.extractor.extract_from_detail_page(dto)

        self.assertEqual(dto.sellers, [])

    def test_extract_from_card_no_container(self):
        self.extractor.config.get = self._mock_config_get
        mock_element = MagicMock()
        mock_element.find_element.side_effect = NoSuchElementException()

        dto = ProductDTO(code="T003")
        self.extractor.extract_from_card(mock_element, dto)

        self.assertEqual(dto.sellers, [])

    def test_extract_from_card_with_price_fallback(self):
        self.extractor.config.get = self._mock_config_get
        mock_element = MagicMock()
        mock_element.find_element.side_effect = [
            NoSuchElementException(),
            MagicMock(text="999,99 TL"),
        ]

        dto = ProductDTO(code="T004")
        self.extractor.extract_from_card(mock_element, dto)

        self.assertEqual(dto.sellers, [])

    def test_deduplicate(self):
        sellers = [
            {"name": "Amazon", "price": 100.0},
            {"name": "Amazon", "price": 100.0},
            {"name": "Trendyol", "price": 120.0},
        ]
        # Ensure identical seller-price combinations are deduplicated (e.g. sponsored duplicates)
        result = self.extractor._deduplicate(sellers)
        self.assertEqual(len(result), 2)

    def test_deduplicate_empty(self):
        result = self.extractor._deduplicate([])
        self.assertEqual(result, [])

    def test_parse_detail_seller_no_price(self):
        product_sel = {"seller_price": "span.pt_v8", "seller_name_wrapper": "span.v_v8"}
        mock_item = MagicMock()
        mock_item.find_element.side_effect = NoSuchElementException()

        result = self.extractor._parse_detail_seller(mock_item, product_sel)
        self.assertIsNone(result)

    def test_parse_card_seller_with_img(self):
        self.extractor.config.get = self._mock_config_get
        mock_link = MagicMock()
        mock_price_el = MagicMock()
        mock_price_el.text = "500,00 TL"
        mock_img = MagicMock()
        mock_img.get_attribute.return_value = "Hepsiburada"

        mock_link.find_element.return_value = mock_price_el
        mock_link.find_elements.side_effect = [[mock_img]]

        # Attempt to resolve seller name from 'alt' image attributes first
        result = self.extractor._parse_card_seller(mock_link)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Hepsiburada")

    def test_parse_card_seller_with_text(self):
        self.extractor.config.get = self._mock_config_get
        mock_link = MagicMock()
        mock_price_el = MagicMock()
        mock_price_el.text = "750,00 TL"
        mock_text = MagicMock()
        mock_text.text = "N11"

        mock_link.find_element.return_value = mock_price_el
        mock_link.find_elements.side_effect = [[], [mock_text]]

        # Fallback to pure text extraction if a logo/image element is missing
        result = self.extractor._parse_card_seller(mock_link)
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "N11")

    def test_extract_from_card_with_sellers(self):
        self.extractor.config.get = self._mock_config_get
        mock_element = MagicMock()
        mock_container = MagicMock()
        mock_element.find_element.return_value = mock_container

        mock_link = MagicMock()
        mock_price_el = MagicMock()
        mock_price_el.text = "300,00 TL"
        mock_img = MagicMock()
        mock_img.get_attribute.return_value = "Amazon"
        mock_link.find_element.return_value = mock_price_el
        mock_link.find_elements.side_effect = [[mock_img]]
        mock_container.find_elements.return_value = [mock_link]

        dto = ProductDTO(code="T005")
        self.extractor.extract_from_card(mock_element, dto)

        self.assertEqual(len(dto.sellers), 1)
        self.assertEqual(dto.price, 300.0)

    @patch("src.services.seller_extractor.WebDriverWait")
    def test_expand_all_sellers_no_buttons(self, mock_wait_cls):
        self.mock_driver.find_elements.return_value = []

        self.extractor._expand_all_sellers()

        mock_wait_cls.assert_called_once()

    @patch("src.services.seller_extractor.WebDriverWait")
    def test_expand_all_sellers_clicks_button(self, mock_wait_cls):
        mock_button = MagicMock()
        mock_button.is_displayed.return_value = True

        call_count = {"n": 0}
        def find_elements_side_effect(by, sel):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [mock_button]
            return []

        self.mock_driver.find_elements.side_effect = find_elements_side_effect

        mock_wait_instance = MagicMock()
        mock_wait_cls.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = mock_button

        # Ensure hidden sellers are exposed by programmatically clicking 'Load More'
        self.extractor._expand_all_sellers()

        self.mock_driver.execute_script.assert_called()

if __name__ == "__main__":
    unittest.main()
