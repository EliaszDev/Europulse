"""Generate static chart assets for README screenshots.

Requires kaleido (listed in project[dev] dependencies).
  $ pip install -e ".[dev]"
  $ python scripts/generate_screenshots.py
"""

from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _random_walk(n: int, start: float = 100.0, sigma: float = 0.02) -> pd.Series:
    """Generate a synthetic price series."""
    rng = np.random.default_rng(42)
    returns = rng.normal(0, sigma, n)
    prices = start * np.exp(np.cumsum(returns))
    dates = pd.date_range(end=datetime.today(), periods=n, freq="B")
    return pd.Series(prices, index=dates)


def generate_regime_chart() -> None:
    """Save a sample regime-detection chart to assets/."""
    prices = _random_walk(252)
    # Simple moving-average regime
    short_ma = prices.rolling(20).mean()
    long_ma = prices.rolling(50).mean()
    regime = np.where(short_ma > long_ma, "Bull", "Bear")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=prices.index, y=prices, mode="lines", name="Price"))
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=short_ma,
            mode="lines",
            name="MA(20)",
            line=dict(color="orange"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=long_ma,
            mode="lines",
            name="MA(50)",
            line=dict(color="green"),
        )
    )
    fig.update_layout(
        title="Regime Detection — Sample Ticker",
        xaxis_title="Date",
        yaxis_title="Price (EUR)",
        template="plotly_white",
    )
    fig.write_image(str(ASSETS_DIR / "regime_chart.png"), width=1200, height=600, scale=2)
    print("  -> assets/regime_chart.png")


def generate_risk_heatmap() -> None:
    """Save a sample risk heatmap to assets/."""
    tickers = ["SX5E", "SXXP", "EXW1", "CAC40", "DAX"]
    metrics = ["Volatility", "VaR (95%)", "Max Drawdown", "Beta"]
    rng = np.random.default_rng(7)
    z = rng.uniform(0, 1, size=(len(tickers), len(metrics)))
    z = np.round(z, 2)

    fig = px.imshow(
        z,
        x=metrics,
        y=tickers,
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        title="Risk Heatmap — Sample Basket",
    )
    fig.update_layout(template="plotly_white")
    fig.write_image(str(ASSETS_DIR / "risk_heatmap.png"), width=1000, height=500, scale=2)
    print("  -> assets/risk_heatmap.png")


def generate_forecast_chart() -> None:
    """Save a sample forecast chart to assets/."""
    n_hist = 180
    n_fore = 30
    hist = _random_walk(n_hist)
    last_price = hist.iloc[-1]
    dates_hist = hist.index
    dates_fore = pd.date_range(start=dates_hist[-1] + timedelta(days=1), periods=n_fore, freq="B")

    rng = np.random.default_rng(99)
    forecast = last_price * np.exp(np.cumsum(rng.normal(0.0005, 0.015, n_fore)))
    upper = forecast * 1.05
    lower = forecast * 0.95

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=dates_hist, y=hist, mode="lines", name="Historical", line=dict(color="blue"))
    )
    fig.add_trace(
        go.Scatter(
            x=dates_fore,
            y=forecast,
            mode="lines",
            name="Forecast",
            line=dict(color="orange", dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(dates_fore) + list(dates_fore[::-1]),
            y=list(upper) + list(lower[::-1]),
            fill="toself",
            fillcolor="rgba(255,165,0,0.2)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95 % CI",
        )
    )
    fig.add_vline(x=dates_hist[-1], line_width=2, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="Exp-Smooth Forecast — Sample Ticker",
        xaxis_title="Date",
        yaxis_title="Price (EUR)",
        template="plotly_white",
    )
    fig.write_image(str(ASSETS_DIR / "forecast_chart.png"), width=1200, height=600, scale=2)
    print("  -> assets/forecast_chart.png")


def generate_sample_report() -> None:
    """Save a minimal sample HTML report to assets/."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EuroPulse Sample Report</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;line-height:1.5;color:#333}
h1{color:#1f77b4}h2{border-bottom:1px solid #ddd;padding-bottom:.25rem}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.5rem;border-bottom:1px solid #eee}
th{background:#f6f8fa}
</style>
</head>
<body>
<h1>🇪🇺 EuroPulse Daily Intelligence Report</h1>
<p><strong>Date:</strong> 2026-05-21 &nbsp;|&nbsp; <strong>Status:</strong> 🟢 All systems operational</p>

<h2>📈 Market Snapshot</h2>
<table>
<tr><th>Ticker</th><th>Price</th><th>1D Change</th><th>RSI</th></tr>
<tr><td>SX5E</td><td>4,850.20</td><td>+0.42 %</td><td>58.3</td></tr>
<tr><td>SXXP</td><td>520.15</td><td>-0.11 %</td><td>49.7</td></tr>
<tr><td>EXW1.DE</td><td>142.80</td><td>+0.85 %</td><td>62.1</td></tr>
</table>

<h2>🔍 LLM Summary</h2>
<p>European equities showed resilience amid mixed macro signals. The ECB rate-cut
expectations have shifted to Q3, supporting the EUR/USD near-term floor.</p>

<h2>⚠️ Risk Alerts</h2>
<ul>
<li>SX5E volatility spiked above the 30-day rolling average.</li>
<li>None of the tracked tickers hit overbought / oversold RSI thresholds.</li>
</ul>

<p style="margin-top:2rem;font-size:.85rem;color:#666">Generated by EuroPulse v0.1.0</p>
</body>
</html>"""
    path = ASSETS_DIR / "sample_report.html"
    path.write_text(html, encoding="utf-8")
    print(f"  -> {path}")


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating screenshot assets...")
    generate_regime_chart()
    generate_risk_heatmap()
    generate_forecast_chart()
    generate_sample_report()
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
