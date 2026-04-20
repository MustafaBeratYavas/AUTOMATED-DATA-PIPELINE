# -- Scraper Orchestration Service --
# Coordinates the full product resolution pipeline via a three-tier fallback:
#   1. Direct URL access — if a known product page URL exists
#   2. Internal marketplace search — text-based product code lookup
#   3. Google site-scoped search — last-resort discovery via web search engine
# Each strategy delegates to DetailScraper and SellerExtractor for data extraction.

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException
)
from src.core.config import Config
from src.core.logger import Logger
from src.core.exceptions import ScraperError
from src.models.product import ProductDTO
from src.services.search_service import SearchService
from src.services.detail_scraper import DetailScraper
from src.services.seller_extractor import SellerExtractor
from src.utils import string_utils

class ScraperService:

    def __init__(
        self,
        driver: WebDriver,
        search_service: SearchService,
        detail_scraper: DetailScraper,
        seller_extractor: SellerExtractor,
    ) -> None:
        self.driver = driver
        self.config = Config()
        self.logger = Logger.get_logger(__name__)

        # Inject collaborator services for search, detail extraction, and seller parsing
        self.search = search_service
        self.detail = detail_scraper
        self.seller = seller_extractor

    def process_product(self, dto: ProductDTO) -> ProductDTO:
        # Main entry point — attempts all three resolution strategies in priority order
        self.logger.info(f"[{dto.code}] Processing...")

        # Strategy 1: Direct URL navigation if a prior URL is available
        if dto.url and "akakce.com" in dto.url:
            if self._try_direct_url(dto):
                return dto

        # Strategy 2: Internal marketplace search
        try:
            if self.search.search_internal(dto.code):
                if self._analyze_internal_results(dto.code, dto):
                    return dto
        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Internal search error: {exc}")

        # Strategy 3: Google fallback search as last resort
        self.logger.info(f"[{dto.code}] Switching to fallback search.")
        self._try_google_search(dto)

        return dto

    def _try_direct_url(self, dto: ProductDTO) -> bool:
        # Navigate directly to a known product URL and attempt extraction
        self.logger.info(f"[{dto.code}] Source URL found. Attempting direct access.")
        try:
            assert dto.url is not None, "Direct URL called with no URL set"
            self.driver.get(dto.url)
            if self._scrape_and_extract(dto):
                return True
            # Clear invalid URL to prevent reuse in future attempts
            dto.url = None
        except Exception as exc:
            self.logger.warning(f"[{dto.code}] Direct URL failed: {exc}")
            dto.url = None
        return False

    def _analyze_internal_results(self, code: str, dto: ProductDTO) -> bool:
        # Evaluate the search results page and route to the appropriate handler
        try:
            items = self.search.get_result_items()
            if not items:
                return False

            # Validate the first result item has a recognisable title element
            first_item = items[0]
            title_sel = self.config.get("selectors", "search_result_title")
            first_item.find_element(By.CSS_SELECTOR, title_sel)

            # Attempt to extract product category from the results page header
            if not dto.category:
                try:
                    cat_links = self.driver.find_elements(By.CSS_SELECTOR, "p.wbb_v8 a")
                    if cat_links:
                        dto.category = string_utils.clean_text(cat_links[0].text)
                    else:
                        cat_links = self.driver.find_elements(By.XPATH, "//p[contains(text(), 'kategoriye git')]/a")
                        if cat_links:
                            dto.category = string_utils.clean_text(cat_links[0].text)
                except Exception as e:
                    self.logger.debug(f"[{code}] Category extraction failed: {e}")

            # Determine result type: card (compact) vs. detail (full page redirect)
            class_attr = first_item.get_attribute("class") or ""
            is_redirect = "n-p" in class_attr

            if is_redirect:
                return self._handle_card_result(first_item, dto, code)

            return self._handle_detail_result(first_item, dto, code)

        except NoSuchElementException as exc:
            self.logger.error(f"[{code}] Result element not found: {exc}")
            return False
        except ScraperError as exc:
            self.logger.error(f"[{code}] Result analysis error: {exc}")
            return False

    def _handle_card_result(
        self, element: WebElement, dto: ProductDTO, code: str,
    ) -> bool:
        # Process a compact card-layout result — extract data inline without navigation
        self._extract_card_data(element, dto, code)
        return True

    def _handle_detail_result(
        self, element: WebElement, dto: ProductDTO, code: str,
    ) -> bool:
        # Process a detail-type result — click through to the full product page
        link = element.find_element(By.TAG_NAME, "a")
        self.driver.execute_script("arguments[0].click();", link)
        
        # Wait for the detail page content to render
        try:
            page_switch_delays = self.config.get("delays", "page_switch", default=[5.0, 6.0])
            wait_time = page_switch_delays[0] if page_switch_delays else 5.0
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config.get("selectors", "product", "title", default="h1")))
            )
        except TimeoutException:
            self.logger.debug(f"[{code}] Detail page load wait timeout.")

        # Capture the resolved URL for future direct access
        dto.url = self.driver.current_url

        if not self._scrape_and_extract(dto):
            dto.url = None
            return False

        return True

    def _try_google_search(self, dto: ProductDTO) -> None:
        # Execute a Google site-scoped search and iterate through candidate URLs
        try:
            urls = self.search.search_google(dto.code, dto.brand)

            for url in urls:
                try:
                    self.driver.get(url)
                    
                    # Wait for the target page to load before extraction
                    try:
                        google_switch_delays = self.config.get("delays", "google_switch", default=[5.0, 6.0])
                        wait_time = google_switch_delays[0] if google_switch_delays else 5.0
                        WebDriverWait(self.driver, wait_time).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, self.config.get("selectors", "product", "title", default="h1")))
                        )
                    except TimeoutException:
                        self.logger.debug(f"[{dto.code}] Fallback page load wait timeout.")
                        
                    dto.url = self.driver.current_url

                    if not self._scrape_and_extract(dto):
                        dto.url = None
                        continue

                    # Successful extraction — stop iterating candidates
                    return

                except StaleElementReferenceException:
                    continue

        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Google search error: {exc}")

    def _scrape_and_extract(self, dto: ProductDTO) -> bool:
        # Unified extraction pipeline: detail metadata + seller listings
        try:
            if not self.detail.scrape(dto):
                return False
            self.seller.extract_from_detail_page(dto)
            return True
        except ScraperError as exc:
            self.logger.error(f"[{dto.code}] Detail page parsing error: {exc}")
            return False

    def _extract_card_data(
        self, element: WebElement, dto: ProductDTO, code: str,
    ) -> None:
        # Pull title and seller data directly from a card element without navigation
        try:
            dto.url = self.driver.current_url

            title_sel = self.config.get("selectors", "search_result_title")
            dto.title = element.find_element(By.CSS_SELECTOR, title_sel).text.strip()

            # Delegate seller extraction to the card-specific handler
            self.seller.extract_from_card(element, dto)

        except NoSuchElementException as exc:
            self.logger.error(f"[{code}] Card element not found: {exc}")
        except Exception as exc:
            self.logger.error(f"[{code}] Extraction failed: {exc}")
