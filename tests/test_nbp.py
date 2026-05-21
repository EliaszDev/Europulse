"""Tests for Polish National Bank (NBP) exchange-rate fetcher."""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

from europulse.ingestion.nbp import fetch_nbp_series, fetch_nbp_table


def test_fetch_nbp_table():
    """fetch_nbp_table should parse the NBP table API response."""

    fake_json = [{
        "effectiveDate": "2024-06-15",
        "rates": [
            {"code": "EUR", "currency": "euro", "mid": 4.25},
            {"code": "USD", "currency": "dollar", "mid": 3.95},
        ],
    }]

    fake_resp = MagicMock()
    fake_resp.json.return_value = fake_json

    with patch("europulse.ingestion.nbp.fetch_url", return_value=fake_resp):
        df = fetch_nbp_table()

    assert len(df) == 2
    assert set(df["code"]) == {"EUR", "USD"}
    assert df.iloc[0]["date"] == date(2024, 6, 15)


def test_fetch_nbp_table_with_since():
    """The *since* parameter should filter out older rows."""

    fake_json = [{
        "effectiveDate": "2024-01-01",
        "rates": [{"code": "EUR", "currency": "euro", "mid": 4.20}],
    }]

    fake_resp = MagicMock()
    fake_resp.json.return_value = fake_json

    with patch("europulse.ingestion.nbp.fetch_url", return_value=fake_resp):
        df = fetch_nbp_table(since="2024-06-01")

    assert df.empty


def test_fetch_nbp_series():
    """fetch_nbp_series should return a tidy time-series DataFrame."""

    fake_json = {
        "rates": [
            {"effectiveDate": "2024-06-10", "mid": 4.20},
            {"effectiveDate": "2024-06-11", "mid": 4.22},
        ],
    }

    fake_resp = MagicMock()
    fake_resp.json.return_value = fake_json

    with patch("europulse.ingestion.nbp.fetch_url", return_value=fake_resp):
        df = fetch_nbp_series("EUR")

    assert len(df) == 2
    assert list(df.columns) == ["date", "rate"]
    assert df.iloc[-1]["rate"] == 4.22


def test_fetch_nbp_series_with_since():
    """The *since* parameter should filter older observations."""

    fake_json = {
        "rates": [
            {"effectiveDate": "2024-01-01", "mid": 4.20},
            {"effectiveDate": "2024-06-01", "mid": 4.25},
        ],
    }

    fake_resp = MagicMock()
    fake_resp.json.return_value = fake_json

    with patch("europulse.ingestion.nbp.fetch_url", return_value=fake_resp):
        df = fetch_nbp_series("EUR", since="2024-05-01")

    assert len(df) == 1
    assert df.iloc[0]["date"] == date(2024, 6, 1)
