"""Unit tests for ProductDTO database row normalization."""

import unittest
from datetime import date
from src.models.product import ProductDTO

class TestProductDTO(unittest.TestCase):
    """Validate DTO defaults and seller-to-row expansion."""

    def test_no_sellers_single_row(self):
        dto = ProductDTO(code="P001", brand="Razer", price=500.0)
        rows = dto.to_db_rows()


        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["product_code"], "P001")
        self.assertEqual(rows[0]["brand"], "Razer")
        self.assertIsNone(rows[0]["marketplace"])
        self.assertEqual(rows[0]["price"], 500.0)

    def test_multiple_sellers(self):
        dto = ProductDTO(
            code="P002",
            sellers=[
                {"name": "Amazon", "price": 100.0},
                {"name": "Trendyol", "price": 120.0},
            ],
        )
        rows = dto.to_db_rows()


        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["marketplace"], "Amazon")
        self.assertEqual(rows[0]["price"], 100.0)
        self.assertEqual(rows[1]["marketplace"], "Trendyol")
        self.assertEqual(rows[1]["price"], 120.0)

    def test_default_values(self):
        dto = ProductDTO(code="P003")

        self.assertIsNone(dto.url)
        self.assertEqual(dto.brand, "Razer")
        self.assertIsNone(dto.title)
        self.assertIsNone(dto.category)
        self.assertIsNone(dto.price)
        self.assertEqual(dto.sellers, [])

    def test_no_sellers_no_price_returns_none_price(self):
        dto = ProductDTO(code="P004")

        rows = dto.to_db_rows()

        self.assertEqual(rows[0]["brand"], "Razer")
        self.assertIsNone(rows[0]["marketplace"])
        self.assertIsNone(rows[0]["price"])

    def test_scraped_at_format(self):
        dto = ProductDTO(code="P005")
        rows = dto.to_db_rows()

        expected = date.today().strftime("%Y-%m-%d")
        self.assertEqual(rows[0]["scraped_at"], expected)

    def test_to_db_rows_includes_all_columns(self):
        dto = ProductDTO(
            code="P006",
            brand="MSI",
            title="MSI Monitor",
            category="Monitör",
            url="https://akakce.com/test",
            sellers=[{"name": "Shop", "price": 1234.56}],
        )
        rows = dto.to_db_rows()

        expected_keys = {
            "brand", "product_code", "product_category", "product_name",
            "marketplace", "price", "product_url", "scraped_at",
        }

        self.assertEqual(set(rows[0].keys()), expected_keys)
        self.assertEqual(rows[0]["product_category"], "Monitör")

    def test_seller_price_stored_as_float(self):
        dto = ProductDTO(
            code="P007",
            sellers=[{"name": "Shop", "price": 1234.56}],
        )
        rows = dto.to_db_rows()

        self.assertIsInstance(rows[0]["price"], float)
        self.assertAlmostEqual(rows[0]["price"], 1234.56)

if __name__ == "__main__":
    unittest.main()
