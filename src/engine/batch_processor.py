"""Queue-driven batch orchestration for product scraping jobs."""

from src.core.exceptions import DatabaseError
from src.core.logger import Logger
from src.models.product import ProductDTO
from src.services.database import DatabaseService
from src.services.scraper_service import ScraperService


class BatchProcessor:
    """Pull pending product codes, scrape them, and persist normalized rows."""

    def __init__(
        self,
        database: DatabaseService,
        scraper: ScraperService,
    ) -> None:
        """Store database and scraper collaborators for the run loop."""
        self.database = database
        self.scraper = scraper
        self.logger = Logger.get_logger(__name__)

    def run(self, max_retries: int | None = None) -> None:
        """Process queued products until no pending database tasks remain."""
        if max_retries is None:
            max_retries = int(self.scraper.config.get("scraping", "retries", default=3))

        self.logger.info("Starting queued scraping run.")

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

            self.logger.info(
                f"[attempt={err_count + 1}/{max_retries}] "
                f"code={code} status=started"
            )

            try:
                # A DTO is intentionally created fresh per attempt so stale data is not reused.
                dto = ProductDTO(code=code)
                self.scraper.process_product(dto)

                rows = dto.to_db_rows()
                self.database.insert_products(rows)

                self.logger.info(
                    f"[{idx}] code={code} status=completed rows_saved={len(rows)}"
                )
                self.database.update_target_status(t_id, "COMPLETED", err_count)
                success_count += 1

            except DatabaseError as exc:
                # Database errors are treated as transient because SQLite locks can clear.
                self.logger.error(
                    f"[attempt={err_count + 1}/{max_retries}] "
                    f"code={code} status=retry_pending sequence={idx} "
                    f"reason=database_error error={exc}"
                )
                self.database.update_target_status(t_id, "PENDING", err_count + 1)
                fail_count += 1
            except Exception as exc:
                # Scraper failures are retried with an explicit cap to avoid queue starvation.
                new_err_count = err_count + 1
                self.logger.error(
                    f"[attempt={new_err_count}/{max_retries}] "
                    f"code={code} status=scraper_error sequence={idx} error={exc}"
                )
                if new_err_count >= max_retries:
                    self.logger.warning(
                        f"[{idx}] code={code} status=failed reason=max_retries_reached"
                    )
                    self.database.update_target_status(t_id, "FAILED", new_err_count)
                else:
                    self.database.update_target_status(t_id, "PENDING", new_err_count)
                fail_count += 1

            idx += 1

        self.logger.info(
            f"Queued scraping run completed. "
            f"success_count={success_count}, failed_attempts={fail_count}"
        )
