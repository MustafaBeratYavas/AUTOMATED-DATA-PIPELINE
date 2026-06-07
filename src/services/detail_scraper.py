"""Extract product metadata from Akakce product detail pages."""

import random

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from src.core.config import Config
from src.core.logger import Logger
from src.core.selector_usage import SelectorUsageTracker
from src.models.product import ProductDTO
from src.utils import string_utils, time_utils


class DetailScraper:
    """Populate product title, price, and category from the current browser page."""

    def __init__(self, driver: WebDriver) -> None:
        """Keep the active WebDriver and shared configuration."""
        self.driver = driver
        self.config = Config()
        self.logger = Logger.get_logger(__name__)

    def scrape(self, dto: ProductDTO) -> bool:
        """Extract configured detail-page fields into ``dto``."""
        product_sel = self.config.get("selectors", "product")
        if not product_sel:
            self.logger.warning("Product selectors are not configured; skipping detail scrape.")
            return False

        self._extract_title(dto, product_sel)
        self._extract_price(dto, product_sel)
        self._extract_category(dto, product_sel)

        # A partial delay preserves human-like pacing without slowing every test path.
        delay_range = self.config.get("delays", "post_detail", default=[0.5, 1.5])
        raw_delay_probability = self.config.get(
            "scraping", "detail_delay_probability", default=0.7
        )
        delay_probability = (
            float(raw_delay_probability)
            if isinstance(raw_delay_probability, int | float | str)
            else 0.7
        )
        if random.random() < delay_probability:
            time_utils.random_sleep(*delay_range)

        return True

    def _extract_title(self, dto: ProductDTO, selectors: dict) -> None:
        """Set the DTO title when a configured heading is available."""
        title_sel = selectors.get("title", "h1")
        elements = self.driver.find_elements(By.CSS_SELECTOR, title_sel)
        SelectorUsageTracker.record_query(
            "selectors.product.title",
            title_sel,
            found_count=len(elements),
            context="DetailScraper._extract_title",
            product_code=dto.code,
        )
        if elements:
            dto.title = elements[0].text.strip()

    def _extract_price(self, dto: ProductDTO, selectors: dict) -> None:
        """Set the DTO price from the first matching product price element."""
        price_sel = selectors.get("price", "span.pt_v8")
        elements = self.driver.find_elements(By.CSS_SELECTOR, price_sel)
        SelectorUsageTracker.record_query(
            "selectors.product.price",
            price_sel,
            found_count=len(elements),
            context="DetailScraper._extract_price",
            product_code=dto.code,
        )
        if elements:
            dto.price = string_utils.clean_price(elements[0].text)

    def _extract_category(self, dto: ProductDTO, selectors: dict) -> None:
        """Infer the product category from breadcrumb navigation."""
        crumb_sel = selectors.get("category_crumb", "nav ol li a")
        crumbs = self.driver.find_elements(By.CSS_SELECTOR, crumb_sel)
        SelectorUsageTracker.record_query(
            "selectors.product.category_crumb",
            crumb_sel,
            found_count=len(crumbs),
            context="DetailScraper._extract_category",
            product_code=dto.code,
        )
        if len(crumbs) >= 2:
            # The penultimate breadcrumb is the category on Akakce detail pages.
            dto.category = crumbs[-2].text.strip()
        elif crumbs:
            dto.category = crumbs[0].text.strip()
