"""Application entry point for the scraping pipeline."""

import sys
import os

# Support direct file execution while keeping package imports stable.
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config
from src.core.logger import Logger
from src.core.selector_usage import SelectorUsageTracker
from src.engine.browser import BrowserEngine
from src.services.database import DatabaseService
from src.services.scraper_service import ScraperService
from src.engine.batch_processor import BatchProcessor
from src.services.search_service import SearchService
from src.services.detail_scraper import DetailScraper
from src.services.seller_extractor import SellerExtractor
from selenium.webdriver.support.ui import WebDriverWait

def main() -> None:
    """Wire runtime services and execute the batch processor."""
    Logger.setup()
    logger = Logger.get_logger("Main")
    config = Config()

    version = config.get("app", "version", default="0.0.0")
    logger.info(f"Starting Automated Data Pipeline v{version}...")

    try:
        # Context managers keep database and browser lifecycles tied to one run.
        with DatabaseService() as db:
            with BrowserEngine() as driver:
                wait = WebDriverWait(driver, config.get("browser", "implicit_wait", default=5))

                search_service = SearchService(driver, wait)
                detail_scraper = DetailScraper(driver)
                seller_extractor = SellerExtractor(driver)

                scraper = ScraperService(
                    driver,
                    search_service,
                    detail_scraper,
                    seller_extractor
                )

                processor = BatchProcessor(db, scraper)
                processor.run(max_retries=3)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Global fatal error: {e}")
        sys.exit(1)
    finally:
        report_path = SelectorUsageTracker.write_report()
        if report_path:
            logger.info(f"Selector usage report written: {report_path}")

if __name__ == "__main__":
    main()
