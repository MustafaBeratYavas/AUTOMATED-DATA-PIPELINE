"""Coordinate product resolution across direct, internal, and fallback search paths."""

from urllib.parse import urlparse

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.config import Config
from src.core.exceptions import ScraperError
from src.core.logger import Logger
from src.core.selector_usage import SelectorUsageTracker
from src.models.product import ProductDTO
from src.services.detail_scraper import DetailScraper
from src.services.search_service import SearchService
from src.services.seller_extractor import SellerExtractor
from src.utils import string_utils


class ScraperService:
    """Resolve one product code into detail metadata and seller listings."""

    def __init__(
        self,
        driver: WebDriver,
        search_service: SearchService,
        detail_scraper: DetailScraper,
        seller_extractor: SellerExtractor,
    ) -> None:
        """Inject browser and parsing collaborators."""
        self.driver = driver
        self.config = Config()
        self.logger = Logger.get_logger(__name__)

        self.search = search_service
        self.detail = detail_scraper
        self.seller = seller_extractor

    def process_product(self, dto: ProductDTO) -> ProductDTO:
        """Run the product through direct URL, internal search, and Google fallback."""
        dto.code = string_utils.normalize_product_code(dto.code)
        self.logger.info(f"[{dto.code}] Processing...")

        # Known URLs are preferred because they avoid search result ambiguity.
        if dto.url and self._is_internal_product_href(dto.url):
            if self._try_direct_url(dto):
                return dto

        try:
            if self.search.search_internal(dto.code):
                if self._analyze_internal_results(dto.code, dto):
                    return dto
        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Internal search error: {exc}")

        self.logger.info(f"[{dto.code}] Switching to fallback search.")
        self._try_google_search(dto)

        return dto

    def _try_direct_url(self, dto: ProductDTO) -> bool:
        """Attempt extraction from a previously resolved product URL."""
        self.logger.info(f"[{dto.code}] Source URL found. Attempting direct access.")
        try:
            assert dto.url is not None, "Direct URL called with no URL set"
            self.driver.get(dto.url)
            if self._scrape_and_extract(dto):
                return True
            dto.url = None
        except Exception as exc:
            self.logger.warning(f"[{dto.code}] Direct URL failed: {exc}")
            dto.url = None
        return False

    def _analyze_internal_results(self, code: str, dto: ProductDTO) -> bool:
        """Open the first internal result that matches the requested product code."""
        try:
            items = self.search.get_result_items()
            if not items:
                return False

            title_sel = self.config.get("selectors", "search_result_title")
            for item in items:
                try:
                    title = self._extract_result_title(item, title_sel, code)
                    href = self._extract_result_href(item)

                    if not title or not href:
                        continue
                    if not self._is_internal_product_href(href):
                        continue
                    if not string_utils.product_code_matches_text(title, code):
                        continue

                    return self._handle_detail_result(item, dto, code)

                except StaleElementReferenceException:
                    continue

            self.logger.info(f"[{code}] No verified internal result matched product code.")
            return False

        except NoSuchElementException as exc:
            self.logger.error(f"[{code}] Result element not found: {exc}")
            return False
        except ScraperError as exc:
            self.logger.error(f"[{code}] Result analysis error: {exc}")
            return False

    def _extract_result_title(
        self, item: WebElement, title_sel: str, code: str
    ) -> str:
        """Return the visible title for a search result item."""
        try:
            title_element = item.find_element(By.CSS_SELECTOR, title_sel)
            SelectorUsageTracker.record_query(
                "selectors.search_result_title",
                title_sel,
                found_count=1,
                context="ScraperService._analyze_internal_results",
                product_code=code,
            )
            return title_element.text.strip()
        except NoSuchElementException:
            SelectorUsageTracker.record_query(
                "selectors.search_result_title",
                title_sel,
                found_count=0,
                context="ScraperService._analyze_internal_results",
                product_code=code,
                error="NoSuchElementException",
            )
            return ""

    def _extract_result_href(self, item: WebElement) -> str:
        """Return the first anchor href from a search result item."""
        try:
            link = item.find_element(By.TAG_NAME, "a")
            href = link.get_attribute("href")
            return href.strip() if isinstance(href, str) else ""
        except NoSuchElementException:
            return ""

    def _is_internal_product_href(self, href: str) -> bool:
        """Reject external links and Akakce category/search result URLs."""
        if not href:
            return False

        parsed = urlparse(href)
        host = parsed.netloc.lower()

        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return False
        if host and not self._is_akakce_host(host):
            return False
        if not host and not href.startswith("/"):
            return False

        target = f"{parsed.path}?{parsed.query}".lower()
        blocked_markers = (
            "/c/?",
            "/arama",
            "/kategori",
            "q=",
            "redirect",
            "redir",
            "out=",
        )
        if any(marker in target for marker in blocked_markers):
            return False

        return bool(host or href.startswith("/"))

    @staticmethod
    def _is_akakce_host(host: str) -> bool:
        """Return whether a parsed host belongs to Akakce."""
        host_without_port = host.split(":", 1)[0].lower()
        return host_without_port == "akakce.com" or host_without_port.endswith(".akakce.com")

    def _current_url_is_safe_product(self, code: str) -> bool:
        """Validate the active page did not redirect outside trusted Akakce URLs."""
        current_url = self.driver.current_url or ""
        if self._is_internal_product_href(current_url):
            return True

        self.logger.warning(
            f"[{code}] Unsafe or non-product URL rejected after navigation: {current_url}"
        )
        return False

    def _detail_page_matches_code(self, dto: ProductDTO) -> bool:
        """Validate the loaded detail page still represents the requested product code."""
        if string_utils.product_code_matches_text(dto.title, dto.code):
            return True

        current_url = self.driver.current_url or ""
        if string_utils.product_code_matches_text(current_url, dto.code):
            return True

        self.logger.warning(
            f"[{dto.code}] Detail page rejected because product code did not match. "
            f"title={dto.title!r} url={current_url!r}"
        )
        return False

    def _handle_detail_result(
        self, element: WebElement, dto: ProductDTO, code: str,
    ) -> bool:
        """Open a detail search result and scrape the resulting page."""
        link = element.find_element(By.TAG_NAME, "a")
        self.driver.execute_script("arguments[0].click();", link)

        # Akakce can switch templates after click; waiting for the title keeps parsing stable.
        title_sel = self.config.get("selectors", "product", "title", default="h1")
        try:
            page_switch_delays = self.config.get("delays", "page_switch", default=[5.0, 6.0])
            wait_time = page_switch_delays[0] if page_switch_delays else 5.0
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, title_sel))
            )
            SelectorUsageTracker.record_query(
                "selectors.product.title",
                title_sel,
                found_count=1,
                context="ScraperService._handle_detail_result.wait",
                product_code=code,
            )
        except TimeoutException:
            SelectorUsageTracker.record_query(
                "selectors.product.title",
                title_sel,
                found_count=0,
                context="ScraperService._handle_detail_result.wait",
                product_code=code,
                error="TimeoutException",
            )
            self.logger.debug(f"[{code}] Detail page load wait timeout.")

        if not self._current_url_is_safe_product(code):
            dto.url = None
            return False

        dto.url = self.driver.current_url

        if not self._scrape_and_extract(dto):
            dto.url = None
            return False

        return True

    def _try_google_search(self, dto: ProductDTO) -> None:
        """Try site-scoped Google candidates until one yields scrapeable data."""
        try:
            urls = self.search.search_google(dto.code, dto.brand)

            for url in urls:
                try:
                    if not self._is_internal_product_href(url):
                        self.logger.debug(f"[{dto.code}] Fallback URL rejected: {url}")
                        continue

                    self.driver.get(url)

                    title_sel = self.config.get("selectors", "product", "title", default="h1")
                    try:
                        google_switch_delays = self.config.get("delays", "google_switch", default=[5.0, 6.0])
                        wait_time = google_switch_delays[0] if google_switch_delays else 5.0
                        WebDriverWait(self.driver, wait_time).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, title_sel))
                        )
                        SelectorUsageTracker.record_query(
                            "selectors.product.title",
                            title_sel,
                            found_count=1,
                            context="ScraperService._try_google_search.wait",
                            product_code=dto.code,
                        )
                    except TimeoutException:
                        SelectorUsageTracker.record_query(
                            "selectors.product.title",
                            title_sel,
                            found_count=0,
                            context="ScraperService._try_google_search.wait",
                            product_code=dto.code,
                            error="TimeoutException",
                        )
                        self.logger.debug(f"[{dto.code}] Fallback page load wait timeout.")

                    if not self._current_url_is_safe_product(dto.code):
                        dto.url = None
                        continue

                    dto.url = self.driver.current_url

                    if not self._scrape_and_extract(dto):
                        dto.url = None
                        continue

                    return

                except StaleElementReferenceException:
                    continue

        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Google search error: {exc}")

    def _scrape_and_extract(self, dto: ProductDTO) -> bool:
        """Run detail and seller extractors against the current page."""
        try:
            if not self._current_url_is_safe_product(dto.code):
                return False
            if not self.detail.scrape(dto):
                return False
            if not self._detail_page_matches_code(dto):
                return False
            self.seller.extract_from_detail_page(dto)
            return True
        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Detail page parsing error: {exc}")
            return False
