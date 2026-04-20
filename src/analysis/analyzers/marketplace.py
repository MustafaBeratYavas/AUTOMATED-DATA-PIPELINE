# -- Marketplace Competition Analyzer --
# Generates three charts:
#   B1: Cheapest marketplace per category across scrape dates
#   B2: Price aggressiveness score — deviation from category mean
#   B3: Market share evolution — unique product coverage per marketplace

from typing import cast

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig
from src.analysis.utils.formatters import format_price

class MarketplaceAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "B — Marketplace Competition Analysis"

    def analyze(self) -> None:
        mcp = self._loader.load_marketplace_category_prices()
        all_data = self._loader.load_all_products()
        self._generate_cheapest_by_category(mcp)
        self._generate_aggressiveness_score(all_data)
        self._generate_market_share(all_data)

    def _generate_cheapest_by_category(self, mcp: pd.DataFrame) -> None:
        # Identify the cheapest marketplace per category-date pair (min ≥3 products)
        mcp_filtered = mcp[mcp["product_count"] >= 3].copy()

        idx = mcp_filtered.groupby(["product_category", "scraped_at"])["avg_price"].idxmin()
        cheapest = mcp_filtered.loc[idx].copy()

        fig, axes = plt.subplots(1, 3, figsize=ChartConfig.get_figsize(), sharey=False)
        fig.suptitle(
            "Cheapest Marketplace by Category  (Feb vs Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", y=0.97,
        )
        self._add_subtitle(fig, "Minimum average price among marketplaces with ≥3 listed products", y=0.92)

        categories = sorted(cheapest["product_category"].unique())
        date_colors = {"2026-02-18": "#6C5CE7", "2026-04-18": "#00B894"}
        date_labels = {"2026-02-18": "Feb 2026", "2026-04-18": "Apr 2026"}

        for ax_idx, cat in enumerate(categories):
            ax = axes[ax_idx]
            cat_data = cheapest[cheapest["product_category"] == cat].sort_values("scraped_at")

            dates = cat_data["scraped_at"].tolist()
            prices = cat_data["avg_price"].tolist()
            names = cat_data["marketplace"].tolist()

            x = np.arange(len(dates))
            bars = ax.bar(
                x, prices,
                color=[date_colors[d] for d in dates],
                edgecolor="white", linewidth=0.8, width=0.5, zorder=3,
            )

            # Annotate each bar with marketplace name and formatted price
            for bar, price, name in zip(bars, prices, names):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 50,
                    f"{name}\n{format_price(price)}",
                    ha="center", va="bottom",
                    fontsize=11, fontweight="bold", color=ChartConfig.TEXT_COLOR,
                )

            ax.set_xticks(x)
            ax.set_xticklabels([date_labels.get(d, d) for d in dates], fontsize=12)
            ax.set_title(cat, fontsize=16, fontweight="bold", pad=12)
            ax.set_ylabel("Average Price (₺)" if ax_idx == 0 else "", fontsize=12)

        self._add_watermark(fig)
        fig.tight_layout(rect=(0, 0.03, 1, 0.90))
        self._save_chart(fig, "B1_cheapest_marketplace_by_category.png")

    def _generate_aggressiveness_score(self, df: pd.DataFrame) -> None:
        # Compute how far each marketplace deviates from the category average price
        apr_data = df[df["scraped_at"] == "2026-04-18"].copy()
        cat_avg = apr_data.groupby("product_category")["price"].mean()
        apr_data["cat_avg"] = apr_data["product_category"].map(cat_avg)
        apr_data["deviation_pct"] = ((apr_data["price"] - apr_data["cat_avg"]) / apr_data["cat_avg"]) * 100

        mp_score = (
            apr_data.groupby("marketplace")
            .agg(
                avg_deviation=("deviation_pct", "mean"),
                product_count=("product_code", "nunique"),
            )
            .reset_index()
        )
        
        # Filter to marketplaces with sufficient product coverage
        mp_score = cast(pd.DataFrame, mp_score[mp_score["product_count"] >= 5]).sort_values("avg_deviation")
        top = pd.concat([mp_score.head(10), mp_score.tail(5)]).drop_duplicates()
        top = top.sort_values("avg_deviation")

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        # Colour bars green (below average) or red (above average)
        colors = [
            ChartConfig.POSITIVE_COLOR if v < 0 else ChartConfig.NEGATIVE_COLOR
            for v in top["avg_deviation"]
        ]
        bars = ax.barh(top["marketplace"], top["avg_deviation"], color=colors,
                       edgecolor="white", linewidth=0.5, height=0.6, zorder=3)

        for bar, val in zip(bars, top["avg_deviation"]):
            x_pos = bar.get_width() + (1 if val >= 0 else -1)
            ax.text(
                x_pos, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%", va="center",
                ha="left" if val >= 0 else "right",
                fontsize=11, fontweight="bold",
                color=ChartConfig.POSITIVE_COLOR if val < 0 else ChartConfig.NEGATIVE_COLOR,
            )

        ax.axvline(x=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_xlabel("Avg. Deviation from Category Mean (%)", fontsize=14)
        ax.set_title(
            "Marketplace Price Aggressiveness Score  (Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "Negative = cheaper than category average  |  Positive = more expensive")
        self._add_watermark(fig)

        self._save_chart(fig, "B2_marketplace_aggressiveness_score.png")

    def _generate_market_share(self, df: pd.DataFrame) -> None:
        # Compare unique product counts per marketplace across both scrape dates
        share = (
            df.groupby(["marketplace", "scraped_at"])["product_code"]
            .nunique()
            .reset_index(name="products_listed")
        )

        # Focus on the top 12 marketplaces by total product coverage
        top_mp = (
            share.groupby("marketplace")["products_listed"]
            .sum()
            .nlargest(12)
            .index.tolist()
        )
        share = share[share["marketplace"].isin(top_mp)]

        feb = share[share["scraped_at"] == "2026-02-18"].set_index("marketplace")["products_listed"]
        apr = share[share["scraped_at"] == "2026-04-18"].set_index("marketplace")["products_listed"]

        combined = pd.DataFrame({"Feb 2026": feb, "Apr 2026": apr}).fillna(0)
        combined = combined.sort_values("Apr 2026", ascending=True)

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        y = np.arange(len(combined))
        height = 0.35

        ax.barh(y - height / 2, combined["Feb 2026"], height,
                label="Feb 2026", color="#6C5CE7", edgecolor="white", linewidth=0.5, zorder=3)
        ax.barh(y + height / 2, combined["Apr 2026"], height,
                label="Apr 2026", color="#00B894", edgecolor="white", linewidth=0.5, zorder=3)

        ax.set_yticks(y)
        ax.set_yticklabels(combined.index, fontsize=12)
        ax.set_xlabel("Number of Unique Products Listed", fontsize=14)
        ax.set_title(
            "Marketplace Product Coverage  (Feb vs Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=13, loc="lower right")
        self._add_watermark(fig)

        self._save_chart(fig, "B3_marketplace_market_share.png")
