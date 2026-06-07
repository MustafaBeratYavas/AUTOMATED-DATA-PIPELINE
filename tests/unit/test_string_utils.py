"""Unit tests for price, seller text, and ASCII normalization helpers."""

import unittest
from src.utils.string_utils import (
    canonical_product_code,
    clean_price,
    clean_text,
    normalize_product_code,
    product_code_matches_text,
    to_ascii,
)

class TestCleanPrice(unittest.TestCase):
    """Validate localized price parsing edge cases."""

    def test_standard_turkish_format(self):
        self.assertAlmostEqual(clean_price("38.500,00 TL"), 38500.00)

    def test_with_whitespace(self):
        self.assertAlmostEqual(clean_price(" 1.200 tl "), 1200.0)

    def test_with_lira_symbol(self):
        self.assertAlmostEqual(clean_price("₺ 999,99"), 999.99)

    def test_empty_string(self):

        self.assertAlmostEqual(clean_price(""), 0.0)

    def test_none_input(self):
        self.assertAlmostEqual(clean_price(None), 0.0)

    def test_invalid_text(self):
        self.assertAlmostEqual(clean_price("geçersiz"), 0.0)

    def test_integer_price(self):
        self.assertAlmostEqual(clean_price("500 TL"), 500.0)

    def test_decimal_only(self):
        self.assertAlmostEqual(clean_price("0,99 TL"), 0.99)

    def test_large_number(self):
        self.assertAlmostEqual(clean_price("1.234.567,89 TL"), 1234567.89)

class TestCleanText(unittest.TestCase):
    """Validate seller label cleanup behavior."""

    def test_slash_split(self):
        self.assertEqual(clean_text("Trendyol / Satıcı"), "Trendyol")

    def test_no_slash(self):
        self.assertEqual(clean_text("Hepsiburada"), "Hepsiburada")

    def test_with_whitespace(self):
        self.assertEqual(clean_text("  Amazon  "), "Amazon")

    def test_empty_string(self):
        self.assertEqual(clean_text(""), "")

    def test_none_input(self):
        self.assertEqual(clean_text(None), "")

class TestToAscii(unittest.TestCase):
    """Validate Turkish character transliteration."""

    def test_turkish_chars(self):

        self.assertEqual(to_ascii("çğışöüÇĞİŞÖÜ"), "cgisouCGISOU")

    def test_plain_ascii(self):
        self.assertEqual(to_ascii("Hello"), "Hello")

    def test_empty(self):
        self.assertEqual(to_ascii(""), "")

    def test_none(self):
        self.assertEqual(to_ascii(None), "")


class TestProductCodeNormalization(unittest.TestCase):
    """Validate robust product-code normalization and bounded matching."""

    def test_normalize_product_code(self):
        self.assertEqual(normalize_product_code(" rz01-04620100-r3g1 "), "RZ01-04620100-R3G1")

    def test_canonical_product_code(self):
        self.assertEqual(canonical_product_code("RZ01-04620100 R3G1"), "rz0104620100r3g1")

    def test_product_code_matches_with_separators(self):
        text = "Razer RZ01 04620100-R3G1 Gaming Mouse"
        self.assertTrue(product_code_matches_text(text, "RZ01-04620100-R3G1"))

    def test_product_code_does_not_match_embedded_token(self):
        self.assertFalse(product_code_matches_text("Razer XCODE Gaming Mouse", "CODE"))

if __name__ == "__main__":
    unittest.main()
