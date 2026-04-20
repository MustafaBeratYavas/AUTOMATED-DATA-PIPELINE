# -- Pipeline Entry Point --
# Bootstraps all runtime services and launches the ETL batch processor.
# Wires together the dependency graph: Config → Logger → Browser → Services → Processor.

import sys
import os

# Ensure project root is on sys.path for standalone execution
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.config import Config
from src.core.logger import Logger
from src.engine.browser import BrowserEngine
from src.services.database import DatabaseService
from src.services.scraper_service import ScraperService
from src.engine.batch_processor import BatchProcessor
from src.services.search_service import SearchService
from src.services.detail_scraper import DetailScraper
from src.services.seller_extractor import SellerExtractor
from selenium.webdriver.support.ui import WebDriverWait

def main():
    # Initialise logging and configuration singletons
    Logger.setup()
    logger = Logger.get_logger("Main")
    config = Config()

    version = config.get("app", "version", default="0.0.0")
    logger.info(f"Starting Automated Data Pipeline v{version}...")

    try:
        # Open database and browser connections as managed contexts
        with DatabaseService() as db:
            with BrowserEngine() as driver:
                wait = WebDriverWait(driver, config.get("browser", "implicit_wait", default=5))
                
                # Instantiate service-layer collaborators
                search_service = SearchService(driver, wait)
                detail_scraper = DetailScraper(driver)
                seller_extractor = SellerExtractor(driver)
                
                # Wire the scraper orchestrator with all service dependencies
                scraper = ScraperService(
                    driver,
                    search_service,
                    detail_scraper,
                    seller_extractor
                )
                
                # Launch the batch processor with a configurable retry budget
                processor = BatchProcessor(db, scraper)
                processor.run(max_retries=3)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Global fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
