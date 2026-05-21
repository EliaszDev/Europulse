"""Tests for data freshness checks."""

from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd

from europulse.ingestion.db import create_schema, get_conn
from europulse.ingestion.quality import check_freshness


def _fresh_conn():
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    return conn


def test_freshness_ok():
    conn = _fresh_conn()
    today = datetime.now(timezone.utc)
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "date": [today.date()],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1_000_000],
        }
    )
    conn.execute("INSERT INTO prices SELECT * FROM df")

    result = check_freshness(conn, max_age_days=5)
    assert result["prices"]["ok"] is True
    assert result["prices"]["age_days"] <= 1.0
    conn.close()


def test_freshness_stale():
    conn = _fresh_conn()
    old = datetime.now(timezone.utc) - timedelta(days=10)
    df = pd.DataFrame(
        {
            "ticker": ["AAPL"],
            "date": [old.date()],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1_000_000],
        }
    )
    conn.execute("INSERT INTO prices SELECT * FROM df")

    result = check_freshness(conn, max_age_days=5)
    assert result["prices"]["ok"] is False
    assert result["prices"]["age_days"] >= 9.0
    conn.close()


def test_freshness_empty_table():
    conn = _fresh_conn()
    result = check_freshness(conn, max_age_days=5)
    assert result["prices"]["ok"] is False
    assert result["prices"]["max_date"] is None
    conn.close()


def test_freshness_macro():
    conn = _fresh_conn()
    today = datetime.now(timezone.utc)

    macro_df = pd.DataFrame(
        {
            "series": ["CPI"],
            "date": [today.date()],
            "value": [2.5],
        }
    )
    conn.execute("INSERT INTO macro SELECT * FROM macro_df")

    result = check_freshness(conn, max_age_days=5)
    assert result["macro"]["ok"] is True
    conn.close()
