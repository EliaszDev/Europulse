"""HTML report generator using Jinja2 + Plotly."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import jinja2
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from europulse import config
from europulse.analysis.alerts import macro_alerts, price_alerts, risk_alerts
from europulse.analysis.forecast import exp_smooth_forecast, linear_forecast
from europulse.analysis.regimes import detect_regimes
from europulse.analysis.risk import (
    beta_to_benchmark,
    correlation_matrix,
    max_drawdown,
    rolling_volatility,
    sharpe_ratio,
)

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def _load_template(name: str) -> jinja2.Template:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)))
    return env.get_template(name)


def _price_chart(prices_df: pd.DataFrame) -> str:
    """Generate normalized price chart as Plotly HTML div."""
    if prices_df.empty:
        return "<p>No price data</p>"
    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    fig = go.Figure()
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date")
        normalized = group["close"] / group["close"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=group["date"], y=normalized, mode="lines", name=ticker))
    fig.update_layout(
        title="Normalized Prices (Base = 100)",
        xaxis_title="Date",
        yaxis_title="Index",
        height=450,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _forecast_chart(prices_df: pd.DataFrame, days: int = 30) -> str:
    """Generate forecast chart for key tickers."""
    if prices_df.empty:
        return "<p>No forecast data</p>"
    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    tickers = df["ticker"].unique()[:4]  # limit to first 4
    fig = make_subplots(
        rows=(len(tickers) + 1) // 2, cols=2, subplot_titles=list(tickers), vertical_spacing=0.12
    )
    for idx, ticker in enumerate(tickers):
        group = df[df["ticker"] == ticker].sort_values("date")
        prices = group["close"]
        if len(prices) < 30:
            continue
            fc_df = exp_smooth_forecast(prices, horizon=days)
            fc = fc_df["forecast"].to_numpy()
            lower = fc_df["lower"].to_numpy()
            upper = fc_df["upper"].to_numpy()
            last_date = group["date"].iloc[-1]
            hist_dates = group["date"]
            fc_dates = pd.date_range(start=last_date + timedelta(days=1), periods=days, freq="B")
            row = idx // 2 + 1
            col = idx % 2 + 1
            fig.add_trace(
                go.Scatter(x=hist_dates, y=prices, mode="lines", name="History", line=dict(color="#0d6efd")),
                row=row, col=col,
            )
            fig.add_trace(
                go.Scatter(x=fc_dates, y=fc, mode="lines", name="Forecast", line=dict(color="#198754", dash="dash")),
                row=row, col=col,
            )
            fig.add_trace(
                go.Scatter(
                    x=list(fc_dates) + list(fc_dates[::-1]),
                    y=list(upper) + list(lower[::-1]),
                    fill="toself", fillcolor="rgba(25,135,84,0.15)",
                    line=dict(color="rgba(0,0,0,0)"), name="±1σ", showlegend=False,
                ),
                row=row, col=col,
            )
    fig.update_layout(
        height=300 * ((len(tickers) + 1) // 2),
        template="plotly_white",
        showlegend=False,
        title_text="30-Day Price Forecasts (Exponential Smoothing)",
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _macro_chart(macro_df: pd.DataFrame) -> str:
    """Generate macro chart."""
    if macro_df.empty:
        return "<p>No macro data</p>"
    df = macro_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    series_list = df["series"].unique()
    fig = make_subplots(
        rows=(len(series_list) + 1) // 2, cols=2, subplot_titles=list(series_list), vertical_spacing=0.12
    )
    for idx, series in enumerate(series_list):
        group = df[df["series"] == series].sort_values("date")
        row = idx // 2 + 1
        col = idx % 2 + 1
        fig.add_trace(
            go.Scatter(x=group["date"], y=group["value"], mode="lines", name=series, showlegend=False),
            row=row, col=col,
        )
    fig.update_layout(
        height=300 * ((len(series_list) + 1) // 2),
        template="plotly_white",
        title_text="Macro Time Series",
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def _price_rows(prices_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build price summary rows."""
    rows = []
    if prices_df.empty:
        return rows
    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    today = df["date"].max()
    w1 = today - timedelta(days=7)
    m1 = today - timedelta(days=30)
    ytd_start = pd.Timestamp(year=today.year, month=1, day=1)
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date")
        latest = group["close"].iloc[-1]
        w1_price = group[group["date"] <= w1]["close"]
        m1_price = group[group["date"] <= m1]["close"]
        ytd_price = group[group["date"] >= ytd_start]["close"]
        rows.append(
            {
                "ticker": ticker,
                "latest": latest,
                "w1": (latest / w1_price.iloc[-1] - 1) if len(w1_price) else 0.0,
                "m1": (latest / m1_price.iloc[-1] - 1) if len(m1_price) else 0.0,
                "ytd": (latest / ytd_price.iloc[0] - 1) if len(ytd_price) else 0.0,
            }
        )
    return rows


