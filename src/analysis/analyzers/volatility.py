# -- Price Volatility Analyzer --
# Generates three charts:
#   D1: Box plots showing price distribution shifts per category (Feb vs Apr)
#   D2: Top 15 most volatile products by Coefficient of Variation (CV)
#   D3: Price spread change — identifies convergence vs. divergence trends

from typing import cast

import pandas as pd
import matplotlib.pyplot as plt

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig

class VolatilityAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "D — Price Volatility Analysis"

    def analyze(self) -> None:
        all_data = self._loader.load_all_products()
        self._generate_box_plot(all_data)
        self._generate_cv_chart(all_data)
        self._generate_spread_change(all_data)

    def _generate_box_plot(self, df: pd.DataFrame) -> None:
        # Render side-by-side box plots per category showing median, IQR, and outliers
        fig, axes = plt.subplots(1, 3, figsize=ChartConfig.get_figsize(), sharey=False)
        fig.suptitle(
            "Price Distribution by Category  (Feb vs Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", y=0.97,
        )
        self._add_subtitle(fig, "Box plots showing median, IQR, and outlier prices across all marketplaces", y=0.92)

        categories = sorted(df["product_category"].unique())
        date_colors = {"2026-02-18": "#6C5CE7", "2026-04-18": "#00B894"}

        for ax_idx, cat in enumerate(categories):
            ax = axes[ax_idx]
            cat_data = df[df["product_category"] == cat]

            dates = sorted(cat_data["scraped_at"].unique())
            box_data = [cat_data[cat_data["scraped_at"] == d]["price"].dropna() for d in dates]

            bp = ax.boxplot(
                box_data, positions=range(len(dates)),
                widths=0.4, patch_artist=True,
                medianprops={"color": "white", "linewidth": 2},
                whiskerprops={"color": ChartConfig.TEXT_COLOR},
                capprops={"color": ChartConfig.TEXT_COLOR},
                flierprops={"marker": "o", "markersize": 4, "alpha": 0.5,
                            "markerfacecolor": "#FF7675"},
            )

            # Apply date-specific colours to each box
            for patch, date in zip(bp["boxes"], dates):
                patch.set_facecolor(date_colors.get(date, "#74B9FF"))
                patch.set_alpha(0.7)
                patch.set_edgecolor("white")

            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels(["Feb 2026", "Apr 2026"], fontsize=12)
            ax.set_title(cat, fontsize=16, fontweight="bold", pad=12)
            if ax_idx == 0:
                ax.set_ylabel("Price (₺)", fontsize=13)

        self._add_watermark(fig)
        fig.tight_layout(rect=(0, 0.03, 1, 0.90))
        self._save_chart(fig, "D1_price_volatility_by_category.png")

    def _generate_cv_chart(self, df: pd.DataFrame) -> None:
        # Rank products by Coefficient of Variation (std/mean) across marketplaces
        apr_data = df[df["scraped_at"] == "2026-04-18"].copy()

        product_cv = (
            apr_data.groupby(["product_code", "product_category"])["price"]
            .agg(["mean", "std", "count"])
            .reset_index()
        )
        # Require at least 3 marketplace listings for statistical significance
        product_cv = cast(pd.DataFrame, product_cv[product_cv["count"] >= 3]).copy()
        product_cv["cv"] = (product_cv["std"] / product_cv["mean"]) * 100

        top_volatile = product_cv.nlargest(15, "cv").sort_values("cv", ascending=True)

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        colors = [
            ChartConfig.CATEGORY_COLORS.get(cat, "#74B9FF")
            for cat in top_volatile["product_category"]
        ]
        bars = ax.barh(
            range(len(top_volatile)), top_volatile["cv"],
            color=colors, edgecolor="white", linewidth=0.5, height=0.6, zorder=3,
        )

        ax.set_yticks(range(len(top_volatile)))
        labels = [f"{code} ({cat})" for code, cat in
                  zip(top_volatile["product_code"], top_volatile["product_category"])]
        ax.set_yticklabels(labels, fontsize=10)

        for bar, val in zip(bars, top_volatile["cv"]):
            ax.text(
                bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=11, fontweight="bold",
                color=ChartConfig.TEXT_COLOR,
            )

        ax.set_xlabel("Coefficient of Variation (%)", fontsize=14)
        ax.set_title(
            "Top 15 Most Price-Volatile Products  (Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "CV = Std Dev / Mean across marketplaces  |  Higher = more inconsistent pricing")

        from matplotlib.patches import Patch
        legend_items = [
            Patch(facecolor=c, label=cat)
            for cat, c in ChartConfig.CATEGORY_COLORS.items()
        ]
        ax.legend(handles=legend_items, fontsize=12, loc="lower right")
        self._add_watermark(fig)

        self._save_chart(fig, "D2_coefficient_of_variation.png")

    def _generate_spread_change(self, df: pd.DataFrame) -> None:
        # Compute per-product price spread (max - min) and track its change over time
        def _spread(group: pd.DataFrame) -> pd.Series:
            return pd.Series({
                "spread": group["price"].max() - group["price"].min(),
                "product_category": group["product_category"].iloc[0],
            })

        feb = df[df["scraped_at"] == "2026-02-18"]
        apr = df[df["scraped_at"] == "2026-04-18"]

        feb_spread = feb.groupby("product_code").apply(_spread, include_groups=False).reset_index()
        apr_spread = apr.groupby("product_code").apply(_spread, include_groups=False).reset_index()

        merged = feb_spread.merge(apr_spread, on="product_code", suffixes=("_feb", "_apr"))
        merged["spread_change"] = merged["spread_apr"].astype(float) - merged["spread_feb"].astype(float)
        merged = merged.sort_values("spread_change")

        # Show the 10 most narrowed and 10 most widened spread products
        top_narrow = merged.head(10)
        top_widen = merged.tail(10)
        display_df = pd.concat([top_narrow, top_widen])

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        # Green = spread narrowed (convergence), Red = spread widened (divergence)
        colors = [
            ChartConfig.POSITIVE_COLOR if v < 0 else ChartConfig.NEGATIVE_COLOR
            for v in display_df["spread_change"]
        ]
        bars = ax.barh(
            range(len(display_df)), display_df["spread_change"],
            color=colors, edgecolor="white", linewidth=0.5, height=0.6, zorder=3,
        )

        ax.set_yticks(range(len(display_df)))
        ax.set_yticklabels(display_df["product_code"], fontsize=10)

        for bar, val in zip(bars, display_df["spread_change"]):
            x_pos = bar.get_width() + (100 if val >= 0 else -100)
            ax.text(
                x_pos, bar.get_y() + bar.get_height() / 2,
                f"{'₺'}{val:+,.0f}", va="center",
                ha="left" if val >= 0 else "right",
                fontsize=10, fontweight="bold", color=ChartConfig.TEXT_COLOR,
            )

        ax.axvline(x=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_xlabel("Price Spread Change (₺)", fontsize=14)
        ax.set_title(
            "Marketplace Price Spread Change  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "Negative = spread narrowed (price convergence)  |  Positive = spread widened")
        self._add_watermark(fig)

        self._save_chart(fig, "D3_price_spread_change.png")
