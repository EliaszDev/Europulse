"""EU macro regime detection from macro time-series data."""

from __future__ import annotations

import json

import pandas as pd

from europulse import config


def detect_regimes(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Classify the EU macro environment into regimes.

    Input: long-format DataFrame with columns `series`, `date`, `value`.
    Output: DataFrame with columns
        date, inflation_regime, yield_curve, policy_stance,
        composite_regime, signals_json
    """
    if macro_df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "inflation_regime",
                "yield_curve",
                "policy_stance",
                "composite_regime",
                "signals_json",
            ]
        )

    df = macro_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Pivot to wide
    wide = df.pivot_table(index="date", columns="series", values="value")

    # Forward-fill missing values so thresholds can be applied row-by-row
    wide = wide.ffill()

    regimes = []
    th = config.REGIME_THRESHOLDS

    for date, row in wide.iterrows():
        # Inflation regime (EA19HICP preferred, fallback CPIAUCSL)
        hicp = row.get("EA19HICP", row.get("CPIAUCSL"))
        if pd.notna(hicp):
            if hicp > th["inflation_high"]:
                inflation = "High"
            elif hicp < th["inflation_low"]:
                inflation = "Low"
            else:
                inflation = "Target"
        else:
            inflation = "Unknown"

        # Yield curve (T10Y2Y)
        t10y2y = row.get("T10Y2Y")
        if pd.notna(t10y2y):
            yield_curve = "Inverted" if t10y2y < th["yield_curve_inverted"] else "Normal"
        else:
            yield_curve = "Unknown"

        # Policy stance (ECBMLFR preferred, fallback FEDFUNDS)
        rate = row.get("ECBMLFR", row.get("FEDFUNDS"))
        if pd.notna(rate):
            if rate > th["policy_restrictive"]:
                policy = "Restrictive"
            elif rate < th["policy_accommodative"]:
                policy = "Accommodative"
            else:
                policy = "Neutral"
        else:
            policy = "Unknown"

        # Composite regime
        composite = _composite_regime(inflation, yield_curve, policy)

        signals = {
            "hicp": None if pd.isna(hicp) else float(hicp),
            "t10y2y": None if pd.isna(t10y2y) else float(t10y2y),
            "policy_rate": None if pd.isna(rate) else float(rate),
        }

        regimes.append(
            {
                "date": date,
                "inflation_regime": inflation,
                "yield_curve": yield_curve,
                "policy_stance": policy,
                "composite_regime": composite,
                "signals_json": json.dumps(signals),
            }
        )

    return pd.DataFrame(regimes)


def _composite_regime(inflation: str, yield_curve: str, policy: str) -> str:
    """Map indicator triplet to a macro regime label."""
    # Simple heuristic matrix
    if inflation == "High" and policy == "Restrictive":
        return "Slowdown"
    if inflation == "Low" and policy == "Accommodative":
        return "Recovery"
    if yield_curve == "Inverted" and policy == "Restrictive":
        return "Contraction"
    if inflation == "Target" and yield_curve == "Normal" and policy == "Neutral":
        return "Expansion"
    if policy == "Accommodative":
        return "Recovery"
    if policy == "Restrictive":
        return "Slowdown"
    return "Expansion"
