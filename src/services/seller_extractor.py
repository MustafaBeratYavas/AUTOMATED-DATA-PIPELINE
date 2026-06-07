"""Extract seller and price data from product detail pages."""

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from src.core.config import Config
from src.core.logger import Logger
from src.core.selector_usage import SelectorUsageTracker
from src.models.product import ProductDTO
from src.utils import string_utils


class SellerExtractor:
    """Parse marketplace sellers from Akakce product detail pages."""

    def __init__(self, driver: WebDriver, config: Config | None = None) -> None:
        """Store browser and configuration dependencies."""
        self.driver = driver
        self.config = config or Config()
        self.logger = Logger.get_logger(__name__)

    def extract_from_detail_page(self, dto: ProductDTO) -> None:
        """Populate seller rows from a full product detail page."""
        sellers = []
        try:
            not_found_elements = self.driver.find_elements(By.XPATH, "//*[contains(., 'Fiyat bulunamad')]")
            if not_found_elements:
                dto.sellers = []
                dto.price = None
                return

            product_sel = self.config.get("selectors", "product")
            all_items = self._collect_detail_seller_items(product_sel, dto.code)

            for item in all_items:
                seller = self._parse_detail_seller(item, product_sel)
                if seller:
                    sellers.append(seller)

        except Exception as e:
            self.logger.debug(f"Detail seller extraction error: {e}")

        dto.sellers = sellers

        if dto.sellers:
            dto.price = min(s["price"] for s in dto.sellers)

    def _collect_detail_seller_items(
        self, product_sel: dict, product_code: str
    ) -> list[WebElement]:
        """Collect seller rows from every known detail-page seller container."""
        container_sel = product_sel.get("sellers_list", "ul#PL, ul.pl_v9")
        containers = self.driver.find_elements(By.CSS_SELECTOR, container_sel)
        SelectorUsageTracker.record_query(
            "selectors.product.sellers_list",
            container_sel,
            found_count=len(containers),
            context="SellerExtractor.extract_from_detail_page",
            product_code=product_code,
        )

        item_sel = product_sel.get("sellers_list_item", "li")
        all_items: list[WebElement] = []
        seen_item_keys: set[str] = set()
        for container in containers:
            try:
                self._extend_unique_elements(
                    all_items,
                    container.find_elements(By.CSS_SELECTOR, item_sel),
                    seen_item_keys,
                )
            except Exception as exc:
                self.logger.debug(f"Seller container item lookup failed: {exc}")

        SelectorUsageTracker.record_query(
            "selectors.product.sellers_list_item",
            item_sel,
            found_count=len(all_items),
            context="SellerExtractor.extract_from_detail_page",
            product_code=product_code,
        )

        alt_sel = product_sel.get("sellers_alt_item", "li.w_v8")
        alt_items = self.driver.find_elements(By.CSS_SELECTOR, alt_sel)
        SelectorUsageTracker.record_query(
            "selectors.product.sellers_alt_item",
            alt_sel,
            found_count=len(alt_items),
            context="SellerExtractor.extract_from_detail_page",
            product_code=product_code,
        )
        self._extend_unique_elements(all_items, alt_items, seen_item_keys)

        return all_items

    def _extend_unique_elements(
        self,
        target: list[WebElement],
        candidates: list[WebElement],
        seen_keys: set[str],
    ) -> None:
        """Append each DOM row once without collapsing equal seller-price offers."""
        for candidate in candidates:
            key = self._element_identity(candidate)
            if key in seen_keys:
                continue
            target.append(candidate)
            seen_keys.add(key)

    @staticmethod
    def _element_identity(element: WebElement) -> str:
        """Return a stable Selenium element identity for duplicate DOM protection."""
        selenium_id = getattr(element, "id", None)
        return selenium_id if isinstance(selenium_id, str) else str(id(element))

    def _parse_detail_seller(self, item: WebElement, product_sel: dict) -> dict | None:
        """Extract one seller from a detail-page list item."""
        price_sel = ""
        wrapper_sel = ""
        try:
            price_sel = product_sel.get("seller_price", "span.pt_v8")
            price_el = item.find_element(By.CSS_SELECTOR, price_sel)
            SelectorUsageTracker.record_query(
                "selectors.product.seller_price",
                price_sel,
                found_count=1,
                context="SellerExtractor._parse_detail_seller",
            )
            price = string_utils.clean_price(price_el.text)

            name = "Unknown"
            try:
                wrapper_sel = product_sel.get(
                    "seller_name_wrapper", "span.v_v8, div.v_v8, b.v_v8"
                )
                name_wrapper = item.find_element(By.CSS_SELECTOR, wrapper_sel)
                SelectorUsageTracker.record_query(
                    "selectors.product.seller_name_wrapper",
                    wrapper_sel,
                    found_count=1,
                    context="SellerExtractor._parse_detail_seller",
                )

                # Akakce may expose seller identity as image alt text or visible text.
                name_imgs = name_wrapper.find_elements(By.TAG_NAME, "img")
                if name_imgs:
                    name = name_imgs[0].get_attribute("alt") or "Unknown"
                else:
                    bold_tags = name_wrapper.find_elements(By.TAG_NAME, "b")
                    if bold_tags:
                        name = bold_tags[0].text.strip()
                    else:
                        name = name_wrapper.text.strip()
            except NoSuchElementException as e:
                SelectorUsageTracker.record_query(
                    "selectors.product.seller_name_wrapper",
                    wrapper_sel,
                    found_count=0,
                    context="SellerExtractor._parse_detail_seller",
                    error="NoSuchElementException",
                )
                self.logger.debug(f"Seller name element missing: {e}")

            name = string_utils.clean_text(name)

            if price and name:
                return {"name": name, "price": price}

        except Exception as e:
            if price_sel:
                SelectorUsageTracker.record_query(
                    "selectors.product.seller_price",
                    price_sel,
                    found_count=0,
                    context="SellerExtractor._parse_detail_seller",
                    error=type(e).__name__,
                )
            self.logger.debug(f"Error parsing detail seller: {e}")

        return None
