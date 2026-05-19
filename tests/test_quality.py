"""Tests for data quality validation."""

import pandas as pd

from europulse.ingestion.quality import validate_prices


def test_validate_prices_fresh():
    """All tickers have recent data — no issues."""
    today = pd.Timestamp.now().normalize()
    df = pd.DataFrame({
        "ticker": ["PKN.WA", "CDR.WA", "ALE.WA"],
        "date": [today, today, today],
        "close": [100.0, 200.0, 50.0],
        "volume": [1000, 2000, 500],
    })
    result = validate_prices(df)
    assert result["stale_tickers"] == []
    assert result["missing_dates"] == {}
    assert result["zero_volume_days"] == {}


def test_validate_prices_stale():
    """Old dates should flag stale tickers."""
    today = pd.Timestamp.now().normalize()
    df = pd.DataFrame({
        "ticker": ["PKN.WA", "PKN.WA", "CDR.WA"],
        "date": [today - pd.Timedelta(days=10), today - pd.Timedelta(days=9), today],
        "close": [100.0, 101.0, 200.0],
        "volume": [1000, 1000, 2000],
    })
    result = validate_prices(df)
    assert "PKN.WA" in result["stale_tickers"]
    assert "CDR.WA" not in result["stale_tickers"]


def test_validate_prices_missing_dates():
    """Gaps in trading days should populate missing_dates."""
    today = pd.Timestamp.now().normalize()
    # 10 business days with only 5 present = 5 missing
    dates = pd.bdate_range(end=today, periods=10)
    present = dates[[0, 2, 4, 6, 8]]
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * len(present),
        "date": present,
        "close": [100.0] * len(present),
        "volume": [1000] * len(present),
    })
    result = validate_prices(df)
    assert "PKN.WA" in result["missing_dates"]
    assert result["missing_dates"]["PKN.WA"] > 0


def test_validate_prices_zero_volume():
    """Zero-volume rows should be flagged."""
    today = pd.Timestamp.now().normalize()
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 4,
        "date": pd.date_range(end=today, periods=4),
        "close": [100.0] * 4,
        "volume": [1000, 0, 500, 0],
    })
    result = validate_prices(df)
    assert "PKN.WA" in result["zero_volume_days"]
    assert result["zero_volume_days"]["PKN.WA"] == 2
