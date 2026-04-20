import os
import sqlite3
from datetime import datetime
from typing import Optional
from src.core.config import Config
from src.core.logger import Logger
from src.core.exceptions import DatabaseError
from src.definitions import ROOT_DIR

class DatabaseService:
    
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

    _INSERT_SQL = """
        INSERT INTO products
            (brand, product_code, product_category, product_name,
             marketplace, price, product_url, scraped_at)
        VALUES
            (:brand, :product_code, :product_category, :product_name,
             :marketplace, :price, :product_url, :scraped_at);
    """

    def __new__(cls) -> "DatabaseService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
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
        
        try:
            self._connection = sqlite3.connect(self._db_path)
            self._connection.execute("PRAGMA journal_mode=WAL;")
            self._connection.execute("PRAGMA foreign_keys=ON;")
            self._connection.execute(self._CREATE_TABLE_SQL)
            self._connection.execute(self._CREATE_TARGETS_TABLE_SQL)
            self._connection.commit()
            self.logger.info(f"Database connected: {self._db_path}")
        except sqlite3.Error as exc:
            raise DatabaseError(f"Failed to initialise database: {exc}") from exc

    def _ensure_connection(self) -> None:
        
        if self._connection is None:
            self.logger.info("Reconnecting to database (Singleton recovery)...")
            self._connect()

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the active connection, raising if unexpectedly None."""
        assert self._connection is not None, "Database connection is not initialised"
        return self._connection

    def __enter__(self) -> "DatabaseService":
        self._ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        
        if self._connection:
            try:
                self._connection.close()
                self.logger.info("Database connection closed.")
            except sqlite3.Error as exc:
                self.logger.warning(f"Error closing database: {exc}")
            finally:
                self._connection = None

    def insert_product(self, row: dict) -> None:
        
        self._ensure_connection()
        try:
            self.conn.execute(self._INSERT_SQL, row)
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert product: {exc}") from exc

    def insert_products(self, rows: list[dict]) -> None:
        
        if not rows:
            return

        self._ensure_connection()
        try:
            self.conn.executemany(self._INSERT_SQL, rows)
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert product batch: {exc}") from exc

    def add_target_product(self, code: str) -> None:
        
        self._ensure_connection()
        try:
            sql = "INSERT OR IGNORE INTO target_products (product_code) VALUES (?)"
            self.conn.execute(sql, (code,))
            self.conn.commit()
        except sqlite3.Error as exc:
            self.conn.rollback()
            raise DatabaseError(f"Failed to seed target code: {exc}") from exc

    def get_pending_product(self) -> Optional[dict]:
        
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
        
        cls._instance = None
