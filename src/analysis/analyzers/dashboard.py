# -- Executive Summary Dashboard Analyzer --
# Generates a single multi-panel dashboard (G1) consolidating key metrics:
#   Panel 1: KPI summary (total records, avg prices, overall change)
#   Panel 2: Category trend bar chart
#   Panel 3: Price distribution histogram
#   Panel 4-5: Top 7 price increases and decreases
#   Panel 6: Top 10 cheapest marketplace ranking

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig
from src.analysis.utils.formatters import format_price, format_pct

class DashboardAnalyzer(BaseAnalyzer):

    def get_name(self) -> str:
        return "G — Executive Summary Dashboard"

    def analyze(self) -> None:
        all_data = self._loader.load_all_products()
        price_changes = self._loader.load_price_changes()
        self._generate_dashboard(all_data, price_changes)

    def _generate_dashboard(self, all_data: pd.DataFrame, price_changes: pd.DataFrame) -> None:
        # Compose a 2×3 grid layout combining all executive summary panels
        fig = plt.figure(figsize=ChartConfig.get_figsize())
        gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.30)

        fig.suptitle(
            "Razer Product Price Intelligence  —  Executive Dashboard",
            fontsize=22, fontweight="bold", y=0.98, color=ChartConfig.TEXT_COLOR,
        )
        fig.text(
            0.5, 0.94,
            "Data Period: Feb 18, 2026 → Apr 18, 2026  |  100 Products  |  37 Marketplaces",
            ha="center", fontsize=12, color="#A0A0B0", style="italic",
        )

        # Wire each grid cell to its dedicated panel renderer
        ax1 = fig.add_subplot(gs[0, 0])
        self._panel_kpis(ax1, all_data, price_changes)

        ax2 = fig.add_subplot(gs[0, 1])
        self._panel_category_trend(ax2, price_changes)

        ax3 = fig.add_subplot(gs[0, 2])
        self._panel_price_distribution(ax3, all_data)

        ax4 = fig.add_subplot(gs[1, 0])
        self._panel_top_movers(ax4, price_changes, direction="up")

        ax5 = fig.add_subplot(gs[1, 1])
        self._panel_top_movers(ax5, price_changes, direction="down")

        ax6 = fig.add_subplot(gs[1, 2])
        self._panel_marketplace_ranking(ax6, all_data)

        self._add_watermark(fig)
        self._save_chart(fig, "G1_executive_dashboard.png")

    def _panel_kpis(self, ax: plt.Axes, all_data: pd.DataFrame, pc: pd.DataFrame) -> None:
        # Render key performance indicators as a text-only panel
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("Key Metrics", fontsize=16, fontweight="bold", pad=10)

        feb = all_data[all_data["scraped_at"] == "2026-02-18"]
        apr = all_data[all_data["scraped_at"] == "2026-04-18"]

        kpis = [
            ("Total Records", f"{len(all_data):,}"),
            ("Feb Avg Price", format_price(feb["price"].mean())),
            ("Apr Avg Price", format_price(apr["price"].mean())),
            ("Overall Change", format_pct(pc["pct_change"].mean())),
            ("Products Up", f"{(pc['pct_change'] > 0).sum()} / {len(pc)}"),
            ("Marketplaces", f"{all_data['marketplace'].nunique()}"),
        ]

        for i, (label, value) in enumerate(kpis):
            y = 0.88 - i * 0.15
            ax.text(0.05, y, label, fontsize=12, color="#A0A0B0", va="center")
            ax.text(0.95, y, value, fontsize=14, fontweight="bold",
                    color=ChartConfig.TEXT_COLOR, va="center", ha="right")

    def _panel_category_trend(self, ax: plt.Axes, pc: pd.DataFrame) -> None:
        # Bar chart showing mean price change per category
        cat_mean = pc.groupby("product_category")["pct_change"].mean()
        categories = cat_mean.index.tolist()
        values = cat_mean.values

        colors = [ChartConfig.CATEGORY_COLORS.get(c, "#74B9FF") for c in categories]
        bars = ax.bar(categories, values, color=colors, edgecolor="white",
                      linewidth=0.8, width=0.5, zorder=3)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                format_pct(val), ha="center", va="bottom",
                fontsize=12, fontweight="bold",
                color=ChartConfig.POSITIVE_COLOR if val > 0 else ChartConfig.NEGATIVE_COLOR,
            )

        ax.axhline(y=0, color="#555566", linestyle="--", linewidth=0.8)
        ax.set_title("Avg Price Change by Category", fontsize=16, fontweight="bold", pad=10)
        ax.set_ylabel("Change (%)", fontsize=11)

    def _panel_price_distribution(self, ax: plt.Axes, all_data: pd.DataFrame) -> None:
        # Histogram of Apr 2026 price distribution across all marketplaces
        apr = all_data[all_data["scraped_at"] == "2026-04-18"]["price"].dropna()
        ax.hist(apr, bins=30, color="#6C5CE7", alpha=0.8, edgecolor="white", linewidth=0.5, zorder=3)
        ax.set_title("Apr 2026 Price Distribution", fontsize=16, fontweight="bold", pad=10)
        ax.set_xlabel("Price (₺)", fontsize=11)
        ax.set_ylabel("Frequency", fontsize=11)

    def _panel_top_movers(self, ax: plt.Axes, pc: pd.DataFrame, direction: str) -> None:
        # Horizontal bar chart of the top 7 price movers (up or down)
        if direction == "up":
            top = pc.nlargest(7, "pct_change")
            title = "Top 7 Price Increases"
            bar_color = ChartConfig.POSITIVE_COLOR
        else:
            top = pc.nsmallest(7, "pct_change")
            title = "Top 7 Price Decreases"
            bar_color = ChartConfig.NEGATIVE_COLOR

        top = top.sort_values("pct_change", ascending=True)
        labels = [f"{code[-8:]} ({cat[:3]})" for code, cat in
                  zip(top["product_code"], top["product_category"])]

        ax.barh(range(len(top)), top["pct_change"], color=bar_color,
                edgecolor="white", linewidth=0.5, height=0.6, zorder=3)
        ax.set_yticks(range(len(top)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(x=0, color="#555566", linestyle="--", linewidth=0.8)
        ax.set_title(title, fontsize=16, fontweight="bold", pad=10)
        ax.set_xlabel("Change (%)", fontsize=11)

    def _panel_marketplace_ranking(self, ax: plt.Axes, all_data: pd.DataFrame) -> None:
        # Rank the 10 cheapest marketplaces by average price in Apr 2026
        apr = all_data[all_data["scraped_at"] == "2026-04-18"]
        mp_avg = apr.groupby("marketplace")["price"].mean().nsmallest(10)
        mp_avg = mp_avg.sort_values(ascending=True)

        ax.barh(range(len(mp_avg)), mp_avg.values, color="#74B9FF",
                edgecolor="white", linewidth=0.5, height=0.6, zorder=3)
        ax.set_yticks(range(len(mp_avg)))
        ax.set_yticklabels(mp_avg.index, fontsize=9)
        ax.set_title("Top 10 Cheapest Marketplaces", fontsize=16, fontweight="bold", pad=10)
        ax.set_xlabel("Avg Price (₺)", fontsize=11)
