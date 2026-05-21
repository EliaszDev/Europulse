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
    conn.execute("CREATE SEQUENCE IF NOT EXISTS report_runs_seq")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS report_runs (
            id INTEGER PRIMARY KEY DEFAULT nextval('report_runs_seq'),
            run_at TIMESTAMP DEFAULT current_timestamp,
            format TEXT,
            output_path TEXT,
            status TEXT,
            duration_ms INTEGER
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


def log_report_run(
    conn: duckdb.DuckDBPyConnection,
    format: str,
    output_path: str,
    status: str,
    duration_ms: int = 0,
) -> None:
    """Log a report generation run to the database."""
    conn.execute("""
        INSERT INTO report_runs (format, output_path, status, duration_ms)
        VALUES (?, ?, ?, ?)
    """, [format, output_path, status, duration_ms])
