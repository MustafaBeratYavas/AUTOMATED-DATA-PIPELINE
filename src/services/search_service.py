"""Search helpers for internal Akakce lookup and Google fallback discovery."""

from urllib.parse import urlparse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.config import Config
from src.core.exceptions import NetworkError
from src.core.logger import Logger
from src.core.selector_usage import SelectorUsageTracker
from src.utils import string_utils, time_utils


class SearchService:
    """Drive search forms and return candidate result elements or URLs."""

    def __init__(self, driver: WebDriver, wait: WebDriverWait, config: Config | None = None):
        """Bind browser primitives and optionally inject test configuration."""
        self.driver = driver
        self.wait = wait
        self.config = config or Config()
        self.logger = Logger.get_logger(__name__)

    def _type_human_like(self, element: WebElement, text: str) -> None:
        """Type text with configured per-character delay."""
        element.clear()
        for char in text:
            element.send_keys(char)
            time_utils.random_sleep(*self.config.get("delays", "typing"))

    def _find_search_box(
        self, selector: str, key_path: str = "selectors.search_input"
    ) -> WebElement:
        """Wait for a clickable search box or raise a domain network error."""
        try:
            element = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            SelectorUsageTracker.record_query(key_path, selector, found_count=1, context="SearchService._find_search_box")
            return element
        except TimeoutException:
            SelectorUsageTracker.record_query(
                key_path,
                selector,
                found_count=0,
                context="SearchService._find_search_box",
                error="TimeoutException",
            )
            raise NetworkError(f"Search box not clickable: {selector}")

    def _type_and_validate_search_text(self, search_box: WebElement, code: str) -> bool:
        """Type the product code and verify the DOM value before submitting."""
        expected_code = string_utils.normalize_product_code(code)
        max_attempts = int(
            self.config.get("scraping", "search_input_validation_attempts", default=2)
        )

        for attempt in range(1, max_attempts + 1):
            self._type_human_like(search_box, expected_code)
            actual_value = (search_box.get_attribute("value") or "").strip()

            if actual_value == expected_code:
                return True

            if (
                string_utils.canonical_product_code(actual_value)
                == string_utils.canonical_product_code(expected_code)
            ):
                return True

            self.logger.warning(
                f"[{expected_code}] Search input validation failed. "
                f"attempt={attempt}/{max_attempts} actual={actual_value!r}"
            )
            search_box.clear()

        return False

    def check_no_result(self) -> bool:
        """Return whether the current page signals no usable search result."""
        try:
            no_res_sel = self.config.get("selectors", "search_no_result")
            elements = self.driver.find_elements(By.CSS_SELECTOR, no_res_sel)
            SelectorUsageTracker.record_query(
                "selectors.search_no_result",
                no_res_sel,
                found_count=len(elements),
                context="SearchService.check_no_result",
            )
            if elements:
                text = elements[0].text.lower()
                no_result_terms = self.config.get(
                    "scraping",
                    "no_result_terms",
                    default=["bulunamad", "ilginizi"],
                )
                return any(term.lower() in text for term in no_result_terms)
            return False
        except Exception:
            return False

    def search_internal(self, code: str) -> bool:
        """Submit a product code to the native marketplace search page."""
        target_code = string_utils.normalize_product_code(code)
        base_url = self.config.get("urls", "base", default="https://www.akakce.com")
        current = self.driver.current_url.lower()

        if "akakce.com" not in current or "google" in current:
            self.driver.get(base_url)
            time_utils.random_sleep(
                *self.config.get("delays", "base_navigation", default=[1.0, 1.5])
            )

        input_sel = self.config.get("selectors", "search_input")
        try:
            search_box = self._find_search_box(input_sel, "selectors.search_input")
        except NetworkError:
            self.logger.warning(f"[{target_code}] Search box not found or not clickable.")
            return False

        if not self._type_and_validate_search_text(search_box, target_code):
            self.logger.warning(f"[{target_code}] Search aborted because input validation failed.")
            return False

        time_utils.random_sleep(*self.config.get("delays", "pre_enter"))
        search_box.send_keys(Keys.RETURN)
        time_utils.random_sleep(*self.config.get("delays", "post_search"))

        if self.check_no_result():
            return False

        return True

    def search_google(self, code: str, brand: str = "Razer") -> list[str]:
        """Return Akakce URLs discovered through a site-scoped Google query."""
        target_code = string_utils.normalize_product_code(code)
        search_url = self.config.get("urls", "search", default="https://www.google.com")
        self.driver.get(search_url)

        input_sel = "textarea[name='q'], input[name='q']"
        try:
            search_box = self._find_search_box(input_sel, "selectors.search_input")
        except NetworkError:
            self.logger.warning(f"[{target_code}] Google search box not found.")
            return []

        query_template = self.config.get("scraping", "google_query_format")
        query = query_template.replace("{code}", target_code).replace("{brand}", brand).strip()
        query = " ".join(query.split())
        self._type_human_like(search_box, query)

        search_box.send_keys(Keys.RETURN)
        time_utils.random_sleep(*self.config.get("delays", "post_search"))

        link_sel = self.config.get("selectors", "google", "result_link")
        links = self.driver.find_elements(By.CSS_SELECTOR, link_sel)
        SelectorUsageTracker.record_query(
            "selectors.google.result_link",
            link_sel,
            found_count=len(links),
            context="SearchService.search_google",
            product_code=code,
        )

        akakce_urls = []
        for link in links:
            try:
                href = link.get_attribute("href")
                if isinstance(href, str) and self._is_akakce_url(href):
                    akakce_urls.append(href)
            except Exception:
                continue

        return akakce_urls

    @staticmethod
    def _is_akakce_url(url: str | None) -> bool:
        """Return whether a URL belongs to Akakce and is not a Google redirect."""
        if not url:
            return False

        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":", 1)[0]
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return False
        if host != "akakce.com" and not host.endswith(".akakce.com"):
            return False

        target = f"{parsed.path}?{parsed.query}".lower()
        return "google" not in target

    def get_result_items(self):
        """Return product result elements from the current internal search page."""
        list_sel = self.config.get("selectors", "search_result_item")
        items = self.driver.find_elements(By.CSS_SELECTOR, list_sel)
        SelectorUsageTracker.record_query(
            "selectors.search_result_item",
            list_sel,
            found_count=len(items),
            context="SearchService.get_result_items",
        )
        return items
