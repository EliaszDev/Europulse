"""Tests for the alert engine."""

import pandas as pd

from europulse.analysis.alerts import (
    macro_alerts,
    price_alerts,
    risk_alerts,
    serialize_alerts,
    _rsi,
)


def test_rsi_calculation():
    prices = pd.Series([100, 102, 101, 105, 103, 107, 106, 108, 110, 112, 111, 113, 115, 114, 116])
    rsi_vals = _rsi(prices)
    assert len(rsi_vals) == len(prices)
    valid = rsi_vals.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_price_alerts_rsi_overbought():
    # Alternating up-trend to push RSI > 70
    prices = [100, 102, 101, 104, 103, 106, 105, 108, 107, 110, 109, 112, 111, 114, 113, 116, 115, 118, 117, 120, 119, 122, 121, 124, 123, 126, 125, 128, 127, 130]
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * len(prices),
        "date": pd.date_range("2024-01-01", periods=len(prices)),
        "close": prices,
        "volume": [1000] * len(prices),
    })
    alerts = price_alerts(df)
    overbought = [a for a in alerts if a["type"] == "RSI_OVERBOUGHT"]
    assert len(overbought) == 1
    assert overbought[0]["ticker"] == "PKN.WA"
    assert overbought[0]["severity"] == "warning"


def test_price_alerts_rsi_oversold():
    prices = list(range(130, 100, -1))
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * len(prices),
        "date": pd.date_range("2024-01-01", periods=len(prices)),
        "close": prices,
        "volume": [1000] * len(prices),
    })
    alerts = price_alerts(df)
    oversold = [a for a in alerts if a["type"] == "RSI_OVERSOLD"]
    assert len(oversold) == 1
    assert oversold[0]["ticker"] == "PKN.WA"


def test_price_alerts_volume_spike():
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "close": [100.0, 101.0, 102.0],
        "volume": [1000, 1000, 5000],
    })
    alerts = price_alerts(df)
    spikes = [a for a in alerts if a["type"] == "VOLUME_SPIKE"]
    assert len(spikes) == 1
    assert spikes[0]["value"] == 5.0


def test_price_alerts_empty():
    df = pd.DataFrame(columns=["ticker", "date", "close", "volume"])
    alerts = price_alerts(df)
    assert alerts == []


def test_macro_alerts_inflation_high():
    df = pd.DataFrame({
        "series": ["EA19HICP"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "value": [2.5, 3.1, 4.0],
    })
    alerts = macro_alerts(df)
    high = [a for a in alerts if a["type"] == "INFLATION_HIGH"]
    assert len(high) == 1
    assert high[0]["value"] == 4.0
    assert high[0]["severity"] == "critical"


def test_macro_alerts_yield_curve_inverted():
    df = pd.DataFrame({
        "series": ["T10Y2Y"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "value": [0.5, -0.1, -0.3],
    })
    alerts = macro_alerts(df)
    inverted = [a for a in alerts if a["type"] == "YIELD_CURVE_INVERTED"]
    assert len(inverted) == 1
    assert inverted[0]["value"] == -0.3


def test_macro_alerts_policy_restrictive():
    df = pd.DataFrame({
        "series": ["ECBMLFR"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "value": [0.5, 1.5, 3.0],
    })
    alerts = macro_alerts(df)
    restrictive = [a for a in alerts if a["type"] == "POLICY_RESTRICTIVE"]
    assert len(restrictive) == 1
    assert restrictive[0]["value"] == 3.0


def test_macro_alerts_policy_accommodative():
    df = pd.DataFrame({
        "series": ["ECBMLFR"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "value": [3.0, 1.5, 0.25],
    })
    alerts = macro_alerts(df)
    accommodative = [a for a in alerts if a["type"] == "POLICY_ACCOMMODATIVE"]
    assert len(accommodative) == 1
    assert accommodative[0]["value"] == 0.25


def test_risk_alerts_drawdown_warning():
    # Max dd ~ -13.6% (from 110 to 95), severity = warning
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 5,
        "date": pd.date_range("2024-01-01", periods=5),
        "close": [100, 110, 95, 100, 102],
    })
    alerts = risk_alerts(df, drawdown_threshold=-0.10)
    dd_alerts = [a for a in alerts if a["type"] == "MAX_DRAWDOWN"]
    assert len(dd_alerts) == 1
    assert dd_alerts[0]["ticker"] == "PKN.WA"
    assert dd_alerts[0]["severity"] == "warning"


def test_risk_alerts_drawdown_critical():
    # Max dd ~ -27% (from 110 to 80), severity = critical
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 6,
        "date": pd.date_range("2024-01-01", periods=6),
        "close": [100, 110, 90, 95, 80, 85],
    })
    alerts = risk_alerts(df, drawdown_threshold=-0.10)
    dd_alerts = [a for a in alerts if a["type"] == "MAX_DRAWDOWN"]
    assert len(dd_alerts) == 1
    assert dd_alerts[0]["ticker"] == "PKN.WA"
    assert dd_alerts[0]["severity"] == "critical"


def test_risk_alerts_no_drawdown():
    df = pd.DataFrame({
        "ticker": ["PKN.WA"] * 3,
        "date": pd.date_range("2024-01-01", periods=3),
        "close": [100, 101, 102],
    })
    alerts = risk_alerts(df, drawdown_threshold=-0.10)
    assert alerts == []


def test_serialize_alerts():
    alerts = [{"type": "TEST", "value": 42.0}]
    json_str = serialize_alerts(alerts)
    assert isinstance(json_str, str)
    assert "TEST" in json_str
    assert "42.0" in json_str
