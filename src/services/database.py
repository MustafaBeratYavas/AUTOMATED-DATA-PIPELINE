"""SQLite persistence and queue management for scraped products."""

import os
import sqlite3
from datetime import datetime
from typing import Optional

from src.core.config import Config
from src.core.exceptions import DatabaseError
from src.core.logger import Logger
from src.definitions import ROOT_DIR


class DatabaseService:
    """Singleton database gateway for product rows and scraping targets."""

    _instance: Optional["DatabaseService"] = None

    _CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            brand           TEXT,
            product_code    TEXT    NOT NULL,
            product_category TEXT,
            product_name    TEXT,
            marketplace     TEXT,
            price           REAL,
            product_url     TEXT,
            scraped_at      TEXT    NOT NULL
        );
    """

    _CREATE_TARGETS_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS target_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'PENDING',
            error_count INTEGER DEFAULT 0,
            last_scraped_at TEXT
        );
    """

    _CREATE_PRODUCT_CATALOG_SQL = """
        CREATE TABLE IF NOT EXISTS product_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT,
            product_code TEXT UNIQUE NOT NULL,
            product_name TEXT,
            product_category TEXT,
            product_url TEXT,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """

    _CREATE_MARKETPLACES_SQL = """
        CREATE TABLE IF NOT EXISTS marketplaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );
    """

    _CREATE_PRICE_OBSERVATIONS_SQL = """
        CREATE TABLE IF NOT EXISTS price_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legacy_product_id INTEGER UNIQUE NOT NULL,
            product_id INTEGER NOT NULL,
            marketplace_id INTEGER,
            price REAL,
            product_url TEXT,
            scraped_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (legacy_product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES product_catalog(id) ON DELETE CASCADE,
            FOREIGN KEY (marketplace_id) REFERENCES marketplaces(id) ON DELETE SET NULL
        );
    """

    _CREATE_TARGET_STATUS_HISTORY_SQL = """
        CREATE TABLE IF NOT EXISTS target_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            old_error_count INTEGER,
            new_error_count INTEGER NOT NULL,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (target_product_id) REFERENCES target_products(id) ON DELETE CASCADE
        );
    """

    _CREATE_TARGET_HISTORY_TRIGGERS_SQL = """
        CREATE TRIGGER IF NOT EXISTS trg_target_products_insert_history
        AFTER INSERT ON target_products
        BEGIN
            INSERT INTO target_status_history
                (target_product_id, product_code, old_status, new_status,
                 old_error_count, new_error_count)
            VALUES
                (NEW.id, NEW.product_code, NULL, NEW.status, NULL, NEW.error_count);
        END;

        CREATE TRIGGER IF NOT EXISTS trg_target_products_update_history
        AFTER UPDATE OF status, error_count ON target_products
        WHEN OLD.status IS NOT NEW.status OR OLD.error_count IS NOT NEW.error_count
        BEGIN
            INSERT INTO target_status_history
                (target_product_id, product_code, old_status, new_status,
                 old_error_count, new_error_count)
            VALUES
                (NEW.id, NEW.product_code, OLD.status, NEW.status,
                 OLD.error_count, NEW.error_count);
        END;
    """

    _CREATE_ANALYTICS_VIEWS_SQL = """
        CREATE VIEW IF NOT EXISTS v_product_offer_history AS
        SELECT
            po.id AS observation_id,
            pc.product_code,
            pc.brand,
            pc.product_name,
            pc.product_category,
            m.name AS marketplace,
            po.price,
            po.product_url,
            po.scraped_at,
            po.created_at
        FROM price_observations AS po
        JOIN product_catalog AS pc ON pc.id = po.product_id
        LEFT JOIN marketplaces AS m ON m.id = po.marketplace_id;

        CREATE VIEW IF NOT EXISTS v_marketplace_price_summary AS
        SELECT
            m.name AS marketplace,
            COUNT(*) AS listing_count,
            COUNT(DISTINCT pc.product_code) AS product_count,
            ROUND(MIN(po.price), 2) AS min_price,
            ROUND(AVG(po.price), 2) AS average_price,
            ROUND(MAX(po.price), 2) AS max_price,
            MAX(po.scraped_at) AS latest_scraped_at
        FROM price_observations AS po
        JOIN product_catalog AS pc ON pc.id = po.product_id
        JOIN marketplaces AS m ON m.id = po.marketplace_id
        WHERE po.price IS NOT NULL AND po.price > 0
        GROUP BY m.name;

        CREATE VIEW IF NOT EXISTS v_product_price_spread AS
        SELECT
            pc.product_code,
            pc.product_name,
            pc.product_category,
            COUNT(DISTINCT po.marketplace_id) AS marketplace_count,
            ROUND(MIN(po.price), 2) AS min_price,
            ROUND(AVG(po.price), 2) AS average_price,
            ROUND(MAX(po.price), 2) AS max_price,
            ROUND(MAX(po.price) - MIN(po.price), 2) AS price_spread,
            MAX(po.scraped_at) AS latest_scraped_at
        FROM price_observations AS po
        JOIN product_catalog AS pc ON pc.id = po.product_id
        WHERE po.price IS NOT NULL AND po.price > 0
        GROUP BY pc.product_code, pc.product_name, pc.product_category;
    """

    _INSERT_SQL = """
        INSERT INTO products
            (brand, product_code, product_category, product_name,
             marketplace, price, product_url, scraped_at)
        VALUES
            (:brand, :product_code, :product_category, :product_name,
             :marketplace, :price, :product_url, :scraped_at);
    """

    def __new__(cls) -> "DatabaseService":
        """Return one service instance so SQLite connections are centralized."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
        """Open the configured SQLite database and create required tables."""
        if self._initialised:
            return

        self.logger = Logger.get_logger(__name__)
        self.config = Config()

        db_rel_path = self.config.get("paths", "database", default="data/scraper.db")
        self._db_path = os.path.join(ROOT_DIR, db_rel_path)

        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        self._connection: Optional[sqlite3.Connection] = None
        self._connect()
        self._initialised = True

    def _connect(self) -> None:
        """Create the SQLite connection and initialize schema if needed."""
        try:
            self._connection = sqlite3.connect(self._db_path)
            self._connection.execute("PRAGMA journal_mode=WAL;")
            self._connection.execute("PRAGMA foreign_keys=ON;")
            self._initialize_schema()
            self._connection.commit()
            self.logger.info(f"Database connected: {self._db_path}")
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialise database: {exc}") from exc

    def _initialize_schema(self) -> None:
        """Create all persistence, relational, view, and trigger objects."""
        self.conn.execute(self._CREATE_TABLE_SQL)
        self.conn.execute(self._CREATE_TARGETS_TABLE_SQL)
        self.conn.execute(self._CREATE_PRODUCT_CATALOG_SQL)
        self.conn.execute(self._CREATE_MARKETPLACES_SQL)
        self.conn.execute(self._CREATE_PRICE_OBSERVATIONS_SQL)
        self.conn.execute(self._CREATE_TARGET_STATUS_HISTORY_SQL)
        self.conn.executescript(self._CREATE_TARGET_HISTORY_TRIGGERS_SQL)
        self.conn.executescript(self._CREATE_ANALYTICS_VIEWS_SQL)
        self._backfill_relational_tables()

    def _backfill_relational_tables(self) -> None:
        """Populate the relational schema from existing legacy product rows."""
        cursor = self.conn.execute(
            """
            SELECT id, brand, product_code, product_category, product_name,
                   marketplace, price, product_url, scraped_at
            FROM products
            ORDER BY id ASC
            """
        )
        for legacy_id, brand, code, category, name, marketplace, price, url, scraped_at in cursor.fetchall():
            row = {
                "brand": brand,
                "product_code": code,
                "product_category": category,
                "product_name": name,
                "marketplace": marketplace,
                "price": price,
                "product_url": url,
                "scraped_at": scraped_at,
            }
            self._insert_relational_product_row(row, legacy_id)

    def _ensure_connection(self) -> None:
        """Reconnect lazily after a context-managed close."""
        if self._connection is None:
            self.logger.info("Reconnecting to database (Singleton recovery)...")
            self._connect()

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the active connection, raising if unexpectedly absent."""
        assert self._connection is not None, "Database connection is not initialised"
        return self._connection

    def __enter__(self) -> "DatabaseService":
        """Ensure the database is connected before entering a context block."""
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the active connection when a context block exits."""
        self.close()

    def close(self) -> None:
        """Close the SQLite connection while keeping singleton state recoverable."""
        if self._connection:
            try:
                self._connection.close()
                self.logger.info("Database connection closed.")
            except sqlite3.Error as exc:
                self.logger.warning(f"Error closing database: {exc}")
            finally:
                self._connection = None

    def insert_product(self, row: dict) -> None:
        """Insert one normalized product row."""
        self._ensure_connection()
        try:
            cursor = self.conn.execute(self._INSERT_SQL, row)
            legacy_product_id = cursor.lastrowid
            if legacy_product_id is None:
                raise DatabaseError("SQLite did not return an id for inserted product row")
            self._insert_relational_product_row(row, legacy_product_id)
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert product: {exc}") from exc

    def insert_products(self, rows: list[dict]) -> None:
        """Insert a batch of normalized product rows atomically."""
        if not rows:
            return

        self._ensure_connection()
        try:
            for row in rows:
                cursor = self.conn.execute(self._INSERT_SQL, row)
                legacy_product_id = cursor.lastrowid
                if legacy_product_id is None:
                    raise DatabaseError("SQLite did not return an id for inserted product row")
                self._insert_relational_product_row(row, legacy_product_id)
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert product batch: {exc}") from exc

    def _insert_relational_product_row(self, row: dict, legacy_product_id: int) -> None:
        """Mirror a legacy product row into the relational SQL schema."""
        product_id = self._upsert_product_catalog(row)
        marketplace_id = self._upsert_marketplace(row.get("marketplace"))
        self.conn.execute(
            """
            INSERT OR IGNORE INTO price_observations
                (legacy_product_id, product_id, marketplace_id, price, product_url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                legacy_product_id,
                product_id,
                marketplace_id,
                row.get("price"),
                row.get("product_url"),
                row.get("scraped_at"),
            ),
        )

    def _upsert_product_catalog(self, row: dict) -> int:
        """Insert or refresh one product catalog record and return its id."""
        product_code = row["product_code"]
        self.conn.execute(
            """
            INSERT INTO product_catalog
                (brand, product_code, product_name, product_category, product_url)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_code) DO UPDATE SET
                brand = COALESCE(excluded.brand, product_catalog.brand),
                product_name = COALESCE(excluded.product_name, product_catalog.product_name),
                product_category = COALESCE(excluded.product_category, product_catalog.product_category),
                product_url = COALESCE(excluded.product_url, product_catalog.product_url),
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (
                row.get("brand"),
                product_code,
                row.get("product_name"),
                row.get("product_category"),
                row.get("product_url"),
            ),
        )
        cursor = self.conn.execute(
            "SELECT id FROM product_catalog WHERE product_code = ?",
            (product_code,),
        )
        return int(cursor.fetchone()[0])

    def _upsert_marketplace(self, marketplace: str | None) -> int | None:
        """Insert one marketplace when available and return its id."""
        if not marketplace or not marketplace.strip():
            return None

        name = marketplace.strip()
        self.conn.execute(
            "INSERT OR IGNORE INTO marketplaces (name) VALUES (?)",
            (name,),
        )
        cursor = self.conn.execute(
            "SELECT id FROM marketplaces WHERE name = ?",
            (name,),
        )
        return int(cursor.fetchone()[0])

    def add_target_product(self, code: str) -> None:
        """Add a product code to the scraping queue if it is not already present."""
        self._ensure_connection()
        try:
            sql = "INSERT OR IGNORE INTO target_products (product_code) VALUES (?)"
            self.conn.execute(sql, (code,))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to seed target code: {exc}") from exc

    def get_pending_product(self) -> Optional[dict]:
        """Claim the oldest pending product and mark it in progress."""
        self._ensure_connection()
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, product_code, error_count
                FROM target_products
                WHERE status = 'PENDING'
                ORDER BY id ASC LIMIT 1
            ''')
            row = cursor.fetchone()

            if not row:
                return None

            t_id, code, err_count = row

            # The status update is committed with the read to avoid duplicate work.
            cursor.execute('''
                UPDATE target_products
                SET status = 'IN_PROGRESS'
                WHERE id = ?
            ''', (t_id,))

            self.conn.commit()
            return {"id": t_id, "product_code": code, "error_count": err_count}

        except sqlite3.Error as exc:
            self.conn.rollback()
            self.logger.error(f"Error fetching pending product: {exc}")
            raise DatabaseError(f"Queue lock error: {exc}") from exc

    def update_target_status(self, target_id: int, status: str, error_count: int = 0) -> None:
        """Persist a queue status transition for a target product."""
        self._ensure_connection()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            sql = '''
                UPDATE target_products
                SET status = ?, error_count = ?, last_scraped_at = ?
                WHERE id = ?
            '''
            self.conn.execute(sql, (status, error_count, now, target_id))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to update target status: {exc}") from exc

    @classmethod
    def reset_instance(cls) -> None:
        """Clear singleton state for unit tests."""
        cls._instance = None
