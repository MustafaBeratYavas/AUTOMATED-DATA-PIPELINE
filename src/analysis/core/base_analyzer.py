# -- Abstract Base Analyzer --
# Template Method pattern for the analysis pipeline: subclasses implement
# analyze() and get_name(), while the base class provides shared utilities
# for chart persistence, subtitle rendering, and watermark annotation.

import os
import logging
from abc import ABC, abstractmethod

import matplotlib.pyplot as plt

from src.analysis.core.data_loader import DataLoader
from src.analysis.core.chart_config import ChartConfig
from src.definitions import ROOT_DIR

class BaseAnalyzer(ABC):

    def __init__(self, data_loader: DataLoader) -> None:
        self._loader = data_loader
        self._output_dir = os.path.join(ROOT_DIR, "reports", "charts")
        self._logger = logging.getLogger(self.__class__.__name__)
        # Ensure the chart output directory exists before any write attempt
        os.makedirs(self._output_dir, exist_ok=True)

    @abstractmethod
    def analyze(self) -> None:
        # Subclass contract: execute the full analysis and generate charts
        ...

    @abstractmethod
    def get_name(self) -> str:
        # Subclass contract: return a human-readable name for logging
        ...

    def _save_chart(self, fig: plt.Figure, filename: str) -> str:
        # Persist a matplotlib figure to disk with standardised dimensions and DPI
        filepath = os.path.join(self._output_dir, filename)

        fig.set_size_inches(ChartConfig.FIGURE_WIDTH, ChartConfig.FIGURE_HEIGHT)
        fig.tight_layout(rect=(0.02, 0.03, 0.98, 0.93))

        fig.savefig(
            filepath,
            dpi=ChartConfig.DPI,
            facecolor=ChartConfig.BG_COLOR,
            edgecolor=ChartConfig.BG_COLOR,
        )
        plt.close(fig)
        self._logger.info(f"Chart saved: {filepath}")
        return filepath

    def _add_subtitle(
        self, fig: plt.Figure, text: str, y: float = 0.94
    ) -> None:
        # Render an italic subtitle centred below the main chart title
        fig.text(
            0.5, y, text,
            ha="center",
            fontsize=ChartConfig.SUBTITLE_SIZE,
            color="#A0A0B0",
            style="italic",
        )

    def _add_watermark(self, fig: plt.Figure) -> None:
        # Stamp a discrete source attribution in the bottom-right corner
        fig.text(
            0.99, 0.01,
            "Source: Marketplace Scraper  |  Feb 2026 vs Apr 2026",
            ha="right", va="bottom",
            fontsize=9, color="#555566", style="italic",
        )
