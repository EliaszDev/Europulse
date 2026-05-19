"""Tests for data quality checks."""

import pandas as pd

from europulse.ingestion.quality import validate_prices


def test_validate_prices_stale_ticker():
    today = pd.Timestamp.now().normalize()
    old_date = today - pd.Timedelta(days=10)

    df = pd.DataFrame({
        "ticker": ["PKN.WA"],
        "date": [old_date],
        "open": [100.0],
        "high": [101.0],
        "low": [99.0],
        "close": [100.5],
        "volume": [1000],
    })

    result = validate_prices(df)
    assert "PKN.WA" in result["stale_tickers"]
