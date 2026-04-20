# -- Read-Only SQLite Data Loader --
# Provides a query-level API over the scraped products database for the analysis layer.
# All connections are opened in read-only mode (?mode=ro) with query_only pragma
# to guarantee zero side effects on the production data store.

import os
import sqlite3
from typing import Optional, cast

import pandas as pd

from src.definitions import ROOT_DIR

# Canonical marketplace name aliases to normalise inconsistent scraper output
_MARKETPLACE_ALIASES: dict[str, str] = {
    "Media Markt": "MediaMarkt",
    "Media Markt Pazar Yeri": "MediaMarkt Pazaryeri",
}

class DataLoader:

    def __init__(self, db_path: Optional[str] = None) -> None:
        # Resolve the database path and validate its existence before proceeding
        if db_path is None:
            db_path = os.path.join(ROOT_DIR, "database", "scraper.db")

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

        # Construct a read-only URI for safe concurrent access
        self._uri = f"file:{db_path}?mode=ro"
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        # Open an ephemeral read-only connection enforced at both URI and pragma level
        conn = sqlite3.connect(self._uri, uri=True)
        conn.execute("PRAGMA query_only = ON;")
        return conn

    def _normalise_marketplaces(self, df: pd.DataFrame) -> pd.DataFrame:
        # Standardise marketplace name variants using the alias map
        if "marketplace" in df.columns:
            df["marketplace"] = df["marketplace"].replace(_MARKETPLACE_ALIASES)
            df = cast(pd.DataFrame, df.loc[df["marketplace"].notna() & (df["marketplace"] != "")])
        return df

    # -- Query Methods --

    def load_all_products(self) -> pd.DataFrame:
        # Load the entire products table with marketplace normalisation applied
        query = "SELECT * FROM products"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return self._normalise_marketplaces(df)

    def load_by_date(self, scraped_at: str) -> pd.DataFrame:
        # Filter products by a specific scrape date (YYYY-MM-DD format)
        query = "SELECT * FROM products WHERE scraped_at = ?"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(scraped_at,))
        return self._normalise_marketplaces(df)

    def load_price_changes(self) -> pd.DataFrame:
        # Compute product-level price change percentages between two scrape dates
        query = """
            SELECT
                p1.product_code,
                p1.product_category,
                AVG(p1.price) AS feb_avg_price,
                AVG(p2.price) AS apr_avg_price,
                ((AVG(p2.price) - AVG(p1.price)) / AVG(p1.price)) * 100 AS pct_change
            FROM products p1
            JOIN products p2
                ON  p1.product_code = p2.product_code
                AND p1.marketplace  = p2.marketplace
            WHERE p1.scraped_at = '2026-02-18'
              AND p2.scraped_at = '2026-04-18'
            GROUP BY p1.product_code
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df

    def load_category_price_summary(self) -> pd.DataFrame:
        # Aggregate price statistics (avg, min, max, count) by category and date
        query = """
            SELECT
                product_category,
                scraped_at,
                AVG(price)   AS avg_price,
                MIN(price)   AS min_price,
                MAX(price)   AS max_price,
                COUNT(*)     AS record_count
            FROM products
            WHERE marketplace IS NOT NULL AND marketplace != ''
            GROUP BY product_category, scraped_at
            ORDER BY product_category, scraped_at
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df

    def load_marketplace_category_prices(self) -> pd.DataFrame:
        # Cross-tabulate average prices by marketplace, category, and date
        query = """
            SELECT
                marketplace,
                product_category,
                scraped_at,
                AVG(price)               AS avg_price,
                COUNT(DISTINCT product_code) AS product_count
            FROM products
            WHERE marketplace IS NOT NULL AND marketplace != ''
            GROUP BY marketplace, product_category, scraped_at
            ORDER BY marketplace, product_category, scraped_at
        """
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return self._normalise_marketplaces(df)

    def get_scrape_dates(self) -> list[str]:
        # Return a sorted list of all unique scrape dates in the dataset
        query = "SELECT DISTINCT scraped_at FROM products ORDER BY scraped_at"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df["scraped_at"].tolist()

    def get_categories(self) -> list[str]:
        # Return a sorted list of all distinct product categories
        query = "SELECT DISTINCT product_category FROM products WHERE product_category IS NOT NULL ORDER BY product_category"
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return df["product_category"].tolist()
