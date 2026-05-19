"""Tests for reporting modules."""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from europulse.reporting.html_generator import generate_html_report
from europulse.reporting.pdf_generator import generate_pdf_report


def _seed_db(path: str) -> None:
    con = duckdb.connect(path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT,
            date DATE,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS macro (
            series TEXT,
            date DATE,
            value DOUBLE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS news (
            hash TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            published DATE,
            url TEXT,
            content TEXT,
            tickers TEXT,
            embedding BLOB
        )
    """)

    # Seed prices
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    prices = []
    for ticker in ["PKN.WA", "SPY"]:
        for i, d in enumerate(dates):
            prices.append((ticker, d, 100 + i, 101 + i, 99 + i, 100 + i, 1000))
    con.executemany("INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)", prices)

    # Seed macro
    macro = []
    for d in dates[-10:]:
        macro.append(("EA19HICP", d, 2.5))
        macro.append(("ECBMLFR", d, 3.0))
    con.executemany("INSERT INTO macro VALUES (?, ?, ?)", macro)

    # Seed news
    con.execute("""
        INSERT INTO news VALUES
        ('abc123', 'Test Article', 'TestSource', '2024-03-01', 'http://example.com', 'Content', '["PKN.WA"]', NULL)
    """)
    con.close()


def test_generate_html_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        _seed_db(str(db_path))
        out_path = Path(tmpdir) / "report.html"
        html = generate_html_report(db_path=str(db_path), output_path=str(out_path), title="Test Report")
        assert "Test Report" in html
        assert out_path.exists()
        content = out_path.read_text()
        assert "Normalized Prices" in content
        assert "PKN.WA" in content


def test_generate_pdf_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        _seed_db(str(db_path))
        out_path = Path(tmpdir) / "report.pdf"
        result = generate_pdf_report(output_path=str(out_path), db_path=str(db_path), title="Test PDF")
        assert result == str(out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 1000
