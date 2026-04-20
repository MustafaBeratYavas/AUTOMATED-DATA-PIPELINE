# -- Marketplace Behavior Profiling Analyzer --
# Generates two charts:
#   E1: Entry/exit analysis — tracks new, exited, and persistent marketplaces
#   E2: Pricing tier classification — clusters marketplaces by avg price and coverage

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig

class BehaviorAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "E — Marketplace Behavior Profiling"

    def analyze(self) -> None:
        all_data = self._loader.load_all_products()
        self._generate_entry_exit(all_data)
        self._generate_pricing_tier(all_data)

    def _generate_entry_exit(self, df: pd.DataFrame) -> None:
        # Classify marketplaces as New Entry, Exited, or Persistent between scrape dates
        feb_mp = set(df[df["scraped_at"] == "2026-02-18"]["marketplace"].unique())
        apr_mp = set(df[df["scraped_at"] == "2026-04-18"]["marketplace"].unique())

        new_entries = apr_mp - feb_mp
        exits = feb_mp - apr_mp
        persistent = feb_mp & apr_mp

        # Count unique products per marketplace per date for change calculation
        feb_counts = (
            df[df["scraped_at"] == "2026-02-18"]
            .groupby("marketplace")["product_code"].nunique()
        )
        apr_counts = (
            df[df["scraped_at"] == "2026-04-18"]
            .groupby("marketplace")["product_code"].nunique()
        )

        # Build a consolidated change dataset across all marketplace states
        change_data = []
        for mp in persistent:
            feb_c = feb_counts.get(mp, 0)
            apr_c = apr_counts.get(mp, 0)
            change_data.append({
                "marketplace": mp,
                "feb_count": feb_c,
                "apr_count": apr_c,
                "change": apr_c - feb_c,
                "status": "Persistent",
            })
        for mp in new_entries:
            apr_c = apr_counts.get(mp, 0)
            change_data.append({
                "marketplace": mp,
                "feb_count": 0,
                "apr_count": apr_c,
                "change": apr_c,
                "status": "New Entry",
            })
        for mp in exits:
            feb_c = feb_counts.get(mp, 0)
            change_data.append({
                "marketplace": mp,
                "feb_count": feb_c,
                "apr_count": 0,
                "change": -feb_c,
                "status": "Exited",
            })

        change_df = pd.DataFrame(change_data).sort_values("change", ascending=True)

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        status_colors = {
            "New Entry": "#00B894",
            "Exited": "#FF7675",
            "Persistent": "#74B9FF",
        }

        colors = [status_colors.get(s, "#A0A0B0") for s in change_df["status"]]
        bars = ax.barh(
            range(len(change_df)), change_df["change"],
            color=colors, edgecolor="white", linewidth=0.5, height=0.65, zorder=3,
        )

        ax.set_yticks(range(len(change_df)))
        ax.set_yticklabels(change_df["marketplace"], fontsize=10)

        # Annotate bars with change value and status tag
        for bar, val, status in zip(bars, change_df["change"], change_df["status"]):
            x_pos = bar.get_width() + (0.3 if val >= 0 else -0.3)
            label = f"{val:+d}" + (" [NEW]" if status == "New Entry" else " [EXIT]" if status == "Exited" else "")
            ax.text(
                x_pos, bar.get_y() + bar.get_height() / 2,
                label, va="center",
                ha="left" if val >= 0 else "right",
                fontsize=10, fontweight="bold", color=ChartConfig.TEXT_COLOR,
            )

        ax.axvline(x=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_xlabel("Change in Unique Products Listed", fontsize=14)
        ax.set_title(
            "Marketplace Entry/Exit & Listing Changes  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )

        from matplotlib.patches import Patch
        legend_items = [Patch(facecolor=c, label=s) for s, c in status_colors.items()]
        ax.legend(handles=legend_items, fontsize=12, loc="lower right")
        self._add_subtitle(fig, "[NEW] = newly entered marketplace  |  [EXIT] = exited marketplace")
        self._add_watermark(fig)

        self._save_chart(fig, "E1_marketplace_entry_exit.png")

    def _generate_pricing_tier(self, df: pd.DataFrame) -> None:
        # Classify marketplaces into Budget/Mid-Range/Premium tiers via percentile boundaries
        apr_data = df[df["scraped_at"] == "2026-04-18"].copy()

        mp_stats = (
            apr_data.groupby("marketplace")
            .agg(
                avg_price=("price", "mean"),
                product_count=("product_code", "nunique"),
                listing_count=("id", "count"),
            )
            .reset_index()
        )
        # Require minimum product coverage for tier classification
        mp_stats = mp_stats[mp_stats["product_count"] >= 3]

        # Define tier boundaries at the 33rd and 66th price percentiles
        p33 = mp_stats["avg_price"].quantile(0.33)
        p66 = mp_stats["avg_price"].quantile(0.66)
        mp_stats["tier"] = pd.cut(
            mp_stats["avg_price"],
            bins=[-np.inf, p33, p66, np.inf],
            labels=["Budget", "Mid-Range", "Premium"],
        )

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        tier_colors = {
            "Budget": "#00B894",
            "Mid-Range": "#74B9FF",
            "Premium": "#FD79A8",
        }

        # Bubble size scales with total listing count for visual weight
        for tier, group in mp_stats.groupby("tier", observed=True):
            ax.scatter(
                group["product_count"], group["avg_price"],
                s=group["listing_count"] * 3,
                alpha=0.7, edgecolors="white", linewidth=0.8,
                color=tier_colors.get(tier, "#A0A0B0"),
                label=f"{tier} Tier",
                zorder=3,
            )
            # Label each bubble with its marketplace name
            for _, row in group.iterrows():
                ax.annotate(
                    row["marketplace"],
                    (row["product_count"], row["avg_price"]),
                    fontsize=9, ha="left", va="bottom",
                    xytext=(5, 5), textcoords="offset points",
                    color=ChartConfig.TEXT_COLOR, alpha=0.85,
                )

        ax.set_xlabel("Unique Products Listed", fontsize=14)
        ax.set_ylabel("Average Price (₺)", fontsize=14)
        ax.set_title(
            "Marketplace Pricing Tier Classification  (Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=13, loc="upper left")
        self._add_subtitle(fig, "Bubble size = total listings  |  Tier boundaries at 33rd and 66th percentile")
        self._add_watermark(fig)

        self._save_chart(fig, "E2_marketplace_pricing_tier.png")
