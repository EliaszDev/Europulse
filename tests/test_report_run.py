"""Tests for report run logging."""

import duckdb
import pandas as pd

from europulse.ingestion.db import create_schema, get_conn, log_report_run


def _fresh_conn():
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    return conn


def test_log_report_run_inserts_row():
    """log_report_run should insert a row into report_runs."""
    conn = _fresh_conn()

    log_report_run(
        conn,
        format="html",
        output_path="/tmp/report.html",
        status="success",
        duration_ms=1234,
    )

    df = conn.execute("SELECT * FROM report_runs").fetchdf()
    assert len(df) == 1
    assert df.iloc[0]["format"] == "html"
    assert df.iloc[0]["output_path"] == "/tmp/report.html"
    assert df.iloc[0]["status"] == "success"
    assert df.iloc[0]["duration_ms"] == 1234
    conn.close()


def test_log_report_run_multiple_entries():
    """Multiple log_report_run calls should append rows."""
    conn = _fresh_conn()

    log_report_run(conn, format="html", output_path="/tmp/a.html", status="success", duration_ms=100)
    log_report_run(conn, format="pdf", output_path="/tmp/a.pdf", status="failed", duration_ms=200)

    df = conn.execute("SELECT * FROM report_runs ORDER BY id").fetchdf()
    assert len(df) == 2
    assert df.iloc[0]["format"] == "html"
    assert df.iloc[1]["format"] == "pdf"
    assert df.iloc[1]["status"] == "failed"
    conn.close()
