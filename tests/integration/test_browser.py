"""Integration smoke test for launching the real browser engine."""

import unittest
from src.engine.browser import BrowserEngine

class TestBrowser(unittest.TestCase):
    """Validate that a live browser can open and render an external page."""

    def test_browser_launch(self):

        try:
            with BrowserEngine() as driver:
                driver.get("https://www.google.com")

                self.assertIn("Google", driver.title)
        except Exception as e:
            self.fail(f"Tarayıcı başlatma hatası: {e}")

if __name__ == "__main__":
    unittest.main()
