# -- String Utilities Unit Tests --
# Validates text normalization utilities, specifically focusing on Turkish price
# parsing, localized text cleaning, and ASCII transliteration.

import unittest
from src.utils.string_utils import clean_price, clean_text, to_ascii

class TestCleanPrice(unittest.TestCase):

    def test_standard_turkish_format(self):
        self.assertAlmostEqual(clean_price("38.500,00 TL"), 38500.00)

    def test_with_whitespace(self):
        self.assertAlmostEqual(clean_price(" 1.200 tl "), 1200.0)

    def test_with_lira_symbol(self):
        self.assertAlmostEqual(clean_price("₺ 999,99"), 999.99)

    def test_empty_string(self):
        # Empty inputs should safely default to 0.0 value
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

    def test_turkish_chars(self):
        # Ensure complete case-sensitive mapping of Turkish-specific characters
        self.assertEqual(to_ascii("çğışöüÇĞİŞÖÜ"), "cgisouCGISOU")

    def test_plain_ascii(self):
        self.assertEqual(to_ascii("Hello"), "Hello")

    def test_empty(self):
        self.assertEqual(to_ascii(""), "")

    def test_none(self):
        self.assertEqual(to_ascii(None), "")

if __name__ == "__main__":
    unittest.main()
