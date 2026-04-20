# -- Analysis Pipeline Orchestrator --
# Sequentially executes all registered analyzers and logs per-step timing.
# Acts as the main entry point for the analysis module, applying the global
# chart theme before dispatching each analyzer's generate-and-save cycle.

import sys
import os
import logging
import time

# Ensure project root is on sys.path for standalone execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.analysis.core.chart_config import ChartConfig
from src.analysis.core.data_loader import DataLoader
from src.analysis.core.base_analyzer import BaseAnalyzer

from src.analysis.analyzers.correlation import CorrelationAnalyzer
from src.analysis.analyzers.marketplace import MarketplaceAnalyzer
from src.analysis.analyzers.segmentation import SegmentationAnalyzer
from src.analysis.analyzers.volatility import VolatilityAnalyzer
from src.analysis.analyzers.behavior import BehaviorAnalyzer
from src.analysis.analyzers.outlier import OutlierAnalyzer
from src.analysis.analyzers.dashboard import DashboardAnalyzer
from src.analysis.analyzers.advanced import AdvancedAnalyzer

class AnalysisPipeline:

    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._loader = DataLoader()
        # Build the ordered analyzer registry — execution follows registration order
        self._analyzers: list[BaseAnalyzer] = self._build_registry()

    def _build_registry(self) -> list[BaseAnalyzer]:
        # Instantiate all analyzers with the shared DataLoader instance
        return [
            CorrelationAnalyzer(self._loader),
            MarketplaceAnalyzer(self._loader),
            SegmentationAnalyzer(self._loader),
            VolatilityAnalyzer(self._loader),
            BehaviorAnalyzer(self._loader),
            OutlierAnalyzer(self._loader),
            DashboardAnalyzer(self._loader),
            AdvancedAnalyzer(self._loader),
        ]

    def run(self) -> None:
        # Execute each analyzer sequentially with per-step timing and error isolation
        total = len(self._analyzers)
        self._logger.info(f"Starting analysis pipeline with {total} analyzers...")
        pipeline_start = time.time()

        for idx, analyzer in enumerate(self._analyzers, start=1):
            name = analyzer.get_name()
            self._logger.info(f"[{idx}/{total}] Running: {name}")
            step_start = time.time()

            try:
                analyzer.analyze()
                elapsed = time.time() - step_start
                self._logger.info(f"[{idx}/{total}] Completed: {name}  ({elapsed:.1f}s)")
            except Exception as exc:
                # Log and continue — one failed analyzer should not halt the entire pipeline
                self._logger.error(f"[{idx}/{total}] FAILED: {name} — {exc}", exc_info=True)

        total_elapsed = time.time() - pipeline_start
        self._logger.info(f"Pipeline finished in {total_elapsed:.1f}s — charts saved to reports/charts/")

def main() -> None:
    # Configure console-only logging for standalone analysis execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)20s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Apply the global dark theme before any chart rendering
    ChartConfig.apply_theme()

    pipeline = AnalysisPipeline()
    pipeline.run()

if __name__ == "__main__":
    main()
