# -- Advanced Analytics Analyzer --
# Generates three charts:
#   H1: Price convergence scatter — CV comparison between scrape dates
#   H2: Listing elasticity — correlation between marketplace count and price change
#   H3: Product lifecycle — price movement segmented by generation tier

from typing import cast

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig
from src.analysis.utils.formatters import format_pct

class AdvancedAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "H — Advanced Analytics"

    def analyze(self) -> None:
        all_data = self._loader.load_all_products()
        price_changes = self._loader.load_price_changes()
        self._generate_convergence(all_data)
        self._generate_elasticity(all_data, price_changes)
        self._generate_lifecycle(all_data, price_changes)

    def _generate_convergence(self, df: pd.DataFrame) -> None:
        # Compare per-product price CV between Feb and Apr to detect convergence/divergence
        def _calc_spread(group: pd.DataFrame) -> float:
            if len(group) < 2:
                return np.nan
            # Coefficient of Variation as a normalised spread metric
            return group["price"].std() / group["price"].mean() * 100

        feb = df[df["scraped_at"] == "2026-02-18"]
        apr = df[df["scraped_at"] == "2026-04-18"]

        feb_cv = feb.groupby(["product_code", "product_category"]).apply(
            _calc_spread, include_groups=False
        ).reset_index(name="cv_feb")
        apr_cv = apr.groupby(["product_code", "product_category"]).apply(
            _calc_spread, include_groups=False
        ).reset_index(name="cv_apr")

        merged = feb_cv.merge(apr_cv, on=["product_code", "product_category"]).dropna()

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        for cat in sorted(merged["product_category"].unique()):
            subset = merged[merged["product_category"] == cat]
            ax.scatter(
                subset["cv_feb"], subset["cv_apr"],
                s=100, alpha=0.7, edgecolors="white", linewidth=0.8,
                color=ChartConfig.CATEGORY_COLORS.get(cat, "#74B9FF"),
                label=cat, zorder=3,
            )

        # Draw the diagonal no-change reference line
        max_val = max(merged["cv_feb"].max(), merged["cv_apr"].max()) + 2
        ax.plot([0, max_val], [0, max_val], "--", color="#555566", linewidth=1.5,
                label="No Change Line")

        # Count products in each convergence zone
        converged = (merged["cv_apr"] < merged["cv_feb"]).sum()
        diverged = (merged["cv_apr"] > merged["cv_feb"]).sum()

        # Shade convergence and divergence regions
        ax.fill_between(
            [0, max_val], [0, max_val], [0, 0],
            color=ChartConfig.POSITIVE_COLOR, alpha=0.05,
        )
        ax.fill_between(
            [0, max_val], [max_val, max_val], [0, max_val],
            color=ChartConfig.NEGATIVE_COLOR, alpha=0.05,
        )

        ax.text(max_val * 0.7, max_val * 0.2, f"Converged\n({converged} products)",
                fontsize=13, color=ChartConfig.POSITIVE_COLOR, ha="center", fontweight="bold")
        ax.text(max_val * 0.2, max_val * 0.8, f"Diverged\n({diverged} products)",
                fontsize=13, color=ChartConfig.NEGATIVE_COLOR, ha="center", fontweight="bold")

        ax.set_xlabel("Price CV in Feb 2026 (%)", fontsize=14)
        ax.set_ylabel("Price CV in Apr 2026 (%)", fontsize=14)
        ax.set_title(
            "Marketplace Price Convergence Analysis",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=12, loc="upper left")
        self._add_subtitle(fig, "Points below diagonal = prices converging across marketplaces")
        self._add_watermark(fig)

        self._save_chart(fig, "H1_price_convergence.png")

    def _generate_elasticity(self, all_data: pd.DataFrame, pc: pd.DataFrame) -> None:
        # Scatter plot testing whether more marketplace listings correlate with price changes
        feb_listings = (
            all_data[all_data["scraped_at"] == "2026-02-18"]
            .groupby("product_code")["marketplace"].nunique()
            .reset_index(name="feb_listings")
        )
        apr_listings = (
            all_data[all_data["scraped_at"] == "2026-04-18"]
            .groupby("product_code")["marketplace"].nunique()
            .reset_index(name="apr_listings")
        )

        merged = pc.merge(feb_listings, on="product_code").merge(apr_listings, on="product_code")
        merged["listing_change"] = merged["apr_listings"] - merged["feb_listings"]

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        for cat in sorted(merged["product_category"].unique()):
            subset = merged[merged["product_category"] == cat]
            ax.scatter(
                subset["apr_listings"], subset["pct_change"],
                s=120, alpha=0.7, edgecolors="white", linewidth=0.8,
                color=ChartConfig.CATEGORY_COLORS.get(cat, "#74B9FF"),
                label=cat, zorder=3,
            )

        # Overlay a linear regression trend line with R² annotation
        if len(merged) > 2:
            slope, intercept, r_val, _, _ = stats.linregress(
                merged["apr_listings"], merged["pct_change"]
            )
            x_line = np.linspace(merged["apr_listings"].min(), merged["apr_listings"].max(), 100)
            ax.plot(x_line, slope * x_line + intercept,
                    color="#FDCB6E", linewidth=2, linestyle="-",
                    label=f"Trend (R² = {r_val**2:.3f})", zorder=2)

        ax.axhline(y=0, color="#555566", linestyle="--", linewidth=0.8)
        ax.set_xlabel("Number of Marketplace Listings (Apr 2026)", fontsize=14)
        ax.set_ylabel("Price Change (%)", fontsize=14)
        ax.set_title(
            "Listing Count vs Price Change  (Elasticity Analysis)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=12, loc="upper right")
        self._add_subtitle(fig, "Do products listed on more marketplaces show different price behavior?")
        self._add_watermark(fig)

        self._save_chart(fig, "H2_listing_vs_price_elasticity.png")

    def _generate_lifecycle(self, all_data: pd.DataFrame, pc: pd.DataFrame) -> None:
        # Segment products by generation tier and compare price movement behaviour
        feb = cast(pd.DataFrame, all_data[all_data["scraped_at"] == "2026-02-18"])

        product_info = feb.drop_duplicates(subset="product_code")[["product_code", "product_name", "product_category"]]

        def _classify_generation(name: str) -> str:
            # Map product naming conventions to generation tiers
            if pd.isna(name):
                return "Unknown"
            name_upper = name.upper()
            for gen in ["V4", "V3 PRO", "35K"]:
                if gen in name_upper:
                    return "Latest Gen"
            for gen in ["V3", "V2 PRO"]:
                if gen in name_upper:
                    return "Current Gen"
            return "Legacy"

        product_info["generation"] = product_info["product_name"].apply(_classify_generation)

        merged = pc.merge(
            product_info[["product_code", "generation"]],
            on="product_code",
        )

        gen_stats = (
            merged.groupby(["product_category", "generation"])["pct_change"]
            .agg(["mean", "count"])
            .reset_index()
        )

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        categories = sorted(gen_stats["product_category"].unique())
        generations = ["Latest Gen", "Current Gen", "Legacy"]
        gen_colors = {"Latest Gen": "#00B894", "Current Gen": "#74B9FF", "Legacy": "#A29BFE"}

        x = np.arange(len(categories))
        width = 0.25

        # Render grouped bars for each generation within each category
        for i, gen in enumerate(generations):
            gen_data = gen_stats[gen_stats["generation"] == gen]
            values = []
            counts = []
            for cat in categories:
                cat_gen = gen_data[gen_data["product_category"] == cat]
                values.append(cat_gen["mean"].values[0] if len(cat_gen) > 0 else 0)
                counts.append(cat_gen["count"].values[0] if len(cat_gen) > 0 else 0)

            bars = ax.bar(
                x + i * width, values, width,
                label=gen, color=gen_colors.get(gen, "#A0A0B0"),
                edgecolor="white", linewidth=0.8, zorder=3,
            )

            # Annotate each bar with formatted percentage and sample size
            for bar, val, cnt in zip(bars, values, counts):
                if cnt > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.3,
                        f"{format_pct(val)}\nn={cnt}",
                        ha="center", va="bottom", fontsize=9,
                        color=ChartConfig.POSITIVE_COLOR if val > 0 else ChartConfig.NEGATIVE_COLOR,
                    )

        ax.axhline(y=0, color="#555566", linestyle="--", linewidth=0.8)
        ax.set_xticks(x + width)
        ax.set_xticklabels(categories, fontsize=14, fontweight="bold")
        ax.set_ylabel("Average Price Change (%)", fontsize=14)
        ax.set_title(
            "Price Movement by Product Generation  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=13, loc="upper left")
        self._add_subtitle(fig, "Latest Gen = V4/V3 Pro/35K  |  Current Gen = V3/V2 Pro  |  Legacy = older models")
        self._add_watermark(fig)

        self._save_chart(fig, "H3_product_lifecycle.png")
