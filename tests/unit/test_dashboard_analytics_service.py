"""Unit tests for dashboard metric calculations."""

import unittest

from src.web.schemas import ProductPriceRow
from src.web.services.dashboard_analytics_service import DashboardAnalyticsService


class TestDashboardAnalyticsService(unittest.TestCase):
    """Validate marketplace, product spread, and heatmap calculations."""

    def setUp(self):
        """Create a metric service with representative dashboard rows."""
        self.service = DashboardAnalyticsService()
        self.rows = [
            self._row("P1", "Mouse", "Trendyol", 100.0),
            self._row("P1", "Mouse", "Trendyol", 105.0),
            self._row("P1", "Mouse", "Amazon Türkiye", 120.0),
            self._row("P1", "Mouse", "Hepsiburada", 140.0),
            self._row("P2", "Kulaklık", "Trendyol", 250.0),
            self._row("P2", "Kulaklık", "Amazon Türkiye", 200.0),
            self._row("P2", "Kulaklık", "n11", 220.0),
            self._row("P3", "Mouse", None, None),
        ]

    def _row(
        self,
        code: str,
        category: str,
        marketplace: str | None,
        price: float | None,
    ) -> ProductPriceRow:
        """Return one product row fixture."""
        return ProductPriceRow(
            product_code=code,
            product_name=f"{code} Product",
            product_category=category,
            marketplace=marketplace,
            price=price,
            product_url=f"https://www.akakce.com/{code.lower()}.html",
            scraped_at="2026-06-06",
        )

    def test_summary_counts_rows_and_distinct_entities(self):
        summary = self.service.summary(self.rows)

        self.assertEqual(summary["total_rows"], 8)
        self.assertEqual(summary["priced_rows"], 7)
        self.assertEqual(summary["product_count"], 3)
        self.assertEqual(summary["marketplace_count"], 4)
        self.assertEqual(summary["category_count"], 2)
        self.assertEqual(summary["last_scraped_at"], "2026-06-06")

    def test_marketplace_competitiveness_counts_cheapest_wins(self):
        metrics = self.service.marketplace_competitiveness(self.rows)
        by_marketplace = {item["marketplace"]: item for item in metrics}

        self.assertEqual(by_marketplace["Trendyol"]["cheapest_win_count"], 1)
        self.assertEqual(by_marketplace["Amazon Türkiye"]["cheapest_win_count"], 1)
        self.assertEqual(by_marketplace["Hepsiburada"]["cheapest_win_count"], 0)
        self.assertEqual(by_marketplace["Trendyol"]["listing_count"], 2)

    def test_product_price_spread_returns_widest_products(self):
        spread = self.service.product_price_spread(self.rows)
        first = spread[0]

        self.assertEqual(first["product_code"], "P1")
        self.assertEqual(first["min_price"], 100.0)
        self.assertEqual(first["max_price"], 140.0)
        self.assertEqual(first["spread_percent"], 40.0)
        self.assertEqual(first["cheapest_marketplaces"], ["Trendyol"])

    def test_category_marketplace_heatmap_counts_listing_matrix(self):
        heatmap = self.service.category_marketplace_heatmap(self.rows)
        cell_map = {
            (cell["marketplace"], cell["category"]): cell["listing_count"]
            for cell in heatmap["cells"]
        }

        self.assertEqual(heatmap["categories"], ["Kulaklık", "Mouse"])
        self.assertEqual(cell_map[("Trendyol", "Mouse")], 1)
        self.assertEqual(cell_map[("n11", "Kulaklık")], 1)
        self.assertEqual(cell_map[("Hepsiburada", "Kulaklık")], 0)

    def test_filter_by_category_scopes_rows(self):
        filtered = self.service.filter_by_category(self.rows, "Mouse")

        self.assertEqual({row.product_category for row in filtered}, {"Mouse"})
        self.assertEqual(len(filtered), 5)


if __name__ == "__main__":
    unittest.main()
