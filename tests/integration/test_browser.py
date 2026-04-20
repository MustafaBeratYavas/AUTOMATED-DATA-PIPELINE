# -- Browser Engine Integration Tests --
# Tests the actual WebDriver orchestration on a real browsing environment
# to ensure network and execution contexts are operational.

import unittest
from src.engine.browser import BrowserEngine

class TestBrowser(unittest.TestCase):

    def test_browser_launch(self):
        
        try:
            with BrowserEngine() as driver:
                driver.get("https://www.google.com")
                # Confirm the browser can fully render a live external web page
                self.assertIn("Google", driver.title)
        except Exception as e:
            self.fail(f"Tarayıcı başlatma hatası: {e}")

if __name__ == "__main__":
    unittest.main()
