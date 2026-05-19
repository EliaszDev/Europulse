"""Data quality checks for ingested price data."""

from __future__ import annotations

import pandas as pd


def validate_prices(df: pd.DataFrame) -> dict:
    """Return quality flags for a price DataFrame.

    Expected columns: ticker, date, open, high, low, close, volume
    """
    result = {
        "missing_dates": {},
        "zero_volume_days": {},
        "stale_tickers": [],
    }

    if df.empty:
        return result

    # Ensure date is datetime
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    today = pd.Timestamp.now().normalize()
    stale_threshold = today - pd.Timedelta(days=5)

    for ticker, grp in df.groupby("ticker"):
        grp = grp.sort_values("date")

        # Missing trading days heuristic: compare expected vs actual count
        date_range = pd.date_range(start=grp["date"].min(), end=grp["date"].max(), freq="B")
        missing = len(date_range) - len(grp)
        if missing > 0:
            result["missing_dates"][ticker] = missing

        # Zero volume days
        zero_vol = (grp["volume"] == 0).sum()
        if zero_vol > 0:
            result["zero_volume_days"][ticker] = int(zero_vol)

        # Stale tickers
        if grp["date"].max() < stale_threshold:
            result["stale_tickers"].append(ticker)

    return result
