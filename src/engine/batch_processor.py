# -- ETL Batch Processor --
# Orchestrates the core execution loop pulling pending target codes from the
# database queue, resolving product data via the ScraperService, and persisting
# normalized rows handling retries and errors transactionally.

from src.core.logger import Logger
from src.core.exceptions import DatabaseError
from src.models.product import ProductDTO
from src.services.database import DatabaseService
from src.services.scraper_service import ScraperService

class BatchProcessor:
    
    def __init__(
        self,
        database: DatabaseService,
        scraper: ScraperService,
    ) -> None:
        self.database = database
        self.scraper = scraper
        self.logger = Logger.get_logger(__name__)

    def run(self, max_retries: int = 3) -> None:
        # Main sequential processing loop pulling from the persistent DB queue
        self.logger.info("Starting ETL pipeline using Database Task Queue.")

        success_count = 0
        fail_count = 0
        idx = 1

        while True:
            target = self.database.get_pending_product()
            if not target:
                self.logger.info("No pending tasks found. Queue is empty.")
                break

            t_id = target["id"]
            code = target["product_code"]
            err_count = target["error_count"]

            self.logger.info(f"[{idx}] Processing: {code} (Attempt: {err_count + 1})")

            try:
                dto = ProductDTO(code=code)
                self.scraper.process_product(dto)

                rows = dto.to_db_rows()
                self.database.insert_products(rows)

                self.logger.info(f"[{idx}] {code} — {len(rows)} row(s) saved.")
                self.database.update_target_status(t_id, "COMPLETED", err_count)
                success_count += 1

            except DatabaseError as exc:
                # Transitory DB errors (like lock tables) re-enqueue the product immediately
                self.logger.error(f"[{idx}] {code} — DB error: {exc}")
                self.database.update_target_status(t_id, "PENDING", err_count + 1)
                fail_count += 1
            except Exception as exc:
                # Scraper errors are retried up to max_retries before marking as FAILED
                self.logger.error(f"[{idx}] {code} — Scraper error: {exc}")
                new_err_count = err_count + 1
                if new_err_count >= max_retries:
                    self.logger.warning(f"[{idx}] {code} — Max retries reached. Marking FAILED.")
                    self.database.update_target_status(t_id, "FAILED", new_err_count)
                else:
                    self.database.update_target_status(t_id, "PENDING", new_err_count)
                fail_count += 1
            
            idx += 1

        self.logger.info(
            f"Queue processing completed. "
            f"Success: {success_count}, Failed attempts: {fail_count}"
        )
