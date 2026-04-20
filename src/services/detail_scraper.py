# -- Product Detail Scraper --
# Extracts product metadata (title, price, category) from a live detail page DOM.
# Uses CSS selectors loaded from the centralised YAML configuration to decouple
# extraction logic from DOM structure changes.

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from src.core.config import Config
from src.core.logger import Logger
from src.models.product import ProductDTO
from src.utils import string_utils, time_utils

class DetailScraper:

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver
        self.config = Config()
        self.logger = Logger.get_logger(__name__)

    def scrape(self, dto: ProductDTO) -> bool:
        # Orchestrate the extraction of all detail page fields into the DTO
        product_sel = self.config.get("selectors", "product")
        if not product_sel:
            self.logger.warning("Product selectors not configured — skipping detail scrape")
            return False

        # Extract each field independently to maximise partial data recovery
        self._extract_title(dto, product_sel)
        self._extract_price(dto, product_sel)
        self._extract_category(dto, product_sel)

        # Introduce a randomised delay to throttle request cadence
        delay_range = self.config.get("delays", "post_detail", default=[0.5, 1.5])
        if random.random() > 0.3:
            time_utils.random_sleep(*delay_range)

        return True

    def _extract_title(self, dto: ProductDTO, selectors: dict) -> None:
        # Pull the product title from the first matching heading element
        title_sel = selectors.get("title", "h1")
        elements = self.driver.find_elements(By.CSS_SELECTOR, title_sel)
        if elements:
            dto.title = elements[0].text.strip()

    def _extract_price(self, dto: ProductDTO, selectors: dict) -> None:
        # Extract and normalise the primary price display value
        price_sel = selectors.get("price", "span.pt_v8")
        elements = self.driver.find_elements(By.CSS_SELECTOR, price_sel)
        if elements:
            dto.price = string_utils.clean_price(elements[0].text)

    def _extract_category(self, dto: ProductDTO, selectors: dict) -> None:
        # Derive the product category from breadcrumb navigation (penultimate crumb)
        crumb_sel = selectors.get("category_crumb", "nav ol li a")
        crumbs = self.driver.find_elements(By.CSS_SELECTOR, crumb_sel)
        if len(crumbs) >= 2:
            # The second-to-last breadcrumb typically contains the product category
            dto.category = crumbs[-2].text.strip()
        elif crumbs:
            # Fallback to the only available breadcrumb
            dto.category = crumbs[0].text.strip()
