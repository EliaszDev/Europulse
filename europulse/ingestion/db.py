"""DuckDB connection, schema, and storage helpers."""

from __future__ import annotations

import duckdb
import pandas as pd

from europulse import config


def get_conn(path: str = config.DB_PATH) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection (creates file if missing)."""
    return duckdb.connect(path)


def create_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create all application tables if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro (
            series TEXT,
            date DATE,
            value DOUBLE,
            PRIMARY KEY (series, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            prompt_hash TEXT PRIMARY KEY,
            prompt TEXT,
            response TEXT,
            model TEXT,
            created_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY,
            alert_type TEXT,
            ticker TEXT,
            metric_value DOUBLE,
            threshold DOUBLE,
            explanation TEXT,
            triggered_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            level TEXT,
            message TEXT,
            timestamp TIMESTAMP DEFAULT current_timestamp
        )
    """)


def upsert_prices(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    """Insert or replace price rows into DuckDB."""
    conn.register("prices_df", df)
    conn.execute("""
        INSERT OR REPLACE INTO prices
        SELECT * FROM prices_df
    """)
    conn.unregister("prices_df")


def upsert_macro(conn: duckdb.DuckDBPyConnection, df: pd.DataFrame) -> None:
    """Insert or replace macro rows into DuckDB."""
    conn.register("macro_df", df)
    conn.execute("""
        INSERT OR REPLACE INTO macro
        SELECT * FROM macro_df
    """)
    conn.unregister("macro_df")
