# -- Custom Browser Engine --
# Wraps SeleniumBase to provide an undetectable, anti-bot hardened 
# Chrome WebDriver. Implements a context manager lifecycle and reads
# user preferences natively from settings.yaml.

from __future__ import annotations

import os
from typing import Any

from seleniumbase import Driver
from src.core.config import Config
from src.core.logger import Logger
from src.definitions import ROOT_DIR

class BrowserEngine:

    def __init__(self) -> None:
        self.config = Config()
        self.logger = Logger.get_logger(__name__)
        self.driver: Any = None

    def __enter__(self) -> Any:
        # Ensures the driver is started dynamically when the context block is entered
        self.start()
        assert self.driver is not None, "BrowserEngine.start() failed to initialise the driver"
        return self.driver

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        self.stop()

    def start(self) -> None:
        # Factory method launching UC (Undetected-Chromedriver) mode using config tokens
        if self.driver:
            return

        headless = self.config.get("browser", "headless", default=False)
        window_size = self.config.get("browser", "window_size", default="1920,1080")
        page_load_timeout = self.config.get("browser", "page_load_timeout", default=30)
        user_agent = self.config.get("browser", "user_agent")

        user_data_rel = self.config.get("browser", "user_data_dir", default="data/chrome_profile")
        user_data_abs = os.path.join(ROOT_DIR, user_data_rel)

        try:
            self.logger.info("Initializing browser engine (UC Mode)...")
            self.logger.info(f"Profile path: {user_data_abs}")

            chromium_args = [
                f"--window-size={window_size}",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-popup-blocking",
            ]

            self.driver = Driver(
                uc=True,
                headless=headless,
                chromium_arg=chromium_args,
                user_data_dir=user_data_abs,
            )

            base_url = self.config.get("urls", "base", default="https://www.akakce.com")
            reconnect_time = self.config.get("browser", "reconnect_time", default=6)
            try:
                self.driver.uc_open_with_reconnect(base_url, reconnect_time=reconnect_time)  # type: ignore[attr-defined]
                self.logger.info("Initial page loaded with reconnect strategy.")
            except Exception as e:
                self.logger.warning(f"Reconnect navigation failed, using direct get: {e}")
                self.driver.get(base_url)

            captcha_enabled = self.config.get("browser", "captcha_auto_click", default=True)
            if captcha_enabled:
                try:
                    self.driver.uc_gui_click_captcha()  # type: ignore[attr-defined]
                    self.logger.info("CAPTCHA auto-click attempted.")
                except Exception as e:
                    self.logger.debug(f"CAPTCHA click skipped (none detected or failed): {e}")

            if user_agent:
                self.driver.execute_cdp_cmd(
                    "Network.setUserAgentOverride", {"userAgent": user_agent}
                )

            self.driver.set_page_load_timeout(page_load_timeout)

            if not headless:
                self.driver.maximize_window()

            self.logger.info("Browser engine started successfully.")

        except Exception as e:
            self.logger.critical(f"Failed to start browser engine: {e}")
            self.stop()
            raise

    def stop(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser engine stopped.")
            except Exception as e:
                self.logger.warning(f"Error while stopping browser: {e}")
            finally:
                self.driver = None
