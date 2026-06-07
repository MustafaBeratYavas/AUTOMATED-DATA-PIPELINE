"""Unit tests for browser lifecycle and WebDriver startup behavior."""

import unittest
from unittest.mock import MagicMock, patch
from src.engine.browser import BrowserEngine

class TestBrowserEngine(unittest.TestCase):
    """Validate BrowserEngine context management and startup failure handling."""

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_init(self, mock_logger, mock_config):
        engine = BrowserEngine()
        self.assertIsNone(engine.driver)

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_context_manager_enter_calls_start(self, mock_logger, mock_config):
        engine = BrowserEngine()
        engine.start = MagicMock()
        engine.driver = MagicMock()

        result = engine.__enter__()
        engine.start.assert_called_once()
        self.assertEqual(result, engine.driver)

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_context_manager_exit_calls_stop(self, mock_logger, mock_config):
        engine = BrowserEngine()
        engine.stop = MagicMock()

        engine.__exit__(None, None, None)
        engine.stop.assert_called_once()

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_start_skips_if_driver_exists(self, mock_logger, mock_config):
        engine = BrowserEngine()
        engine.driver = MagicMock()
        engine.start()
        self.assertIsNotNone(engine.driver)

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_stop_quits_driver(self, mock_logger, mock_config):
        engine = BrowserEngine()
        mock_driver = MagicMock()
        engine.driver = mock_driver
        engine.logger = MagicMock()

        engine.stop()

        mock_driver.quit.assert_called_once()
        self.assertIsNone(engine.driver)

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_stop_handles_quit_error(self, mock_logger, mock_config):
        engine = BrowserEngine()
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = Exception("quit failed")
        engine.driver = mock_driver
        engine.logger = MagicMock()

        engine.stop()

        self.assertIsNone(engine.driver)

    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_stop_no_driver(self, mock_logger, mock_config):
        engine = BrowserEngine()
        engine.driver = None
        engine.logger = MagicMock()
        engine.stop()
        self.assertIsNone(engine.driver)

    @patch("src.engine.browser.Driver")
    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_start_initializes_driver(self, mock_logger, mock_config, mock_driver_cls):
        engine = BrowserEngine()
        engine.logger = MagicMock()

        mock_config_instance = MagicMock()
        engine.config = mock_config_instance
        mock_config_instance.get.side_effect = lambda *a, **kw: {
            ("browser", "headless"): True,
            ("browser", "start_maximized"): True,
            ("browser", "page_load_timeout"): 30,
            ("browser", "user_agent"): None,
            ("browser", "user_data_dir"): "data/chrome_profile",
            ("urls", "base"): "https://www.akakce.com",
            ("browser", "reconnect_time"): 6,
            ("browser", "captcha_auto_click"): False,
        }.get(a, kw.get("default"))

        mock_driver_instance = MagicMock()
        mock_driver_cls.return_value = mock_driver_instance


        engine.start()

        mock_driver_cls.assert_called_once()
        self.assertEqual(engine.driver, mock_driver_instance)

    @patch("src.engine.browser.Driver")
    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_start_uses_start_maximized_for_visible_browser(
        self, mock_logger, mock_config, mock_driver_cls
    ):
        engine = BrowserEngine()
        engine.logger = MagicMock()

        mock_config_instance = MagicMock()
        engine.config = mock_config_instance
        mock_config_instance.get.side_effect = lambda *a, **kw: {
            ("browser", "headless"): False,
            ("browser", "start_maximized"): True,
            ("browser", "page_load_timeout"): 30,
            ("browser", "user_agent"): None,
            ("browser", "user_data_dir"): "data/chrome_profile",
            ("urls", "base"): "https://www.akakce.com",
            ("browser", "reconnect_time"): 6,
            ("browser", "captcha_auto_click"): False,
        }.get(a, kw.get("default"))

        mock_driver_instance = MagicMock()
        mock_driver_cls.return_value = mock_driver_instance

        engine.start()

        chromium_args = mock_driver_cls.call_args.kwargs["chromium_arg"]
        self.assertIn("--start-maximized", chromium_args)
        self.assertFalse(any(arg.startswith("--window" "-size=") for arg in chromium_args))
        mock_driver_instance.maximize_window.assert_not_called()

    @patch("src.engine.browser.Driver")
    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_start_does_not_set_dimension_arg_for_headless_browser(
        self, mock_logger, mock_config, mock_driver_cls
    ):
        engine = BrowserEngine()
        engine.logger = MagicMock()

        mock_config_instance = MagicMock()
        engine.config = mock_config_instance
        mock_config_instance.get.side_effect = lambda *a, **kw: {
            ("browser", "headless"): True,
            ("browser", "start_maximized"): True,
            ("browser", "page_load_timeout"): 30,
            ("browser", "user_agent"): None,
            ("browser", "user_data_dir"): "data/chrome_profile",
            ("urls", "base"): "https://www.akakce.com",
            ("browser", "reconnect_time"): 6,
            ("browser", "captcha_auto_click"): False,
        }.get(a, kw.get("default"))

        mock_driver_cls.return_value = MagicMock()

        engine.start()

        chromium_args = mock_driver_cls.call_args.kwargs["chromium_arg"]
        self.assertNotIn("--start-maximized", chromium_args)
        self.assertFalse(any(arg.startswith("--window" "-size=") for arg in chromium_args))

    @patch("src.engine.browser.Driver")
    @patch("src.engine.browser.Config")
    @patch("src.engine.browser.Logger")
    def test_start_failure_calls_stop(self, mock_logger, mock_config, mock_driver_cls):
        engine = BrowserEngine()
        engine.logger = MagicMock()
        engine.config = MagicMock()
        engine.config.get.side_effect = Exception("config fail")


        with self.assertRaises(Exception):
            engine.start()

        self.assertIsNone(engine.driver)

if __name__ == "__main__":
    unittest.main()
