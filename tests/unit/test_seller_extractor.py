"""Unit tests for seller extraction from detail page layouts."""

import unittest
from unittest.mock import MagicMock, patch
from selenium.common.exceptions import NoSuchElementException

from src.services.seller_extractor import SellerExtractor
from src.models.product import ProductDTO

class TestSellerExtractor(unittest.TestCase):
    """Validate seller parsing and offer row collection."""

    def setUp(self):
        """Create a SellerExtractor with mocked configuration and driver state."""
        self.mock_driver = MagicMock()
        with patch("src.services.seller_extractor.Config"),             patch("src.services.seller_extractor.Logger"):
            self.extractor = SellerExtractor(self.mock_driver)
            self.extractor.config = MagicMock()
            self.extractor.logger = MagicMock()

    def _mock_config_get(self, *keys, **kwargs):
        """Return selector mappings used by seller extraction tests."""
        mapping = {
            ("selectors", "product"): {
                "sellers_list": "ul#PL",
                "sellers_list_item": "li",
                "sellers_alt_item": "li.w_v8",
                "seller_price": "span.pt_v8",
                "seller_name_wrapper": "span.v_v8",
            },
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
            """Return mocked seller sub-elements according to selector intent."""
            if "pt_v8" in sel:
                return mock_price_el
            if "v_v8" in sel:
                return mock_name_wrapper
            raise NoSuchElementException()

        mock_item.find_element.side_effect = item_find_element
        mock_ul.find_elements.return_value = [mock_item]

        def driver_find_elements(by, sel):
            """Return list containers while suppressing no-price and alt-item paths."""
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


        self.assertEqual(len(dto.sellers), 1)
        self.assertEqual(dto.sellers[0]["name"], "Trendyol")
        self.assertIsNotNone(dto.price)
        self.assertGreater(dto.price, 0)
        self.assertEqual(dto.price, 1500.0)

    def test_collect_detail_seller_items_reads_all_containers(self):
        first_container = MagicMock()
        second_container = MagicMock()
        first_items = [MagicMock(), MagicMock()]
        second_items = [MagicMock()]
        first_container.find_elements.return_value = first_items
        second_container.find_elements.return_value = second_items

        def driver_find_elements(by, sel):
            """Return seller containers and suppress alternative layout rows."""
            if "ul#PL" in sel:
                return [first_container, second_container]
            if "li.w_v8" in sel:
                return []
            return []

        self.mock_driver.find_elements.side_effect = driver_find_elements

        product_sel = self._mock_config_get("selectors", "product")
        assert product_sel is not None

        result = self.extractor._collect_detail_seller_items(product_sel, "T001")

        self.assertEqual(result, first_items + second_items)

    def test_extract_from_detail_page_no_sellers(self):
        self.extractor.config.get = self._mock_config_get
        self.mock_driver.find_elements.return_value = []

        dto = ProductDTO(code="T002")
        self.extractor.extract_from_detail_page(dto)

        self.assertEqual(dto.sellers, [])

    def test_extract_from_detail_page_price_not_found_leaves_database_values_empty(self):
        self.extractor.config.get = self._mock_config_get
        not_found = MagicMock()
        not_found.text = "Fiyat bulunamad"

        def driver_find_elements(by, sel):
            """Expose only the no-price marker."""
            if "Fiyat bulunamad" in sel:
                return [not_found]
            return []

        self.mock_driver.find_elements.side_effect = driver_find_elements

        dto = ProductDTO(code="T003")
        self.extractor.extract_from_detail_page(dto)
        rows = dto.to_db_rows()

        self.assertEqual(dto.sellers, [])
        self.assertIsNone(dto.price)
        self.assertIsNone(rows[0]["marketplace"])
        self.assertIsNone(rows[0]["price"])

    def test_extract_from_detail_page_preserves_equal_offer_rows(self):
        self.extractor.config.get = self._mock_config_get

        mock_ul = MagicMock()
        first_item = MagicMock()
        second_item = MagicMock()
        first_item.id = "offer-1"
        second_item.id = "offer-2"

        price_el = MagicMock()
        price_el.text = "1.500,00 TL"

        def make_name_wrapper():
            wrapper = MagicMock()
            wrapper.find_elements.side_effect = [
                [],
                [MagicMock(text="Trendyol")],
            ]
            return wrapper

        def item_find_element(by, sel):
            """Return identical seller details for distinct offer rows."""
            if "pt_v8" in sel:
                return price_el
            if "v_v8" in sel:
                return make_name_wrapper()
            raise NoSuchElementException()

        first_item.find_element.side_effect = item_find_element
        second_item.find_element.side_effect = item_find_element
        mock_ul.find_elements.return_value = [first_item, second_item]

        def driver_find_elements(by, sel):
            """Return one seller container with two distinct equal-price rows."""
            if "//*" in sel:
                return []
            if "ul#PL" in sel:
                return [mock_ul]
            if "li.w_v8" in sel:
                return []
            return []

        self.mock_driver.find_elements.side_effect = driver_find_elements

        dto = ProductDTO(code="T001")
        self.extractor.extract_from_detail_page(dto)

        self.assertEqual(len(dto.sellers), 2)

    def test_parse_detail_seller_no_price(self):
        product_sel = {"seller_price": "span.pt_v8", "seller_name_wrapper": "span.v_v8"}
        mock_item = MagicMock()
        mock_item.find_element.side_effect = NoSuchElementException()

        result = self.extractor._parse_detail_seller(mock_item, product_sel)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
