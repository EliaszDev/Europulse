"""Polish National Bank (NBP) official exchange-rate fetcher.

NBP provides a free, no-key JSON API for current and historical
mid-exchange rates of major currencies against PLN.
"""

from __future__ import annotations

import pandas as pd

from europulse.ingestion.http import fetch_url

NBP_TABLE_URL = "http://api.nbp.pl/api/exchangerates/tables/A"
NBP_SERIES_URL = "http://api.nbp.pl/api/exchangerates/rates/A"


def fetch_nbp_table(since: str | None = None) -> pd.DataFrame:
    """Fetch the latest NBP table A (mid rates) and return a tidy DataFrame.

    Columns: code, currency, rate, date
    """
    url = f"{NBP_TABLE_URL}/?format=json"
    resp = fetch_url(url, timeout=20.0)
    data = resp.json()

    rows = []
    for table in data:
        effective_date = table.get("effectiveDate")
        for rate in table.get("rates", []):
            rows.append({
                "code": rate["code"],
                "currency": rate["currency"],
                "rate": rate["mid"],
                "date": effective_date,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        df = df.dropna(subset=["rate"])
        if since:
            since_date = pd.to_datetime(since).date()
            df = df[df["date"] >= since_date]
    return df


def fetch_nbp_series(code: str, since: str | None = None) -> pd.DataFrame:
    """Fetch historical mid-rate series for a single currency *code* (e.g. EUR).

    Columns: date, rate
    """
    url = f"{NBP_SERIES_URL}/{code}/?format=json"
    resp = fetch_url(url, timeout=20.0)
    data = resp.json()

    rows = []
    for rate in data.get("rates", []):
        rows.append({"date": rate["effectiveDate"], "rate": rate["mid"]})

    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
        df = df.dropna(subset=["rate"])
        if since:
            since_date = pd.to_datetime(since).date()
            df = df[df["date"] >= since_date]
    return df[["date", "rate"]]
