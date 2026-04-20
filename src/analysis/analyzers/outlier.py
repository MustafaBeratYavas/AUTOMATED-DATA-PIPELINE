# -- Outlier & Anomaly Detection Analyzer --
# Generates two charts:
#   F1: IQR-based outlier box plot with annotated extreme products
#   F2: Z-score scatter plot separating normal vs. anomalous price changes

import pandas as pd
import matplotlib.pyplot as plt

from src.analysis.core.base_analyzer import BaseAnalyzer
from src.analysis.core.chart_config import ChartConfig

class OutlierAnalyzer(BaseAnalyzer):

    # Z-score threshold beyond which a product is flagged as anomalous
    _ZSCORE_THRESHOLD: float = 2.0

    def get_name(self) -> str:
        return "F — Outlier & Anomaly Detection"

    def analyze(self) -> None:
        price_changes = self._loader.load_price_changes()
        self._generate_outlier_boxplot(price_changes)
        self._generate_zscore_distribution(price_changes)

    def _generate_outlier_boxplot(self, df: pd.DataFrame) -> None:
        # Render box plots per category with IQR fences and annotated outlier labels
        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        categories = sorted(df["product_category"].unique())
        box_data = [
            df[df["product_category"] == cat]["pct_change"].dropna()
            for cat in categories
        ]

        bp = ax.boxplot(
            box_data, positions=range(len(categories)),
            widths=0.45, patch_artist=True,
            medianprops={"color": "white", "linewidth": 2.5},
            whiskerprops={"color": ChartConfig.TEXT_COLOR, "linewidth": 1.5},
            capprops={"color": ChartConfig.TEXT_COLOR, "linewidth": 1.5},
            flierprops={
                "marker": "D", "markersize": 8, "alpha": 0.9,
                "markerfacecolor": "#FF7675", "markeredgecolor": "white",
            },
        )

        # Apply category-specific colours to each box
        for patch, cat in zip(bp["boxes"], categories):
            patch.set_facecolor(ChartConfig.CATEGORY_COLORS.get(cat, "#74B9FF"))
            patch.set_alpha(0.7)
            patch.set_edgecolor("white")
            patch.set_linewidth(1.5)

        # Identify and annotate outliers beyond 1.5× IQR fences
        for cat_idx, cat in enumerate(categories):
            cat_data = df[df["product_category"] == cat]["pct_change"].dropna()
            Q1 = cat_data.quantile(0.25)
            Q3 = cat_data.quantile(0.75)
            IQR = Q3 - Q1
            lower_fence = Q1 - 1.5 * IQR
            upper_fence = Q3 + 1.5 * IQR

            outliers = df[
                (df["product_category"] == cat) &
                ((df["pct_change"] < lower_fence) | (df["pct_change"] > upper_fence))
            ]

            for _, row in outliers.iterrows():
                ax.annotate(
                    row["product_code"][-8:],
                    (cat_idx, row["pct_change"]),
                    fontsize=8, ha="left", va="center",
                    xytext=(12, 0), textcoords="offset points",
                    color="#FD79A8", alpha=0.9,
                    arrowprops={"arrowstyle": "->", "color": "#FD79A8", "alpha": 0.5},
                )

        ax.axhline(y=0, color="#555566", linewidth=1, linestyle="--")
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, fontsize=14, fontweight="bold")
        ax.set_ylabel("Price Change (%)", fontsize=14)
        ax.set_title(
            "Outlier Detection: Price Change Distribution  (Feb → Apr 2026)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        self._add_subtitle(fig, "IQR method  |  Diamonds = outliers beyond 1.5× IQR fences")
        self._add_watermark(fig)

        self._save_chart(fig, "F1_outlier_detection_boxplot.png")

    def _generate_zscore_distribution(self, df: pd.DataFrame) -> None:
        # Compute Z-scores and classify products as normal or anomalous
        df = df.copy()
        mean_change = df["pct_change"].mean()
        std_change = df["pct_change"].std()
        df["z_score"] = (df["pct_change"] - mean_change) / std_change
        df["is_anomaly"] = df["z_score"].abs() > self._ZSCORE_THRESHOLD

        fig, ax = plt.subplots(figsize=ChartConfig.get_figsize())

        normal = df[~df["is_anomaly"]]
        anomaly = df[df["is_anomaly"]]

        # Plot normal products as blue circles
        ax.scatter(
            range(len(normal)), normal["z_score"].values,
            c="#74B9FF", s=60, alpha=0.6, edgecolors="white", linewidth=0.5,
            label=f"Normal (n={len(normal)})", zorder=3,
        )
        # Plot anomalous products as red diamonds with labels
        ax.scatter(
            [len(normal) + i for i in range(len(anomaly))],
            anomaly["z_score"].values,
            c="#FF7675", s=100, alpha=0.9, edgecolors="white", linewidth=0.8,
            marker="D", label=f"Anomaly (n={len(anomaly)})", zorder=4,
        )

        # Annotate each anomaly with its product code and category abbreviation
        for i, (_, row) in enumerate(anomaly.iterrows()):
            cat_short = row["product_category"][:3].upper()
            ax.annotate(
                f"{row['product_code'][-8:]}\n({cat_short})",
                (len(normal) + i, row["z_score"]),
                fontsize=8, ha="center", va="bottom",
                xytext=(0, 10), textcoords="offset points",
                color="#FD79A8",
            )

        # Draw threshold boundary lines at ±2σ
        ax.axhline(y=self._ZSCORE_THRESHOLD, color="#FF7675", linewidth=1.5,
                   linestyle="--", label=f"Threshold (±{self._ZSCORE_THRESHOLD}σ)")
        ax.axhline(y=-self._ZSCORE_THRESHOLD, color="#FF7675", linewidth=1.5, linestyle="--")
        ax.axhline(y=0, color="#555566", linewidth=0.8)

        ax.set_xlabel("Products (sorted by Z-score group)", fontsize=14)
        ax.set_ylabel("Z-Score of Price Change", fontsize=14)
        ax.set_title(
            "Z-Score Anomaly Detection  (Price Change Distribution)",
            fontsize=ChartConfig.TITLE_SIZE, fontweight="bold", pad=20,
        )
        ax.legend(fontsize=12, loc="upper left")
        self._add_subtitle(
            fig,
            f"Z-score threshold = ±{self._ZSCORE_THRESHOLD}σ  "
            f"|  Mean change = {mean_change:.1f}%  |  Std = {std_change:.1f}%"
        )
        self._add_watermark(fig)

        self._save_chart(fig, "F2_zscore_distribution.png")
