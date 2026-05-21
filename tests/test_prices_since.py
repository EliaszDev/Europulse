"""Tests for price incremental ingestion via `since`."""

from unittest.mock import patch

import pandas as pd

from europulse.ingestion.prices import fetch_prices


def test_fetch_prices_uses_since_as_start():
    """When `since` is provided, yfinance.download should receive `start`."""

    fake_data = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2024-01-15"]),
    )
    fake_data.index.name = "Date"

    with patch("europulse.ingestion.prices.yf.download") as mock_download:
        mock_download.return_value = fake_data
        fetch_prices(["AAPL"], since="2024-01-01")
        _, kwargs = mock_download.call_args
        assert kwargs.get("start") == "2024-01-01"
        assert "period" not in kwargs


def test_fetch_prices_uses_period_when_since_is_none():
    """When `since` is None, yfinance.download should receive `period`."""

    fake_data = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [101.0],
            "Low": [99.0],
            "Close": [100.5],
            "Volume": [1000],
        },
        index=pd.to_datetime(["2024-01-15"]),
    )
    fake_data.index.name = "Date"

    with patch("europulse.ingestion.prices.yf.download") as mock_download:
        mock_download.return_value = fake_data
        fetch_prices(["AAPL"], period="1y")
        _, kwargs = mock_download.call_args
        assert kwargs.get("period") == "1y"
        assert "start" not in kwargs


def test_fetch_prices_empty_tickers():
    """fetch_prices with empty tickers should return empty DataFrame."""
    df = fetch_prices([])
    assert df.empty
    assert list(df.columns) == ["ticker", "date", "open", "high", "low", "close", "volume"]
