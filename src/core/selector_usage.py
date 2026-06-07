"""Runtime telemetry for selector configuration usage."""

from __future__ import annotations

import json
import os
from datetime import datetime
from threading import Lock
from typing import Any

from src.definitions import ROOT_DIR


class SelectorUsageTracker:
    """Collect selector reads and DOM query outcomes during a scraping run."""

    _enabled: bool = True
    _output_dir: str = "logs"
    _report_prefix: str = "selector_usage"
    _selectors: dict[str, dict[str, Any]] = {}
    _lock = Lock()

    @classmethod
    def configure(cls, settings: dict[str, Any] | None) -> None:
        """Initialize tracker settings and selector inventory from application config."""
        if not settings:
            return

        usage_config = (
            settings.get("observability", {})
            .get("selector_usage", {})
        )
        cls._enabled = usage_config.get("enabled", True)
        cls._output_dir = usage_config.get("output_dir", settings.get("paths", {}).get("logs_dir", "logs"))
        cls._report_prefix = usage_config.get("report_prefix", "selector_usage")

        with cls._lock:
            cls._selectors = {}
            cls._register_inventory(settings.get("selectors", {}), ("selectors",))

    @classmethod
    def record_config_access(cls, key_path: tuple[str, ...], value: Any) -> None:
        """Record that a selector value was read from configuration."""
        if not cls._enabled or not key_path or key_path[0] != "selectors":
            return

        with cls._lock:
            if isinstance(value, str):
                entry = cls._entry(".".join(key_path), value)
                entry["config_reads"] += 1
            elif isinstance(value, dict):
                cls._register_inventory(value, key_path)

    @classmethod
    def record_query(
        cls,
        key_path: str,
        selector: str,
        *,
        found_count: int = 0,
        context: str = "",
        product_code: str | None = None,
        error: str | None = None,
    ) -> None:
        """Record the outcome of a DOM query made with a configured selector."""
        if not cls._enabled:
            return

        with cls._lock:
            entry = cls._entry(key_path, selector)
            entry["queries"] += 1
            entry["matched_elements"] += max(found_count, 0)
            if found_count > 0:
                entry["hits"] += 1
            else:
                entry["misses"] += 1
            if error:
                entry["errors"] += 1
                entry["last_error"] = error
            if context:
                entry["last_context"] = context
            if product_code:
                entry["last_product_code"] = product_code

    @classmethod
    def write_report(cls) -> str | None:
        """Write selector usage telemetry to disk and return the report path."""
        if not cls._enabled:
            return None

        with cls._lock:
            if not cls._selectors:
                return None
            selectors: list[dict[str, Any]] = []
            for key, stats in sorted(cls._selectors.items()):
                record = dict(stats)
                record["key"] = key
                selectors.append(record)

        unused = [item["key"] for item in selectors if int(item["queries"]) == 0]
        failing = [
            item["key"]
            for item in selectors
            if int(item["queries"]) > 0 and int(item["hits"]) == 0
        ]

        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "total_selectors": len(selectors),
                "queried_selectors": len([item for item in selectors if int(item["queries"]) > 0]),
                "unused_selectors": len(unused),
                "failing_selectors": len(failing),
            },
            "unused_selectors": unused,
            "failing_selectors": failing,
            "selectors": selectors,
        }

        output_dir = os.path.join(ROOT_DIR, cls._output_dir)
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{cls._report_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(output_dir, filename)

        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

        return path

    @classmethod
    def reset(cls) -> None:
        """Clear all runtime counters while keeping the current configuration."""
        with cls._lock:
            for entry in cls._selectors.values():
                entry.update(
                    {
                        "config_reads": 0,
                        "queries": 0,
                        "hits": 0,
                        "misses": 0,
                        "matched_elements": 0,
                        "errors": 0,
                        "last_context": None,
                        "last_product_code": None,
                        "last_error": None,
                    }
                )

    @classmethod
    def _register_inventory(cls, node: dict[str, Any], prefix: tuple[str, ...]) -> None:
        """Register every string selector under the given config subtree."""
        for key, value in node.items():
            next_path = (*prefix, str(key))
            if isinstance(value, str):
                cls._entry(".".join(next_path), value)
            elif isinstance(value, dict):
                cls._register_inventory(value, next_path)

    @classmethod
    def _entry(cls, key_path: str, selector: str) -> dict[str, Any]:
        """Return a mutable telemetry record for a selector key."""
        if key_path not in cls._selectors:
            cls._selectors[key_path] = {
                "selector": selector,
                "config_reads": 0,
                "queries": 0,
                "hits": 0,
                "misses": 0,
                "matched_elements": 0,
                "errors": 0,
                "last_context": None,
                "last_product_code": None,
                "last_error": None,
            }
        else:
            cls._selectors[key_path]["selector"] = selector
        return cls._selectors[key_path]
