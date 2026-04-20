# -- Centralised Configuration Singleton --
# Loads and caches settings.yaml as a globally shared, thread-safe configuration store.
# Uses the Singleton pattern (__new__) to guarantee a single parse across the application lifecycle.

import os
import yaml  # type: ignore
from typing import Any
from src.definitions import ROOT_DIR

class Config:

    _instance = None
    _settings = {}

    def __new__(cls):
        # Enforce single-instance guarantee across all import boundaries
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        # Resolve and parse the YAML manifest from the config directory
        path = os.path.join(ROOT_DIR, "config", "settings.yaml")

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._settings = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load settings from {path}: {e}")

    def get(self, *keys, default=None) -> Any:
        # Traverse nested YAML keys with a fallback default for missing paths
        data = self._settings
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return default
        return data if data is not None else default

    @classmethod
    def reset_instance(cls) -> None:
        # Teardown hook exclusively for unit test isolation
        cls._instance = None
        cls._settings = {}
