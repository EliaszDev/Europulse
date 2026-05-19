"""Price ingestion via yfinance."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_prices(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """Download OHLCV data and normalise to long format.

    Returns DataFrame with columns: ticker, date, open, high, low, close, volume
    """
    if not tickers:
        return pd.DataFrame(
            columns=["ticker", "date", "open", "high", "low", "close", "volume"]
        )

    data = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
    )

    if data.empty:
        return pd.DataFrame(
            columns=["ticker", "date", "open", "high", "low", "close", "volume"]
        )

    # Single ticker returns 1D columns; multi-ticker returns 2D MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        # Multi-ticker: melt wide -> long
        df = data.stack(level=1, future_stack=True).reset_index()
        df = df.rename(
            columns={
                "Date": "date",
                "Ticker": "ticker",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
    else:
        # Single ticker
        df = data.reset_index()
        df["ticker"] = tickers[0]
        df = df.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

    # Ensure column names are lowercase
    df.columns = [c.lower() for c in df.columns]

    # Select and order columns
    cols = ["ticker", "date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in cols if c in df.columns]]

    # Drop rows with missing close price
    df = df.dropna(subset=["close"])

    # Convert date to datetime.date for DuckDB compatibility
    df["date"] = pd.to_datetime(df["date"]).dt.date

    return df
