"""HTTP routes for the local dashboard."""

from __future__ import annotations

from typing import Iterable, Protocol

from flask import Blueprint, jsonify, render_template, request

from src.web.repositories.product_repository import ProductRepository
from src.web.schemas import ProductPriceRow
from src.web.services.dashboard_analytics_service import DashboardAnalyticsService


class DashboardProductRepository(Protocol):
    """Repository contract required by the dashboard routes."""

    def fetch_product_rows(self) -> list[ProductPriceRow]:
        """Return product rows to be transformed into dashboard metrics."""
        ...

    def available_categories(self, rows: Iterable[ProductPriceRow]) -> list[str]:
        """Return the available category filters for the provided rows."""
        ...


def create_dashboard_blueprint(
    product_repository: DashboardProductRepository | None = None,
    analytics_service: DashboardAnalyticsService | None = None,
) -> Blueprint:
    """Create the dashboard blueprint with injectable services for tests."""
    dashboard = Blueprint("dashboard", __name__)
    repository = product_repository or ProductRepository()
    analytics = analytics_service or DashboardAnalyticsService()

    @dashboard.get("/")
    def index():
        """Render the dashboard shell; data is loaded through JSON APIs."""
        return render_template("dashboard.html")

    @dashboard.get("/api/dashboard-data")
    def dashboard_data():
        """Return all chart data for the current dashboard filter."""
        rows = repository.fetch_product_rows()
        selected_category = request.args.get("category", "").strip()
        filtered_rows = analytics.filter_by_category(rows, selected_category)

        return jsonify(
            {
                "filters": {
                    "selected_category": selected_category,
                    "categories": repository.available_categories(rows),
                },
                "summary": analytics.summary(filtered_rows),
                "marketplace_competitiveness": analytics.marketplace_competitiveness(filtered_rows),
                "product_price_spread": analytics.product_price_spread(filtered_rows),
                "category_marketplace_heatmap": analytics.category_marketplace_heatmap(filtered_rows),
            }
        )

    @dashboard.get("/health")
    def health():
        """Return a lightweight health response for local checks."""
        return jsonify({"status": "ok"})

    return dashboard
