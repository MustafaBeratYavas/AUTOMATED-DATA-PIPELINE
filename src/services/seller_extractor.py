# -- Seller Extraction Engine --
# Parses seller/marketplace listings from both detail pages and card-layout results.
# Handles two distinct DOM structures (full detail vs. compact card) and applies
# deduplication to eliminate repeated seller-price pairs from paginated listings.

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from src.core.config import Config
from src.core.logger import Logger
from src.models.product import ProductDTO
from src.utils import string_utils

class SellerExtractor:

    # Static mapping of numeric marketplace IDs to human-readable names
    _SELLER_NAME_MAP = {
        "11070": "n11",
        "11168": "Amazon",
        "11075": "Hepsiburada",
        "11116": "Trendyol",
        "335": "Boyner",
        "407": "Vatan Bilgisayar",
        "40":  "Teknosa",
        "24":  "MediaMarkt",
        "11124": "Çiçeksepeti",
        "11169": "PttAVM",
    }

    def __init__(self, driver: WebDriver, config: Config | None = None) -> None:
        self.driver = driver
        self.config = config or Config()
        self.logger = Logger.get_logger(__name__)

    # -- Detail Page Extraction --

    def extract_from_detail_page(self, dto: ProductDTO) -> None:
        # Parse all seller listings from a full product detail page
        sellers = []
        try:
            # Check for "price not found" indicator before attempting extraction
            not_found_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Fiyat bulunamadı')]")
            if not_found_elements:
                dto.sellers = []
                dto.price = 0.0
                return

            # Click "show more prices" buttons to reveal the full seller list
            self._expand_all_sellers()

            # Locate the primary seller list container
            product_sel = self.config.get("selectors", "product")
            container_sel = product_sel.get("sellers_list", "ul#PL, ul.pl_v9")
            uls = self.driver.find_elements(By.CSS_SELECTOR, container_sel)

            # Collect list items from the primary container
            all_items = []
            if uls:
                item_sel = product_sel.get("sellers_list_item", "li")
                all_items.extend(uls[0].find_elements(By.CSS_SELECTOR, item_sel))

            # Also check for alternative-layout seller items outside the main list
            alt_sel = product_sel.get("sellers_alt_item", "li.w_v8")
            all_items.extend(self.driver.find_elements(By.CSS_SELECTOR, alt_sel))

            # Parse each list item into a seller dict
            for item in all_items:
                seller = self._parse_detail_seller(item, product_sel)
                if seller:
                    sellers.append(seller)

        except Exception as e:
            self.logger.debug(f"Detail seller extraction error: {e}")

        # Remove duplicate seller-price pairs from paginated results
        dto.sellers = self._deduplicate(sellers)

        # Set the DTO price to the minimum across all extracted sellers
        if dto.sellers:
            dto.price = min(s["price"] for s in dto.sellers)

    def _expand_all_sellers(self) -> None:
        # Iteratively click "load more" buttons to reveal all paginated sellers
        button_xpaths = [
            "//*[contains(text(), 'Daha fazla fiyat gör')]",
            "//*[contains(text(), 'Tüm fiyatları gör')]"
        ]
        
        max_clicks = 10
        clicks = 0
        wait = WebDriverWait(self.driver, 3)
        
        while clicks < max_clicks:
            try:
                # Scan for any visible "load more" button
                button = None
                for xpath in button_xpaths:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for el in elements:
                        if el.is_displayed():
                            button = el
                            break
                    if button:
                        break
                
                # No more expand buttons found — all sellers are visible
                if not button:
                    break
                
                # Scroll the button into viewport before clicking
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                
                # Attempt native click, fall back to JS click if intercepted
                try:
                    button = wait.until(EC.element_to_be_clickable(button))
                    button.click()
                except TimeoutException:
                    self.driver.execute_script("arguments[0].click();", button)
                except Exception:
                    self.driver.execute_script("arguments[0].click();", button)
                    
                # Wait for the DOM to update after the click
                try:
                    wait.until(EC.staleness_of(button))
                except TimeoutException:
                    pass
                
                clicks += 1
                self.logger.debug(f"Clicked load prices button (Click {clicks}/{max_clicks})")
            except Exception as e:
                self.logger.debug(f"Error expanding sellers list: {e}")
                break

    # -- Card Layout Extraction --

    def extract_from_card(self, element: WebElement, dto: ProductDTO) -> None:
        # Parse seller data from a compact search result card element
        sellers = []
        container_sel = self.config.get("selectors", "card", "sellers_container")
        link_sel = self.config.get("selectors", "card", "seller_link")

        try:
            container = element.find_element(By.CSS_SELECTOR, container_sel)
            links = container.find_elements(By.CSS_SELECTOR, link_sel)

            for lnk in links:
                seller = self._parse_card_seller(lnk)
                if seller:
                    sellers.append(seller)

        except NoSuchElementException as e:
            self.logger.debug(f"Sellers container not found in card: {e}")

        dto.sellers = sellers

        if sellers:
            # Use the cheapest seller price as the canonical product price
            dto.price = min(s["price"] for s in sellers)
        else:
            # Fallback: extract standalone price from the search result card
            try:
                price_sel = self.config.get("selectors", "search_result_price")
                price_text = element.find_element(By.CSS_SELECTOR, price_sel).text
                dto.price = string_utils.clean_price(price_text)
            except NoSuchElementException as e:
                self.logger.debug(f"Price missing in search result: {e}")

    # -- Private Parsing Helpers --

    def _parse_detail_seller(self, item: WebElement, product_sel: dict) -> dict | None:
        # Extract seller name and price from a detail page list item
        try:
            # Parse the price element first — skip this item if unavailable
            price_sel = product_sel.get("seller_price", "span.pt_v8")
            price_el = item.find_element(By.CSS_SELECTOR, price_sel)
            price = string_utils.clean_price(price_el.text)

            name = "Unknown"
            try:
                # Resolve seller name from image alt-text or bold text inside the wrapper
                wrapper_sel = product_sel.get(
                    "seller_name_wrapper", "span.v_v8, div.v_v8, b.v_v8"
                )
                name_wrapper = item.find_element(By.CSS_SELECTOR, wrapper_sel)

                # Priority: img alt attribute > bold tag text > wrapper text
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
                self.logger.debug(f"Seller name element missing: {e}")

            # Sanitise the extracted seller name
            name = string_utils.clean_text(name)

            if price and name:
                return {"name": name, "price": price}

        except Exception as e:
            self.logger.debug(f"Error parsing detail seller: {e}")

        return None

    def _parse_card_seller(self, link_element: WebElement) -> dict | None:
        # Extract seller name and price from a card-layout seller link
        try:
            price_sel = self.config.get("selectors", "card", "seller_price")
            price_el = link_element.find_element(By.CSS_SELECTOR, price_sel)
            price = string_utils.clean_price(price_el.text)

            name = "Unknown"
            img_sel = self.config.get("selectors", "card", "seller_name_img")
            text_sel = self.config.get("selectors", "card", "seller_name_text")

            # Try image alt-text first, then fall back to text element
            imgs = link_element.find_elements(By.CSS_SELECTOR, img_sel)
            if imgs:
                name = imgs[0].get_attribute("alt") or "Unknown"
            else:
                texts = link_element.find_elements(By.CSS_SELECTOR, text_sel)
                if texts:
                    name = texts[0].text

            seller_name = string_utils.clean_text(name)

            # Resolve numeric marketplace IDs to readable names via the static map
            if seller_name.isdigit():
                seller_name = self._SELLER_NAME_MAP.get(seller_name, f"ID:{seller_name}")
            elif seller_name.lower() == "unknown":
                seller_name = "Bilinmeyen Satıcı"

            # Only return valid sellers with a positive price
            if price > 0:
                return {"name": seller_name, "price": price}

        except Exception as e:
            self.logger.debug(f"Error parsing card seller: {e}")

        return None

    def _deduplicate(self, sellers: list[dict]) -> list[dict]:
        # Remove duplicate seller entries by (name, price) composite key
        unique = []
        seen: set = set()
        for s in sellers:
            key = (s["name"], s["price"])
            if key not in seen:
                unique.append(s)
                seen.add(key)
        return unique