def _risk_rows(prices_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build risk summary rows."""
    rows = []
    if prices_df.empty:
        return rows
    df = prices_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    for ticker, group in df.groupby("ticker"):
        group = group.sort_values("date")
        prices = group["close"]
        if len(prices) < 30:
            continue
        vol = rolling_volatility(prices, window=30)
        dd = max_drawdown(prices)
        sharpe = sharpe_ratio(prices)
        rows.append(
            {
                "ticker": ticker,
                "vol": vol.iloc[-1] if len(vol) else 0.0,
                "dd": dd,
                "sharpe": sharpe,
                "beta": 0.0,  # populated below
            }
        )
    # Beta vs SPY
    spy_df = df[df["ticker"] == "SPY"][["date", "close"]].rename(columns={"close": "spy"})
    if not spy_df.empty:
        for row in rows:
            ticker_df = df[df["ticker"] == row["ticker"]][["date", "close"]]
            merged = ticker_df.merge(spy_df, on="date").sort_values("date")
            if len(merged) >= 30:
                row["beta"] = beta_to_benchmark(merged["close"], merged["spy"])
    return rows


def _macro_rows(macro_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build macro summary rows."""
    rows = []
    if macro_df.empty:
        return rows
    df = macro_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    for series, group in df.groupby("series"):
        group = group.sort_values("date")
        latest = group["value"].iloc[-1]
        y_ago = group[group["date"] <= (group["date"].max() - pd.Timedelta(days=365))]
        yoy = (latest / y_ago["value"].iloc[-1] - 1) if len(y_ago) else 0.0
        # Simple trend: last 3 values
        vals = group["value"].tail(3).to_numpy()
        trend = "→"
        if len(vals) >= 3:
            trend = "↑" if vals[-1] > vals[0] else "↓" if vals[-1] < vals[0] else "→"
        rows.append({"series": series, "latest": latest, "yoy": yoy, "trend": trend})
    return rows


def generate_html_report(
    db_path: str = config.DB_PATH,
    output_path: str | None = None,
    title: str = "EuroPulse Intelligence Report",
) -> str:
    """Generate a full HTML report and return the HTML string.

    If output_path is provided, also write to disk.
    """
    con = duckdb.connect(db_path, read_only=True)

    # Load data
    prices = con.execute("SELECT * FROM prices ORDER BY ticker, date").fetchdf()
    macro = con.execute("SELECT * FROM macro ORDER BY series, date").fetchdf()
    news = con.execute(
        "SELECT title, source, published, tickers FROM news ORDER BY published DESC LIMIT 10"
    ).fetchdf()
    con.close()

    # Run analysis
    regime = "Unknown"
    if not macro.empty:
        regime_df = detect_regimes(macro)
        if not regime_df.empty and "composite_regime" in regime_df.columns:
            regime = regime_df["composite_regime"].iloc[-1]

    price_alert_list = price_alerts(prices)
    macro_alert_list = macro_alerts(macro)
    risk_alert_list = risk_alerts(prices)
    all_alerts = price_alert_list + macro_alert_list + risk_alert_list

    # Compute average vol
    risk_rows = _risk_rows(prices)
    avg_vol = sum(r["vol"] for r in risk_rows) / len(risk_rows) if risk_rows else 0.0

    # Macro summary
    macro_rows = _macro_rows(macro)
    macro_summary = "N/A"
    if macro_rows:
        hicp = next((r for r in macro_rows if r["series"] == "EA19HICP"), None)
        if hicp:
            macro_summary = f"HICP {hicp['latest']:.1f}%"
        else:
            macro_summary = f"{macro_rows[0]['series']} {macro_rows[0]['latest']:.1f}"

    # News formatting
    news_items = []
    for _, row in news.iterrows():
        tickers = json.loads(row["tickers"]) if isinstance(row["tickers"], str) else row["tickers"] or []
        news_items.append(
            {
                "title": row["title"],
                "source": row["source"],
                "published": row["published"].strftime("%Y-%m-%d") if hasattr(row["published"], "strftime") else str(row["published"]),
                "tickers": tickers,
            }
        )

    # Badge for regime
    badge_map = {
        "Recovery": "success",
        "Expansion": "success",
        "Peak": "warning",
        "Contraction": "danger",
        "Stagflation": "danger",
        "Moderation": "info",
    }
    regime_badge = badge_map.get(regime, "info")

    # Render
    template = _load_template("report_template.html")
    html = template.render(
        title=title,
        report_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        data_through=prices["date"].max().strftime("%Y-%m-%d") if not prices.empty else "N/A",
        regime=regime,
        regime_badge=regime_badge,
        alert_count=len(all_alerts),
        avg_vol=f"{avg_vol * 100:.1f}%",
        macro_summary=macro_summary,
        price_chart=_price_chart(prices),
        price_rows=_price_rows(prices),
        risk_rows=risk_rows,
        forecast_chart=_forecast_chart(prices),
        alerts=all_alerts,
        macro_chart=_macro_chart(macro),
        macro_rows=macro_rows,
        news=news_items,
    )

    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")

    return html
