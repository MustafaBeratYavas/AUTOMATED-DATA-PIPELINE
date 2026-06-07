"""Configure application logging for console and file output."""

import logging
import os
import sys
from datetime import datetime
from src.core.config import Config
from src.definitions import ROOT_DIR


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)15s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ColorizedConsoleFormatter(logging.Formatter):
    """Apply ANSI colors to console log levels without affecting file logs."""

    _RESET = "\033[0m"
    _LEVEL_COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Colorize the level name for stream output only."""
        original_levelname = record.levelname
        color = self._LEVEL_COLORS.get(record.levelno)

        if color:
            record.levelname = f"{color}{record.levelname}{self._RESET}"

        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname


class Logger:
    """Idempotent logging bootstrapper used by runtime services."""

    _configured = False

    @staticmethod
    def setup() -> None:
        """Configure global logging handlers once per process."""
        if Logger._configured:
            return

        config = Config()
        log_dir = config.get("paths", "logs_dir", default="logs")

        full_log_path = os.path.join(ROOT_DIR, log_dir)
        os.makedirs(full_log_path, exist_ok=True)

        filename = f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        filepath = os.path.join(full_log_path, filename)

        plain_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        color_formatter = ColorizedConsoleFormatter(LOG_FORMAT, datefmt=DATE_FORMAT)

        file_handler = logging.FileHandler(filepath, encoding="utf-8")
        file_handler.setFormatter(plain_formatter)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(color_formatter)

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)

        # Third-party browser stacks are noisy at INFO level and obscure pipeline events.
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("seleniumbase").setLevel(logging.WARNING)

        Logger._configured = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Return a named logger bound to the configured root handlers."""
        return logging.getLogger(name)
