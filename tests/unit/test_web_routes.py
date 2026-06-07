"""Unit tests for Flask dashboard routes."""

import unittest

from flask import Flask

from src.web.routes import create_dashboard_blueprint
from src.web.schemas import ProductPriceRow


class FakeQueryService:
    """Small fake query service for route tests."""

    def __init__(self):
        self.rows = [
            ProductPriceRow("P1", "P1 Product", "Mouse", "Trendyol", 100.0, "https://a.test/p1", "2026-06-06"),
            ProductPriceRow("P2", "P2 Product", "Kulaklık", "Amazon Türkiye", 200.0, "https://a.test/p2", "2026-06-06"),
        ]

    def fetch_product_rows(self):
        """Return static rows."""
        return self.rows

    @staticmethod
    def available_categories(rows):
        """Return categories from the provided rows."""
        return sorted({row.product_category for row in rows if row.product_category})


class TestWebRoutes(unittest.TestCase):
    """Validate dashboard health and JSON routes."""

    def setUp(self):
        """Create an isolated Flask app with the dashboard blueprint."""
        app = Flask(__name__)
        app.register_blueprint(create_dashboard_blueprint(product_repository=FakeQueryService()))
        self.client = app.test_client()

    def test_health_route(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_dashboard_data_route_returns_chart_payload(self):
        response = self.client.get("/api/dashboard-data")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("summary", payload)
        self.assertIn("marketplace_competitiveness", payload)
        self.assertIn("product_price_spread", payload)
        self.assertIn("category_marketplace_heatmap", payload)
        self.assertEqual(payload["filters"]["categories"], ["Kulaklık", "Mouse"])

    def test_dashboard_data_route_applies_category_filter(self):
        response = self.client.get("/api/dashboard-data?category=Mouse")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["filters"]["selected_category"], "Mouse")
        self.assertEqual(payload["summary"]["total_rows"], 1)


if __name__ == "__main__":
    unittest.main()
