# -- Dual-Sink Logging Infrastructure --
# Configures a timestamped file handler and a live stdout stream handler.
# Suppresses noisy third-party loggers (Selenium, urllib3, SeleniumBase)
# to keep pipeline output clean and operationally readable.

import logging
import os
import sys
from datetime import datetime
from src.core.config import Config
from src.definitions import ROOT_DIR

class Logger:

    _configured = False

    @staticmethod
    def setup() -> None:
        # Idempotent initialiser — safe to call multiple times without side effects
        if Logger._configured:
            return

        config = Config()
        log_dir = config.get("paths", "logs_dir", default="logs")

        # Ensure the logging sink directory exists before writing
        full_log_path = os.path.join(ROOT_DIR, log_dir)
        os.makedirs(full_log_path, exist_ok=True)

        # Generate a unique log file per execution run using timestamp
        filename = f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        filepath = os.path.join(full_log_path, filename)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)15s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(filepath, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        # Silence verbose third-party loggers to reduce noise
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("seleniumbase").setLevel(logging.WARNING)

        Logger._configured = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        # Factory method returning a named logger bound to the global configuration
        return logging.getLogger(name)
