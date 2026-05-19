"""EuroPulse Streamlit Dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from europulse import config
from europulse.analysis.alerts import macro_alerts, price_alerts, risk_alerts
from europulse.analysis.forecast import exp_smooth_forecast
from europulse.analysis.regimes import detect_regimes
from europulse.analysis.risk import (
    beta_to_benchmark,
    max_drawdown,
    rolling_volatility,
    sharpe_ratio,
)

st.set_page_config(page_title="EuroPulse", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_data():
    con = duckdb.connect(config.DB_PATH, read_only=True)
    prices = con.execute("SELECT * FROM prices ORDER BY ticker, date").fetchdf()
    macro = con.execute("SELECT * FROM macro ORDER BY series, date").fetchdf()
    news = con.execute(
        "SELECT title, source, published, tickers FROM news ORDER BY published DESC LIMIT 20"
    ).fetchdf()
    con.close()
    return prices, macro, news


prices_df, macro_df, news_df = load_data()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("📊 EuroPulse")
page = st.sidebar.radio(
    "Navigation",
    ["Overview", "Prices", "Risk", "Forecasts", "Alerts", "Macro", "News"],
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(df: pd.DataFrame, ticker_col: str = "ticker", price_col: str = "close") -> pd.DataFrame:
    out = []
    for t, g in df.groupby(ticker_col):
        g = g.sort_values("date").copy()
        g["norm"] = g[price_col] / g[price_col].iloc[0] * 100
        out.append(g)
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

if page == "Overview":
    st.title("EuroPulse Overview")

    col1, col2, col3, col4 = st.columns(4)
    regime = detect_regimes(macro_df) if not macro_df.empty else "N/A"
    col1.metric("Market Regime", regime)

    all_alerts = price_alerts(prices_df) + macro_alerts(macro_df) + risk_alerts(prices_df)
    col2.metric("Active Alerts", len(all_alerts))

    if not prices_df.empty:
        latest_date = prices_df["date"].max()
        col3.metric("Latest Data", str(latest_date))
    else:
        col3.metric("Latest Data", "N/A")

    col4.metric("Tickers Tracked", prices_df["ticker"].nunique() if not prices_df.empty else 0)

    st.divider()

    if not prices_df.empty:
        norm = _normalize(prices_df)
        fig = px.line(
            norm, x="date", y="norm", color="ticker",
            title="Normalized Prices (Base = 100)", template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price data available.")

    if not macro_df.empty:
        fig2 = px.line(
            macro_df, x="date", y="value", color="series",
            title="Macro Indicators", template="plotly_white",
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

elif page == "Prices":
    st.title("Price Explorer")

    if prices_df.empty:
        st.info("No price data available.")
    else:
        tickers = sorted(prices_df["ticker"].unique())
        selected = st.multiselect("Select tickers", tickers, default=tickers[:4])
        subset = prices_df[prices_df["ticker"].isin(selected)]

        fig = px.line(
            subset, x="date", y="close", color="ticker",
            title="Close Prices", template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Returns table
        today = subset["date"].max()
        w1 = today - timedelta(days=7)
        m1 = today - timedelta(days=30)
        returns = []
        for t, g in subset.groupby("ticker"):
            g = g.sort_values("date")
            latest = g["close"].iloc[-1]
            w1_price = g[g["date"] <= w1]["close"]
            m1_price = g[g["date"] <= m1]["close"]
            returns.append(
                {
                    "ticker": t,
                    "latest": latest,
                    "1W": f"{(latest / w1_price.iloc[-1] - 1) * 100:.2f}%" if len(w1_price) else "N/A",
                    "1M": f"{(latest / m1_price.iloc[-1] - 1) * 100:.2f}%" if len(m1_price) else "N/A",
                }
            )
        st.dataframe(pd.DataFrame(returns), use_container_width=True)

# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

elif page == "Risk":
    st.title("Risk Metrics")

    if prices_df.empty:
        st.info("No price data available.")
    else:
        window = st.slider("Rolling window (days)", 10, 252, 30)
        risk_data = []
        for t, g in prices_df.groupby("ticker"):
            g = g.sort_values("date")
            prices = g["close"].to_numpy()
            if len(prices) < window:
                continue
            vol = rolling_volatility(prices, window=window)
            dd = max_drawdown(prices)
            sharpe = sharpe_ratio(prices)
            risk_data.append(
                {
                    "ticker": t,
                    "volatility": vol[-1] * 100,
                    "max_drawdown": dd * 100,
                    "sharpe": sharpe,
                }
            )

        if risk_data:
            risk_df = pd.DataFrame(risk_data)
            st.dataframe(risk_df, use_container_width=True)

            fig = px.bar(
                risk_df, x="ticker", y="volatility",
                title=f"{window}-Day Annualized Volatility", template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for risk calculations.")

# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------

elif page == "Forecasts":
    st.title("Price Forecasts")

    if prices_df.empty:
        st.info("No price data available.")
    else:
        tickers = sorted(prices_df["ticker"].unique())
        selected = st.selectbox("Select ticker", tickers)
        horizon = st.slider("Forecast horizon (days)", 5, 60, 30)

        group = prices_df[prices_df["ticker"] == selected].sort_values("date")
        prices = group["close"].to_numpy()

        if len(prices) < 30:
            st.warning("Need at least 30 data points for forecasting.")
        else:
            fc, lower, upper = exp_smooth_forecast(prices, horizon=horizon)
            last_date = group["date"].iloc[-1]
            hist_dates = group["date"]
            fc_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon, freq="B")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_dates, y=prices, mode="lines", name="History"))
            fig.add_trace(go.Scatter(x=fc_dates, y=fc, mode="lines", name="Forecast", line=dict(dash="dash")))
            fig.add_trace(
                go.Scatter(
                    x=list(fc_dates) + list(fc_dates[::-1]),
                    y=list(upper) + list(lower[::-1]),
                    fill="toself", fillcolor="rgba(0,100,80,0.15)",
                    line=dict(color="rgba(0,0,0,0)"), name="±1σ",
                )
            )
            fig.update_layout(
                title=f"{selected} — {horizon}-Day Forecast", template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.metric("Current Price", f"{prices[-1]:.2f}")
            st.metric("Forecast (end)", f"{fc[-1]:.2f}", delta=f"{(fc[-1] / prices[-1] - 1) * 100:.2f}%")

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

elif page == "Alerts":
    st.title("Alert Center")

    p_alerts = price_alerts(prices_df)
    m_alerts = macro_alerts(macro_df)
    r_alerts = risk_alerts(prices_df)
    all_alerts = p_alerts + m_alerts + r_alerts

    tab1, tab2, tab3 = st.tabs(["Price", "Macro", "Risk"])
    with tab1:
        if p_alerts:
            st.dataframe(pd.DataFrame(p_alerts), use_container_width=True)
        else:
            st.success("No price alerts.")
    with tab2:
        if m_alerts:
            st.dataframe(pd.DataFrame(m_alerts), use_container_width=True)
        else:
            st.success("No macro alerts.")
    with tab3:
        if r_alerts:
            st.dataframe(pd.DataFrame(r_alerts), use_container_width=True)
        else:
            st.success("No risk alerts.")

    if all_alerts:
        st.divider()
        st.subheader("All Alerts")
        st.dataframe(pd.DataFrame(all_alerts), use_container_width=True)

# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------

elif page == "Macro":
    st.title("Macro Dashboard")

    if macro_df.empty:
        st.info("No macro data available.")
    else:
        series = sorted(macro_df["series"].unique())
        selected = st.multiselect("Select series", series, default=series)
        subset = macro_df[macro_df["series"].isin(selected)]

        fig = px.line(
            subset, x="date", y="value", color="series",
            title="Macro Time Series", template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Latest values
        latest = subset.groupby("series").last().reset_index()
        st.dataframe(latest[["series", "date", "value"]], use_container_width=True)

# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

elif page == "News":
    st.title("Recent News")

    if news_df.empty:
        st.info("No news data available. Run fetch_news.py to populate.")
    else:
        for _, row in news_df.iterrows():
            tickers = json.loads(row["tickers"]) if isinstance(row["tickers"], str) else row["tickers"] or []
            with st.container():
                st.markdown(f"**{row['title']}**")
                st.caption(f"{row['source']} | {row['published']}")
                if tickers:
                    st.markdown(
                        " ".join([f"`{t}`" for t in tickers])
                    )
                st.divider()
