# -- Cross-Category Price Correlation Analyzer --
# Generates two charts:
#   A1: Pearson correlation heatmap showing how price changes co-move across categories
#   A2: Side-by-side mean vs. median price change comparison per category

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns  # type: ignore

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig
from src.analysis.utils.formatters import format_pct

class CorrelationAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "A — Price Correlation Analysis"

    def analyze(self) -> None:
        price_changes = self._loader.load_price_changes()
        self._generate_heatmap(price_changes)
        self._generate_category_comparison(price_changes)

    def _generate_heatmap(self, df: pd.DataFrame) -> None:
        # Pivot product-level price changes into a category matrix and compute Pearson correlation
        pivot = df.pivot_table(
            index="product_code",
            columns="product_category",
            values="pct_change",
        )
        corr = pivot.corr(method="pearson")

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())
        # Mask the upper triangle to avoid redundant mirror display
        mask = np.triu(np.ones_like(corr, dtype=bool), k=1)

        sns.heatmap(
            corr, mask=mask, annot=True, fmt=".2f",
            cmap="RdYlGn", center=0,
            linewidths=2, linecolor=ChartConfig.BG_COLOR,
            vmin=-1, vmax=1,
            annot_kws={"size": 22, "weight": "bold"},
            cbar_kws={"shrink": 0.8, "label": "Pearson Correlation"},
            ax=ax,
        )

        ax.set_title(
            "Cross-Category Price Change Correlation Matrix",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "Pearson correlation of product-level % price changes  (Feb → Apr 2026)")
        self._add_watermark(fig)

        ax.set_xticklabels(ax.get_xticklabels(), fontsize=14,fontweight="bold")
        ax.set_yticklabels(ax.get_yticklabels(), fontsize=14, fontweight="bold")

        self._save_chart(fig, "A1_correlation_heatmap.png")

    def _generate_category_comparison(self, df: pd.DataFrame) -> None:
        # Aggregate mean/median/std statistics per category for bar chart comparison
        cat_stats = (
            df.groupby("product_category")["pct_change"]
            .agg(["mean", "median", "std", "count"])
            .reset_index()
        )

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        categories = cat_stats["product_category"].tolist()
        x = np.arange(len(categories))
        width = 0.30

        # Render mean and median bars side by side with category-specific colours
        bars_mean = ax.bar(
            x - width / 2, cat_stats["mean"], width,
            label="Mean Change (%)",
            color=[ChartConfig.CATEGORY_COLORS.get(c, "#74B9FF") for c in categories],
            edgecolor="white", linewidth=0.8, zorder=3,
        )
        bars_median = ax.bar(
            x + width / 2, cat_stats["median"], width,
            label="Median Change (%)",
            color=[ChartConfig.CATEGORY_COLORS.get(c, "#74B9FF") for c in categories],
            alpha=0.55, edgecolor="white", linewidth=0.8, zorder=3,
        )

        # Annotate bar values with colour-coded percentage labels
        for bar, val in zip(bars_mean, cat_stats["mean"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                format_pct(val), ha="center", va="bottom",
                fontsize=13, fontweight="bold",
                color=ChartConfig.POSITIVE_COLOR if val > 0 else ChartConfig.NEGATIVE_COLOR,
            )
        for bar, val in zip(bars_median, cat_stats["median"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                format_pct(val), ha="center", va="bottom",
                fontsize=12, color="#A0A0B0",
            )

        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=14, fontweight="bold")
        ax.set_ylabel("Price Change (%)", fontsize=14)
        ax.set_title(
            "Average Price Change by Category  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.axhline(y=0, color="#555566", linewidth=1, linestyle="--")
        ax.legend(fontsize=12)

        self._add_subtitle(fig, f"Product-level matched comparison (same product × same marketplace)")
        self._add_watermark(fig)

        self._save_chart(fig, "A2_category_price_change_comparison.png")
