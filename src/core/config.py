"""Load and expose repository configuration from the YAML settings file."""

import os
import yaml
from typing import Any
from src.definitions import ROOT_DIR
from src.core.selector_usage import SelectorUsageTracker

class Config:
    """Process-wide singleton wrapper around ``config/settings.yaml``."""

    _instance = None
    _settings = {}

    def __new__(cls):
        """Return the cached configuration instance, loading settings once."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Read the YAML manifest into memory."""
        path = os.path.join(ROOT_DIR, "config", "settings.yaml")

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._settings = yaml.safe_load(f)
            SelectorUsageTracker.configure(self._settings)
        except Exception as e:
            raise RuntimeError(f"Failed to load settings from {path}: {e}")

    def get(self, *keys: str, default=None) -> Any:
        """Return a nested configuration value or ``default`` when absent."""
        data = self._settings
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return default
        value = data if data is not None else default
        SelectorUsageTracker.record_config_access(tuple(keys), value)
        return value

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton state for tests that need an isolated config load."""
        cls._instance = None
        cls._settings = {}
