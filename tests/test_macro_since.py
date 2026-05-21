"""Tests for macro incremental ingestion via `since`."""

from datetime import date
from unittest.mock import MagicMock

import pandas as pd

from europulse.ingestion.macro import _fetch_fred_series, fetch_ecb, fetch_fred


def test_fetch_fred_passes_since_to_api(monkeypatch):
    """fetch_fred should pass `since` to _fetch_fred_series."""

    captured = {}

    def fake_fetch(series_id, **kwargs):
        captured["since"] = kwargs.get("since")
        return pd.DataFrame({
            "series": [series_id],
            "date": [date(2024, 1, 1)],
            "value": [2.5],
        })

    monkeypatch.setattr("europulse.ingestion.macro._fetch_fred_series", fake_fetch)

    fetch_fred(["CPI"], since="2023-06-01")
    assert captured["since"] == "2023-06-01"


def test_fetch_fred_uses_start_when_since_is_none(monkeypatch):
    """fetch_fred should use `start` as since when since is not provided."""

    captured = {}

    def fake_fetch(series_id, **kwargs):
        captured["since"] = kwargs.get("since")
        return pd.DataFrame({
            "series": [series_id],
            "date": [date(2024, 1, 1)],
            "value": [2.5],
        })

    monkeypatch.setattr("europulse.ingestion.macro._fetch_fred_series", fake_fetch)

    fetch_fred(["CPI"], start="2020-01-01")
    assert captured["since"] == "2020-01-01"


def test_fetch_ecb_passes_since(monkeypatch):
    """fetch_ecb should pass `since` through to _fetch_fred_series."""

    captured = {}

    def fake_fetch(series_id, **kwargs):
        captured["since"] = kwargs.get("since")
        return pd.DataFrame({
            "series": [series_id],
            "date": [date(2024, 1, 1)],
            "value": [1.5],
        })

    monkeypatch.setattr("europulse.ingestion.macro._fetch_fred_series", fake_fetch)

    fetch_ecb(["ECBMLFR"], since="2023-01-01")
    assert captured["since"] == "2023-01-01"


def test_fetch_fred_empty_series():
    """fetch_fred with empty series should return empty DataFrame."""
    df = fetch_fred([])
    assert df.empty
    assert list(df.columns) == ["series", "date", "value"]
