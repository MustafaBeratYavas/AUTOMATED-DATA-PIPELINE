# -- Price Segmentation & Clustering Analyzer --
# Generates two charts:
#   C1: K-Means scatter plot segmenting products into price tiers
#   C2: Average price movement per segment to reveal tier-specific trends

from typing import cast

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig
from src.analysis.utils.formatters import format_pct

class SegmentationAnalyzer(BaseAnalyzer):

    _N_CLUSTERS: int = 4
    _SEGMENT_NAMES: dict[int, str] = {}

    def get_name(self) -> str:
        return "C — Price Segmentation & Clustering"

    def analyze(self) -> None:
        price_changes = self._loader.load_price_changes()
        clustered = self._fit_clusters(price_changes)
        self._generate_scatter(clustered)
        self._generate_segment_movement(clustered)

    def _fit_clusters(self, df: pd.DataFrame) -> pd.DataFrame:
        # Standardise features and run K-Means to assign price tier labels
        features = df[["feb_avg_price", "pct_change"]].dropna()
        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        kmeans = KMeans(n_clusters=self._N_CLUSTERS, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        df = cast(pd.DataFrame, df.loc[features.index]).copy()
        df["cluster"] = labels

        # Map cluster indices to human-readable tier names based on centroid price
        centroids = kmeans.cluster_centers_
        centroid_prices = scaler.inverse_transform(centroids)[:, 0]
        sorted_clusters = np.argsort(centroid_prices)

        name_map = {}
        tier_names = ["Budget", "Mid-Range", "Premium", "Ultra-Premium"]
        for rank, cluster_id in enumerate(sorted_clusters):
            name_map[cluster_id] = tier_names[min(rank, len(tier_names) - 1)]

        df["segment"] = df["cluster"].map(name_map)
        self._SEGMENT_NAMES = name_map
        return df

    def _generate_scatter(self, df: pd.DataFrame) -> None:
        # Plot each product as a point coloured by its assigned price segment
        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        segment_colors = {
            "Budget": "#00B894",
            "Mid-Range": "#74B9FF",
            "Premium": "#FDCB6E",
            "Ultra-Premium": "#FD79A8",
        }

        for segment, group in df.groupby("segment"):
            ax.scatter(
                group["feb_avg_price"], group["pct_change"],
                s=120, alpha=0.8, edgecolors="white", linewidth=0.8,
                label=f"{segment}  (n={len(group)})",
                color=segment_colors.get(segment, "#A29BFE"),
                zorder=3,
            )

        ax.axhline(y=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_xlabel("Average Price in Feb 2026 (₺)", fontsize=14)
        ax.set_ylabel("Price Change Feb → Apr (%)", fontsize=14)
        ax.set_title(
            "Product Price Segments  (K-Means Clustering)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )

        # Overlay category markers (●▲■) on each point for dual-dimension encoding
        for _, row in df.iterrows():
            cat_marker = {"Kulaklık": "●", "Mouse": "▲", "Klavye": "■"}.get(row["product_category"], "◆")
            ax.annotate(
                cat_marker,
                (row["feb_avg_price"], row["pct_change"]),
                fontsize=7, ha="center", va="center", alpha=0.6,
            )

        ax.legend(fontsize=13, loc="upper left", framealpha=0.9)
        self._add_subtitle(fig, "Each point = one product  |  ● Kulaklık  ▲ Mouse  ■ Klavye")
        self._add_watermark(fig)

        self._save_chart(fig, "C1_price_clusters_scatter.png")

    def _generate_segment_movement(self, df: pd.DataFrame) -> None:
        # Aggregate and visualise average price change per K-Means segment
        seg_stats = (
            df.groupby("segment")["pct_change"]
            .agg(["mean", "count"])
            .reset_index()
            .sort_values("mean", ascending=True)
        )

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        segment_colors = {
            "Budget": "#00B894",
            "Mid-Range": "#74B9FF",
            "Premium": "#FDCB6E",
            "Ultra-Premium": "#FD79A8",
        }

        colors = [segment_colors.get(s, "#A29BFE") for s in seg_stats["segment"]]
        bars = ax.bar(
            seg_stats["segment"], seg_stats["mean"],
            color=colors, edgecolor="white", linewidth=0.8, width=0.5, zorder=3,
        )

        # Annotate each bar with the formatted percentage and sample size
        for bar, val, cnt in zip(bars, seg_stats["mean"], seg_stats["count"]):
            y_offset = 0.5 if val >= 0 else -1.5
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + y_offset,
                f"{format_pct(val)}\n(n={cnt})",
                ha="center", va="bottom" if val >= 0 else "top",
                fontsize=13, fontweight="bold",
                color=ChartConfig.POSITIVE_COLOR if val > 0 else ChartConfig.NEGATIVE_COLOR,
            )

        ax.axhline(y=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_ylabel("Average Price Change (%)", fontsize=14)
        ax.set_xlabel("Price Segment", fontsize=14)
        ax.set_title(
            "Price Movement by Product Segment  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "K-Means segmentation based on Feb 2026 price level and 2-month price change")
        self._add_watermark(fig)

        self._save_chart(fig, "C2_segment_price_movement.png")
