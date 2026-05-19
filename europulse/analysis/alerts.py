"""Threshold-based alert generation for prices, risk, and macro signals."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from europulse import config


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Compute RSI for a price series."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def price_alerts(prices_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Generate alerts from price data (RSI, volume spikes).

    Input: long-format DataFrame with columns ticker, date, close, volume.
    Returns list of alert dicts with keys: type, ticker, date, message, severity.
    """
    alerts = []
    if prices_df.empty or "close" not in prices_df.columns:
        return alerts

    th = config.ALERT_THRESHOLDS
    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date")
        closes = group["close"]
        volumes = group["volume"] if "volume" in group.columns else pd.Series(dtype=float)

        if len(closes) >= 14:
            rsi_vals = _rsi(closes)
            latest_rsi = rsi_vals.iloc[-1]
            latest_date = group["date"].iloc[-1]

            if pd.notna(latest_rsi):
                if latest_rsi > th["rsi_overbought"]:
                    alerts.append(
                        {
                            "type": "RSI_OVERBOUGHT",
                            "ticker": ticker,
                            "date": latest_date,
                            "message": f"RSI {latest_rsi:.1f} > {th['rsi_overbought']}",
                            "severity": "warning",
                            "value": float(latest_rsi),
                        }
                    )
                elif latest_rsi < th["rsi_oversold"]:
                    alerts.append(
                        {
                            "type": "RSI_OVERSOLD",
                            "ticker": ticker,
                            "date": latest_date,
                            "message": f"RSI {latest_rsi:.1f} < {th['rsi_oversold']}",
                            "severity": "warning",
                            "value": float(latest_rsi),
                        }
                    )

        if len(volumes) >= 2 and pd.notna(volumes.iloc[-1]) and pd.notna(volumes.iloc[-2]):
            latest_vol = volumes.iloc[-1]
            prev_vol = volumes.iloc[-2]
            if prev_vol > 0:
                spike = latest_vol / prev_vol
                if spike > th["volume_spike"]:
                    alerts.append(
                        {
                            "type": "VOLUME_SPIKE",
                            "ticker": ticker,
                            "date": group["date"].iloc[-1],
                            "message": f"Volume {spike:.1f}x vs prior day",
                            "severity": "info",
                            "value": float(spike),
                        }
                    )

    return alerts


def macro_alerts(macro_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Generate alerts from macro time-series data.

    Input: long-format DataFrame with columns series, date, value.
    Returns list of alert dicts.
    """
    alerts = []
    if macro_df.empty:
        return alerts

    df = macro_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    th = config.REGIME_THRESHOLDS

    for series_name, group in df.groupby("series"):
        group = group.sort_values("date")
        latest = group.iloc[-1]
        val = latest["value"]
        date = latest["date"]

        if pd.isna(val):
            continue

        if series_name == "EA19HICP":
            if val > th["inflation_high"]:
                alerts.append(
                    {
                        "type": "INFLATION_HIGH",
                        "series": series_name,
                        "date": date,
                        "message": f"HICP {val:.2f}% > {th['inflation_high']}%",
                        "severity": "critical",
                        "value": float(val),
                    }
                )
            elif val < th["inflation_low"]:
                alerts.append(
                    {
                        "type": "INFLATION_LOW",
                        "series": series_name,
                        "date": date,
                        "message": f"HICP {val:.2f}% < {th['inflation_low']}%",
                        "severity": "warning",
                        "value": float(val),
                    }
                )

        elif series_name == "T10Y2Y":
            if val < th["yield_curve_inverted"]:
                alerts.append(
                    {
                        "type": "YIELD_CURVE_INVERTED",
                        "series": series_name,
                        "date": date,
                        "message": f"10Y-2Y spread {val:.2f}% < {th['yield_curve_inverted']}%",
                        "severity": "critical",
                        "value": float(val),
                    }
                )

        elif series_name in ("ECBMLFR", "FEDFUNDS"):
            if val > th["policy_restrictive"]:
                alerts.append(
                    {
                        "type": "POLICY_RESTRICTIVE",
                        "series": series_name,
                        "date": date,
                        "message": f"Policy rate {val:.2f}% > {th['policy_restrictive']}%",
                        "severity": "warning",
                        "value": float(val),
                    }
                )
            elif val < th["policy_accommodative"]:
                alerts.append(
                    {
                        "type": "POLICY_ACCOMMODATIVE",
                        "series": series_name,
                        "date": date,
                        "message": f"Policy rate {val:.2f}% < {th['policy_accommodative']}%",
                        "severity": "info",
                        "value": float(val),
                    }
                )

    return alerts


def risk_alerts(prices_df: pd.DataFrame, drawdown_threshold: float = -0.10) -> list[dict[str, Any]]:
    """Generate risk alerts from price data (drawdown).

    Returns list of alert dicts when max drawdown exceeds threshold.
    """
    alerts = []
    if prices_df.empty or "close" not in prices_df.columns:
        return alerts

    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date")
        prices = group["close"]
        if len(prices) < 2:
            continue

        cummax = prices.cummax()
        drawdowns = (prices - cummax) / cummax
        max_dd = drawdowns.min()
        dd_date = group.loc[drawdowns.idxmin(), "date"]

        if pd.notna(max_dd) and max_dd <= drawdown_threshold:
            alerts.append(
                {
                    "type": "MAX_DRAWDOWN",
                    "ticker": ticker,
                    "date": dd_date,
                    "message": f"Max drawdown {max_dd:.2%} (threshold {drawdown_threshold:.0%})",
                    "severity": "critical" if max_dd < -0.20 else "warning",
                    "value": float(max_dd),
                }
            )

    return alerts


def serialize_alerts(alerts: list[dict[str, Any]]) -> str:
    """Convert alerts to JSON string for storage."""
    return json.dumps(alerts, default=str)
