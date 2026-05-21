"""Tests for ingestion layer."""

import duckdb
import pandas as pd

from europulse.ingestion.db import create_schema, upsert_prices


def test_create_schema():
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    assert table_names == {"prices", "macro", "alerts", "logs", "report_runs"}
    conn.close()


def test_upsert_prices():
    conn = duckdb.connect(":memory:")
    create_schema(conn)

    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 5,
        "date": pd.date_range("2024-01-01", periods=5),
        "open": [100.0] * 5,
        "high": [101.0] * 5,
        "low": [99.0] * 5,
        "close": [100.5] * 5,
        "volume": [1000] * 5,
    })

    upsert_prices(conn, df)
    count = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    assert count == 5
    conn.close()
