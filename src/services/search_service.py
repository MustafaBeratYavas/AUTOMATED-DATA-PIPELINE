from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from src.core.config import Config
from src.core.logger import Logger
from src.core.exceptions import NetworkError
from src.utils import time_utils

class SearchService:

    def __init__(self, driver: WebDriver, wait: WebDriverWait, config: Config | None = None):
        self.driver = driver
        self.wait = wait
        self.config = config or Config()
        self.logger = Logger.get_logger(__name__)

    def _type_human_like(self, element, text: str) -> None:
        element.clear()
        for char in text:
            element.send_keys(char)
            time_utils.random_sleep(*self.config.get("delays", "typing"))

    def _find_search_box(self, selector: str):
        try:
            return self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            raise NetworkError(f"Search box not clickable: {selector}")

    def check_no_result(self) -> bool:
        try:
            no_res_sel = self.config.get("selectors", "search_no_result")
            elements = self.driver.find_elements(By.CSS_SELECTOR, no_res_sel)
            if elements:
                text = elements[0].text.lower()
                return "bulunamadı" in text or "ilginizi çekebilir" in text
            return False
        except Exception:
            return False

    def search_internal(self, code: str) -> bool:

        base_url = self.config.get("urls", "base", default="https://www.akakce.com")
        current = self.driver.current_url.lower()

        if "akakce.com" not in current or "google" in current:
            self.driver.get(base_url)
            time_utils.random_sleep(1.0, 1.5)

        input_sel = self.config.get("selectors", "search_input")
        try:
            search_box = self._find_search_box(input_sel)
        except NetworkError:
            self.logger.warning(f"[{code}] Search box not found or not clickable.")
            return False

        self._type_human_like(search_box, code)

        time_utils.random_sleep(*self.config.get("delays", "pre_enter"))
        search_box.send_keys(Keys.RETURN)
        time_utils.random_sleep(*self.config.get("delays", "post_search"))

        if self.check_no_result():
            return False

        return True

    def search_google(self, code: str, brand: str = "Razer") -> list[str]:
       
        search_url = self.config.get("urls", "search", default="https://www.google.com")
        self.driver.get(search_url)

        input_sel = "textarea[name='q'], input[name='q']"
        try:
            search_box = self._find_search_box(input_sel)
        except NetworkError:
            self.logger.warning(f"[{code}] Google search box not found.")
            return []

        query_template = self.config.get("scraping", "google_query_format")
        query = query_template.replace("{code}", code).replace("{brand}", brand).strip()
        query = " ".join(query.split())
        self._type_human_like(search_box, query)

        search_box.send_keys(Keys.RETURN)
        time_utils.random_sleep(*self.config.get("delays", "post_search"))

        link_sel = self.config.get("selectors", "google", "result_link")
        links = self.driver.find_elements(By.CSS_SELECTOR, link_sel)

        akakce_urls = []
        for link in links:
            try:
                href = link.get_attribute("href")
                if href and "akakce.com" in href and "google" not in href:
                    akakce_urls.append(href)
            except Exception:
                continue

        return akakce_urls

    def get_result_items(self):
        list_sel = self.config.get("selectors", "search_result_item")
        return self.driver.find_elements(By.CSS_SELECTOR, list_sel)
