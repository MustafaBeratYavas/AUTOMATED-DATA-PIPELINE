# -- Detail Scraper Unit Tests --
# Tests title, price, and category extraction precisely targeting
# DOM element parsers via the DetailScraper service.

import unittest
from unittest.mock import MagicMock, patch
from src.services.detail_scraper import DetailScraper
from src.models.product import ProductDTO

class TestDetailScraper(unittest.TestCase):

    def setUp(self):
        self.mock_driver = MagicMock()
        with patch("src.services.detail_scraper.Config"),             patch("src.services.detail_scraper.Logger"):
            self.scraper = DetailScraper(self.mock_driver)

    def test_extract_title(self):
        dto = ProductDTO(code="T004")
        mock_el = MagicMock()
        mock_el.text = "Razer DeathAdder V3"
        self.mock_driver.find_elements.return_value = [mock_el]

        self.scraper._extract_title(dto, {"title": "h1"})

        # Title should be set verbatim from element text
        self.assertEqual(dto.title, "Razer DeathAdder V3")

    def test_extract_price(self):
        dto = ProductDTO(code="T005")
        mock_el = MagicMock()
        mock_el.text = "1.500,00 TL"
        self.mock_driver.find_elements.return_value = [mock_el]

        self.scraper._extract_price(dto, {"price": "span.pt"})

        # Formatted price text should cleanly resolve to a native float
        self.assertAlmostEqual(dto.price, 1500.0)

    def test_extract_price_no_element(self):
        dto = ProductDTO(code="T006")
        self.mock_driver.find_elements.return_value = []

        self.scraper._extract_price(dto, {"price": "span.pt"})

        # Graceful fallback: 0.0 when no span found
        self.assertAlmostEqual(dto.price, 0.0)

    def test_extract_category_from_breadcrumb(self):
        dto = ProductDTO(code="T007")
        mock_crumbs = [
            MagicMock(text="Elektronik"),
            MagicMock(text="Çevre Birimleri"),
            MagicMock(text="Kulaklık"),
            MagicMock(text="Razer Kulaklık"),
        ]
        self.mock_driver.find_elements.return_value = mock_crumbs

        self.scraper._extract_category(dto, {"category_crumb": "nav ol li a"})

        # Should accurately extract the primary sub-category based on depth
        self.assertEqual(dto.category, "Kulaklık")

    def test_extract_category_single_crumb(self):
        dto = ProductDTO(code="T008")
        self.mock_driver.find_elements.return_value = [MagicMock(text="Kulaklık")]

        self.scraper._extract_category(dto, {"category_crumb": "nav ol li a"})

        self.assertEqual(dto.category, "Kulaklık")

    def test_extract_category_no_crumbs(self):
        dto = ProductDTO(code="T009")
        self.mock_driver.find_elements.return_value = []

        self.scraper._extract_category(dto, {"category_crumb": "nav ol li a"})

        self.assertIsNone(dto.category)

    def test_full_scrape_success(self):
        dto = ProductDTO(code="T010")
        self.scraper.config = MagicMock()
        self.scraper.config.get.return_value = [0.5, 1.0]

        with patch.object(self.scraper, "_extract_title"),             patch.object(self.scraper, "_extract_price"),             patch.object(self.scraper, "_extract_category"),             patch("src.services.detail_scraper.random.random", return_value=0.5),             patch("src.services.detail_scraper.time_utils"):

            # Verify unified process succeeds when all extraction stages pass
            result = self.scraper.scrape(dto)
            self.assertTrue(result)

if __name__ == "__main__":
    unittest.main()
