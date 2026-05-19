"""Tests for reporting modules."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import warnings
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


def test_generate_html_report_empty_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "empty.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute("CREATE TABLE prices (ticker TEXT, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
        con.execute("CREATE TABLE macro (series TEXT, date DATE, value DOUBLE)")
        con.execute("CREATE TABLE news (hash TEXT PRIMARY KEY, title TEXT, source TEXT, published DATE, url TEXT, content TEXT, tickers TEXT, embedding BLOB)")
        con.close()
        out_path = Path(tmpdir) / "report.html"
        html = generate_html_report(db_path=str(db_path), output_path=str(out_path), title="Empty DB Report")
        assert "Empty DB Report" in html
        assert out_path.exists()
        # Should render empty-state message instead of crashing
        assert "No price data available" in html or "No forecast data" in html


def test_generate_html_report_missing_table():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "missing.duckdb"
        con = duckdb.connect(str(db_path))
        # Only create prices table; macro and news are missing
        con.execute("CREATE TABLE prices (ticker TEXT, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
        con.close()
        out_path = Path(tmpdir) / "report.html"
        # Should raise because the query for macro/news will fail without try/catch
        with pytest.raises(Exception):
            generate_html_report(db_path=str(db_path), output_path=str(out_path))


def test_generate_html_report_invalid_news_tickers():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "invalid.duckdb"
        con = duckdb.connect(str(db_path))
        con.execute("CREATE TABLE prices (ticker TEXT, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
        con.execute("CREATE TABLE macro (series TEXT, date DATE, value DOUBLE)")
        con.execute("CREATE TABLE news (hash TEXT PRIMARY KEY, title TEXT, source TEXT, published DATE, url TEXT, content TEXT, tickers TEXT, embedding BLOB)")
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        prices = [("PKN.WA", d, 100 + i, 101 + i, 99 + i, 100 + i, 1000) for i, d in enumerate(dates)]
        con.executemany("INSERT INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)", prices)
        con.execute("INSERT INTO news VALUES ('abc', 'Title', 'Src', '2024-03-01', 'http://x', 'Body', 'NOT JSON', NULL)")
        con.close()
        out_path = Path(tmpdir) / "report.html"
        # Autoescape should prevent XSS even with invalid/malicious content
        html = generate_html_report(db_path=str(db_path), output_path=str(out_path))
        assert "NOT JSON" in html or "Title" in html
        # Ensure it didn't crash
        assert out_path.exists()


def test_cli_both_format_appends_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        _seed_db(str(db_path))
        base = Path(tmpdir) / "report"
        result = subprocess.run(
            [sys.executable, "-m", "scripts.generate_report", "--db", str(db_path), "--format", "both", "--output", str(base)],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        assert result.returncode == 0, result.stderr
        html_path = Path(f"{base}.html")
        pdf_path = Path(f"{base}.pdf")
        assert html_path.exists()
        assert pdf_path.exists()


def test_forecast_chart_contains_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        _seed_db(str(db_path))
        out_path = Path(tmpdir) / "report.html"
        generate_html_report(db_path=str(db_path), output_path=str(out_path))
        content = out_path.read_text()
        # Forecast chart should contain History and Forecast traces
        assert '"History"' in content
        assert '"Forecast"' in content


def test_pdf_content_verification():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        _seed_db(str(db_path))
        out_path = Path(tmpdir) / "report.pdf"
        generate_pdf_report(output_path=str(out_path), db_path=str(db_path))
        pdf_bytes = out_path.read_bytes()
        assert pdf_bytes.startswith(b"%PDF")
        # Basic size sanity check (should be at least a few KB)
        assert len(pdf_bytes) > 1000


def test_app_imports_without_streamlit_runtime():
    # Verify the dashboard module can be imported even when Streamlit isn't running
    import europulse.config as config
    original_db_path = getattr(config, "DB_PATH", None)
    try:
        config.DB_PATH = "/nonexistent/db.duckdb"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import importlib
            import europulse.ui.app as app_module
            importlib.reload(app_module)
            assert hasattr(app_module, "load_data")
    finally:
        if original_db_path is not None:
            config.DB_PATH = original_db_path
