"""Tests for the analysis engine."""

import numpy as np
import pandas as pd

from europulse.analysis.forecast import exp_smooth_forecast, linear_forecast
from europulse.analysis.regimes import detect_regimes
from europulse.analysis.risk import (
    beta_to_benchmark,
    correlation_matrix,
    max_drawdown,
    rolling_volatility,
    sharpe_ratio,
)


def _mock_macro() -> pd.DataFrame:
    """Build a mock macro DataFrame with three distinct regimes."""
    rows = []
    # Expansion: target inflation, normal yield curve, neutral rate
    for d in pd.date_range("2024-01-01", periods=3):
        rows.append({"series": "EA19HICP", "date": d, "value": 2.0})
        rows.append({"series": "T10Y2Y", "date": d, "value": 0.5})
        rows.append({"series": "ECBMLFR", "date": d, "value": 1.5})

    # Slowdown: high inflation, restrictive policy
    for d in pd.date_range("2024-04-01", periods=3):
        rows.append({"series": "EA19HICP", "date": d, "value": 4.0})
        rows.append({"series": "T10Y2Y", "date": d, "value": -0.2})
        rows.append({"series": "ECBMLFR", "date": d, "value": 3.0})

    # Recovery: low inflation, accommodative policy
    for d in pd.date_range("2024-07-01", periods=3):
        rows.append({"series": "EA19HICP", "date": d, "value": 1.0})
        rows.append({"series": "T10Y2Y", "date": d, "value": 0.3})
        rows.append({"series": "ECBMLFR", "date": d, "value": 0.25})

    return pd.DataFrame(rows)


def test_detect_regimes():
    df = _mock_macro()
    regimes = detect_regimes(df)

    assert not regimes.empty
    assert set(regimes["composite_regime"].unique()) >= {"Expansion", "Slowdown", "Recovery"}
    assert "inflation_regime" in regimes.columns
    assert "signals_json" in regimes.columns


def test_rolling_volatility():
    np.random.seed(42)
    prices = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
        index=pd.date_range("2024-01-01", periods=100),
    )
    vol = rolling_volatility(prices, window=30)
    assert len(vol) == len(prices) - 1  # first return is dropped
    assert vol.iloc[-1] > 0


def test_max_drawdown():
    prices = pd.Series([100, 110, 90, 95, 80, 85], index=pd.date_range("2024-01-01", periods=6))
    dd = max_drawdown(prices)
    assert dd < 0
    assert abs(dd - (-0.2727)) < 0.01  # ~27% drawdown


def test_sharpe_ratio():
    np.random.seed(42)
    prices = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 252)),
        index=pd.date_range("2024-01-01", periods=252),
    )
    sr = sharpe_ratio(prices)
    assert not np.isnan(sr)


def test_correlation_matrix():
    np.random.seed(42)
    prices = pd.DataFrame(
        {
            "A": np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
            "B": np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
        },
        index=pd.date_range("2024-01-01", periods=100),
    )
    corr = correlation_matrix(prices)
    assert corr.shape == (2, 2)
    assert abs(corr.loc["A", "A"] - 1.0) < 1e-6


def test_beta_to_benchmark():
    np.random.seed(42)
    bench = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
        index=pd.date_range("2024-01-01", periods=100),
    )
    stock = bench * 1.1 + np.random.normal(0, 0.01, 100)
    stock = pd.Series(stock, index=bench.index)
    beta = beta_to_benchmark(stock, bench)
    assert not np.isnan(beta)
    assert beta > 0.5


def test_exp_smooth_forecast_shape():
    np.random.seed(42)
    series = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
        index=pd.date_range("2024-01-01", periods=100),
    )
    fc = exp_smooth_forecast(series, horizon=30)
    assert len(fc) == 30
    assert not fc.isnull().any().any()
    assert (fc["lower"] <= fc["forecast"]).all()
    assert (fc["forecast"] <= fc["upper"]).all()


def test_linear_forecast_shape():
    np.random.seed(42)
    series = pd.Series(
        np.cumprod(1 + np.random.normal(0.001, 0.02, 100)),
        index=pd.date_range("2024-01-01", periods=100),
    )
    fc = linear_forecast(series, horizon=30)
    assert len(fc) == 30
    assert not fc.isnull().any().any()
    assert (fc["lower"] <= fc["forecast"]).all()
    assert (fc["forecast"] <= fc["upper"]).all()
