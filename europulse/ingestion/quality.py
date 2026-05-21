"""Data quality checks for ingested price data."""

from __future__ import annotations

from datetime import datetime, timezone

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


def check_freshness(conn, max_age_days: int = 5) -> dict:
    """Return freshness metadata for prices, macro, and news tables.

    Returns a dict keyed by table name with keys:
        max_date (datetime | None), age_days (float), ok (bool)
    """
    result: dict = {}
    now = datetime.now(timezone.utc)

    for table, date_col in [
        ("prices", "date"),
        ("macro", "date"),
    ]:
        try:
            row = conn.execute(
                f"SELECT MAX({date_col}) as max_date FROM {table}"
            ).fetchone()
            max_date = row[0]
            if max_date is None:
                result[table] = {"max_date": None, "age_days": float("inf"), "ok": False}
                continue
            if isinstance(max_date, str):
                max_date = pd.to_datetime(max_date)
            if hasattr(max_date, "tzinfo") and max_date.tzinfo is None:
                max_date = max_date.replace(tzinfo=timezone.utc)
            elif not hasattr(max_date, "tzinfo"):
                # datetime.date object — convert to datetime at midnight UTC
                max_date = datetime.combine(max_date, datetime.min.time()).replace(
                    tzinfo=timezone.utc
                )
            age = (now - max_date).total_seconds() / 86400
            result[table] = {"max_date": max_date, "age_days": age, "ok": age <= max_age_days}
        except Exception:
            result[table] = {"max_date": None, "age_days": float("inf"), "ok": False}

    return result
