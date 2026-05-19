"""Baseline forecasting models."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def exp_smooth_forecast(series: pd.Series, horizon: int = 30) -> pd.DataFrame:
    """Exponential Smoothing with additive trend.

    Returns DataFrame with columns: date, forecast, lower, upper.
    """
    if series.empty or len(series) < 10:
        return pd.DataFrame(columns=["date", "forecast", "lower", "upper"])

    model = ExponentialSmoothing(
        series,
        trend="add",
        seasonal=None,
    ).fit()

    forecast = model.forecast(horizon)
    residuals = model.resid
    std_err = float(np.std(residuals.dropna()))

    last_date = pd.to_datetime(series.index[-1])
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=horizon, freq="B"
    )

    df = pd.DataFrame(
        {
            "date": future_dates.date,
            "forecast": forecast.values,
            "lower": forecast.values - std_err,
            "upper": forecast.values + std_err,
        }
    )
    return df


def linear_forecast(series: pd.Series, horizon: int = 30) -> pd.DataFrame:
    """Linear regression on integer date ordinal.

    Returns DataFrame with columns: date, forecast, lower, upper.
    """
    if series.empty or len(series) < 10:
        return pd.DataFrame(columns=["date", "forecast", "lower", "upper"])

    y = series.values
    X = np.arange(len(y)).reshape(-1, 1)

    model = LinearRegression().fit(X, y)
    preds = model.predict(X)
    residuals = y - preds
    std_err = float(np.std(residuals))

    future_X = np.arange(len(y), len(y) + horizon).reshape(-1, 1)
    forecast = model.predict(future_X)

    last_date = pd.to_datetime(series.index[-1])
    future_dates = pd.date_range(
        start=last_date + pd.Timedelta(days=1), periods=horizon, freq="B"
    )

    df = pd.DataFrame(
        {
            "date": future_dates.date,
            "forecast": forecast,
            "lower": forecast - std_err,
            "upper": forecast + std_err,
        }
    )
    return df
