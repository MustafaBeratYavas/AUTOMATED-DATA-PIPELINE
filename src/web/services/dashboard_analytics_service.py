"""Business metrics used by the dashboard charts."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Iterable

from src.web.schemas import ProductPriceRow


class DashboardAnalyticsService:
    """Transform product listing rows into chart-friendly dashboard metrics."""

    @staticmethod
    def filter_by_category(rows: Iterable[ProductPriceRow], category: str | None) -> list[ProductPriceRow]:
        normalized_category = (category or "").strip()
        if not normalized_category:
            return list(rows)
        return [
            row
            for row in rows
            if row.product_category and row.product_category.strip() == normalized_category
        ]

    def summary(self, rows: Iterable[ProductPriceRow]) -> dict:
        row_list = list(rows)
        priced_rows = self._priced_rows(row_list)
        return {
            "total_rows": len(row_list),
            "priced_rows": len(priced_rows),
            "product_count": len({row.product_code for row in row_list}),
            "marketplace_count": len({row.marketplace.strip() for row in priced_rows if row.marketplace}),
            "category_count": len({row.product_category.strip() for row in row_list if row.product_category}),
            "last_scraped_at": max((row.scraped_at for row in row_list), default=None),
        }

    def marketplace_competitiveness(self, rows: Iterable[ProductPriceRow]) -> list[dict]:
        priced_rows = self._best_marketplace_rows(rows)
        rows_by_product = self._group_by_product(priced_rows)
        product_medians = {
            product_code: median(row.price for row in product_rows if row.price is not None)
            for product_code, product_rows in rows_by_product.items()
        }
        cheapest_wins: dict[str, int] = defaultdict(int)
        price_indexes: dict[str, list[float]] = defaultdict(list)
        prices: dict[str, list[float]] = defaultdict(list)

        for product_rows in rows_by_product.values():
            min_price = min(row.price for row in product_rows if row.price is not None)
            for row in product_rows:
                if row.price is None or not row.marketplace:
                    continue
                marketplace = row.marketplace.strip()
                if row.price == min_price:
                    cheapest_wins[marketplace] += 1

        for row in priced_rows:
            assert row.price is not None
            assert row.marketplace is not None
            marketplace = row.marketplace.strip()
            prices[marketplace].append(row.price)
            product_median = product_medians.get(row.product_code)
            if product_median:
                price_indexes[marketplace].append((row.price / product_median) * 100)

        metrics = []
        for marketplace, marketplace_prices in prices.items():
            metrics.append(
                {
                    "marketplace": marketplace,
                    "listing_count": len(marketplace_prices),
                    "cheapest_win_count": cheapest_wins.get(marketplace, 0),
                    "average_price": round(mean(marketplace_prices), 2),
                    "median_price": round(median(marketplace_prices), 2),
                    "average_price_index": round(mean(price_indexes[marketplace]), 2)
                    if price_indexes[marketplace]
                    else None,
                }
            )

        return sorted(
            metrics,
            key=lambda item: (
                -item["cheapest_win_count"],
                -item["listing_count"],
                item["average_price_index"] if item["average_price_index"] is not None else 9999,
                item["marketplace"],
            ),
        )

    def product_price_spread(self, rows: Iterable[ProductPriceRow], limit: int = 12) -> list[dict]:
        priced_rows = self._best_marketplace_rows(rows)
        products = []

        for product_code, product_rows in self._group_by_product(priced_rows).items():
            valid_rows = [row for row in product_rows if row.price is not None and row.marketplace]
            if len(valid_rows) < 2:
                continue

            prices = [row.price for row in valid_rows if row.price is not None]
            min_price = min(prices)
            max_price = max(prices)
            spread = max_price - min_price
            spread_percent = (spread / min_price) * 100 if min_price else 0.0
            cheapest_marketplaces = sorted(
                {row.marketplace.strip() for row in valid_rows if row.price == min_price and row.marketplace}
            )

            products.append(
                {
                    "product_code": product_code,
                    "product_name": self._first_non_empty(row.product_name for row in valid_rows),
                    "category": self._first_non_empty(row.product_category for row in valid_rows),
                    "marketplace_count": len({row.marketplace.strip() for row in valid_rows if row.marketplace}),
                    "min_price": round(min_price, 2),
                    "median_price": round(median(prices), 2),
                    "max_price": round(max_price, 2),
                    "spread": round(spread, 2),
                    "spread_percent": round(spread_percent, 2),
                    "cheapest_marketplaces": cheapest_marketplaces,
                    "product_url": self._first_non_empty(row.product_url for row in valid_rows),
                }
            )

        return sorted(
            products,
            key=lambda item: (-item["spread_percent"], -item["marketplace_count"], item["product_code"]),
        )[:limit]

    def category_marketplace_heatmap(self, rows: Iterable[ProductPriceRow]) -> dict:
        priced_rows = self._best_marketplace_rows(rows)
        categories = sorted({row.product_category.strip() for row in priced_rows if row.product_category})
        marketplaces = sorted({row.marketplace.strip() for row in priced_rows if row.marketplace})
        counts: dict[tuple[str, str], int] = defaultdict(int)

        for row in priced_rows:
            assert row.marketplace is not None
            if not row.product_category:
                continue
            marketplace = row.marketplace.strip()
            category = row.product_category.strip()
            if marketplace and category:
                counts[(marketplace, category)] += 1

        cells = []
        for marketplace in marketplaces:
            for category in categories:
                cells.append(
                    {
                        "marketplace": marketplace,
                        "category": category,
                        "listing_count": counts[(marketplace, category)],
                    }
                )

        return {
            "categories": categories,
            "marketplaces": marketplaces,
            "cells": cells,
            "max_count": max((cell["listing_count"] for cell in cells), default=0),
        }

    @staticmethod
    def _priced_rows(rows: Iterable[ProductPriceRow]) -> list[ProductPriceRow]:
        return [
            row
            for row in rows
            if row.price is not None and row.price > 0 and row.marketplace and row.marketplace.strip()
        ]

    @staticmethod
    def _group_by_product(rows: Iterable[ProductPriceRow]) -> dict[str, list[ProductPriceRow]]:
        groups: dict[str, list[ProductPriceRow]] = defaultdict(list)
        for row in rows:
            groups[row.product_code].append(row)
        return groups

    @classmethod
    def _best_marketplace_rows(cls, rows: Iterable[ProductPriceRow]) -> list[ProductPriceRow]:
        best_rows: dict[tuple[str, str], ProductPriceRow] = {}
        for row in cls._priced_rows(rows):
            assert row.marketplace is not None
            assert row.price is not None
            marketplace = row.marketplace.strip()
            key = (row.product_code, marketplace)
            current = best_rows.get(key)
            if current is None or current.price is None or row.price < current.price:
                best_rows[key] = ProductPriceRow(
                    product_code=row.product_code,
                    product_name=row.product_name,
                    product_category=row.product_category,
                    marketplace=marketplace,
                    price=row.price,
                    product_url=row.product_url,
                    scraped_at=row.scraped_at,
                )
        return list(best_rows.values())

    @staticmethod
    def _first_non_empty(values: Iterable[str | None]) -> str | None:
        for value in values:
            if value and value.strip():
                return value.strip()
        return None
