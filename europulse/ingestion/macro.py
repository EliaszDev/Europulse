"""Macro data ingestion via FRED and ECB sources."""

from __future__ import annotations

import os

import httpx
import pandas as pd

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"


def _fetch_fred_series(series_id: str, api_key: str | None = None) -> pd.DataFrame:
    """Fetch a single FRED series via the public API."""
    key = api_key or os.getenv("FRED_API_KEY", "")
    params: dict[str, str] = {
        "series_id": series_id,
        "file_type": "json",
        "sort_order": "asc",
    }
    if key:
        params["api_key"] = key

    resp = httpx.get(FRED_API_URL, params=params, timeout=30.0)
    resp.raise_for_status()
    data = resp.json()

    observations = data.get("observations", [])
    if not observations:
        return pd.DataFrame(columns=["series", "date", "value"])

    rows = []
    for obs in observations:
        val = obs.get("value")
        if val is None or val == ".":
            continue
        try:
            rows.append({
                "series": series_id,
                "date": obs["date"],
                "value": float(val),
            })
        except ValueError:
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def fetch_fred(series: list[str], start: str = "2018-01-01") -> pd.DataFrame:
    """Download FRED series and return long-format DataFrame.

    Columns: series, date, value
    """
    if not series:
        return pd.DataFrame(columns=["series", "date", "value"])

    frames = []
    for s in series:
        try:
            df = _fetch_fred_series(s)
            if not df.empty:
                df = df[df["date"] >= pd.to_datetime(start).date()]
                frames.append(df)
        except Exception as exc:
            print(f"  Warning: failed to fetch {s} from FRED: {exc}")

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["series", "date", "value"])


def fetch_ecb(series: list[str]) -> pd.DataFrame:
    """Download ECB SDW series.

    Currently falls back to FRED aliases for common ECB series.
    Columns: series, date, value
    """
    if not series:
        return pd.DataFrame(columns=["series", "date", "value"])

    # FRED aliases for common ECB series
    fred_aliases = {
        "ECBMLFR": "ECBMLFR",
        "EA19HICP": "EA19HICP",
    }

    frames = []
    for s in series:
        alias = fred_aliases.get(s, s)
        try:
            df = _fetch_fred_series(alias)
            if not df.empty:
                df["series"] = s  # preserve original series name
                frames.append(df)
        except Exception as exc:
            print(f"  Warning: failed to fetch {s} from ECB/FRED: {exc}")

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["series", "date", "value"])
