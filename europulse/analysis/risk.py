"""UCITS-style risk metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def _log_returns(prices: pd.Series) -> pd.Series:
    """Compute daily log returns."""
    return np.log(prices / prices.shift(1)).dropna()


def rolling_volatility(prices: pd.Series, window: int = 30) -> pd.Series:
    """Annualised rolling volatility from daily log returns."""
    returns = _log_returns(prices)
    return returns.rolling(window=window).std() * np.sqrt(252)


def max_drawdown(prices: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a percentage."""
    cummax = prices.cummax()
    drawdowns = (prices - cummax) / cummax
    return float(drawdowns.min())


def sharpe_ratio(prices: pd.Series, risk_free: float = 0.02) -> float:
    """Annualised Sharpe ratio."""
    returns = _log_returns(prices)
    if returns.empty:
        return np.nan
    excess = returns.mean() * 252 - risk_free
    vol = returns.std() * np.sqrt(252)
    if vol == 0 or np.isnan(vol):
        return np.nan
    return float(excess / vol)


def correlation_matrix(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Pearson correlation of daily log returns."""
    returns = np.log(prices_df / prices_df.shift(1)).dropna()
    return returns.corr()


def beta_to_benchmark(stock: pd.Series, benchmark: pd.Series) -> float:
    """OLS regression coefficient of stock returns on benchmark returns."""
    stock_ret = _log_returns(stock)
    bench_ret = _log_returns(benchmark)

    aligned = pd.concat([stock_ret, bench_ret], axis=1).dropna()
    if aligned.empty or len(aligned) < 2:
        return np.nan

    X = aligned.iloc[:, 1].values.reshape(-1, 1)  # benchmark
    y = aligned.iloc[:, 0].values  # stock

    model = LinearRegression().fit(X, y)
    return float(model.coef_[0])
