"""EuroPulse Streamlit Dashboard."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from europulse import config

load_dotenv()
from europulse.analysis.forecast import exp_smooth_forecast, linear_forecast
from europulse.analysis.regimes import detect_regimes
from europulse.analysis.risk import (
    beta_to_benchmark,
    correlation_matrix,
    max_drawdown,
    rolling_volatility,
    sharpe_ratio,
)
from europulse.llm.synthesizer import (
    chat_with_data,
    generate_regime_narrative,
    generate_risk_summary,
)

st.set_page_config(page_title="EuroPulse", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_data():
    """Load prices, macro, and news from DuckDB."""
    con = duckdb.connect(config.DB_PATH, read_only=True)
    try:
        prices = con.execute(
            "SELECT ticker, date, open, high, low, close, volume FROM prices ORDER BY ticker, date"
        ).fetchdf()
        macro = con.execute(
            "SELECT series, date, value FROM macro ORDER BY series, date"
        ).fetchdf()
    finally:
        con.close()
    return prices, macro


try:
    prices_df, macro_df = load_data()
except Exception as e:
    st.error(f"Failed to load database: {e}")
    prices_df = pd.DataFrame(
        columns=["ticker", "date", "open", "high", "low", "close", "volume"]
    )
    macro_df = pd.DataFrame(columns=["series", "date", "value"])


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("📊 EuroPulse")

available_tickers = sorted(prices_df["ticker"].unique()) if not prices_df.empty else config.ALL_PRICE_TICKERS
selected_tickers = st.sidebar.multiselect(
    "Tickers",
    options=available_tickers,
    default=available_tickers[: min(4, len(available_tickers))],
)

min_date = prices_df["date"].min() if not prices_df.empty else date.today() - timedelta(days=365)
max_date = prices_df["date"].max() if not prices_df.empty else date.today()
start_date = st.sidebar.date_input("Start date", min_date)
end_date = st.sidebar.date_input("End date", max_date)

if not prices_df.empty:
    prices_df["date"] = pd.to_datetime(prices_df["date"]).dt.date
    filtered_prices = prices_df[
        (prices_df["ticker"].isin(selected_tickers))
        & (prices_df["date"] >= start_date)
        & (prices_df["date"] <= end_date)
    ].copy()
else:
    filtered_prices = prices_df


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tabs = st.tabs(["Macro & Regimes", "Risk & Correlation", "Forecast", "Research Assistant"])

# ---------------------------------------------------------------------------
# Tab 1 — Macro & Regimes
# ---------------------------------------------------------------------------

with tabs[0]:
    st.header("Macro & Regimes")

    if not macro_df.empty:
        regime_df = detect_regimes(macro_df)

        if not regime_df.empty:
            fig = px.line(
                regime_df,
                x="date",
                y="composite_regime",
                title="Composite Regime Over Time",
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                regime_df[["date", "composite_regime", "signals_json"]].tail(10),
                width="stretch",
            )

            with st.spinner("Generating AI narrative..."):
                narrative = generate_regime_narrative(regime_df)
            st.markdown("**AI Narrative**")
            st.info(narrative)
        else:
            st.info("No regime data available.")
    else:
        st.info("No macro data available.")

# ---------------------------------------------------------------------------
# Tab 2 — Risk & Correlation
# ---------------------------------------------------------------------------

with tabs[1]:
    st.header("Risk & Correlation")

    if not filtered_prices.empty:
        window = st.slider("Rolling window (days)", 10, 252, 30, key="risk_window")

        risk_data = []
        pivot = filtered_prices.pivot(index="date", columns="ticker", values="close")
        spy_series = pivot.get("SPY")

        for t, g in filtered_prices.groupby("ticker"):
            g = g.sort_values("date")
            prices = g["close"]
            if len(prices) < window:
                continue
            vol = rolling_volatility(prices, window=window)
            dd = max_drawdown(prices)
            sharpe = sharpe_ratio(prices)

            beta = None
            if spy_series is not None and t != "SPY":
                asset_series = pivot.get(t)
                if asset_series is not None:
                    aligned = pd.concat([asset_series, spy_series], axis=1).dropna()
                    aligned.columns = ["asset", "spy"]
                    if len(aligned) >= window:
                        beta = beta_to_benchmark(aligned["asset"], aligned["spy"])

            risk_data.append(
                {
                    "ticker": t,
                    "volatility": vol.iloc[-1] * 100,
                    "max_drawdown": dd * 100,
                    "sharpe": sharpe,
                    "beta": beta,
                }
            )

        if risk_data:
            risk_df = pd.DataFrame(risk_data)
            st.dataframe(risk_df, width="stretch")

            # Correlation heatmap
            if len(pivot.columns) > 1:
                corr = correlation_matrix(pivot)
                fig = px.imshow(
                    corr,
                    text_auto=".2f",
                    aspect="auto",
                    title="Correlation Heatmap",
                    template="plotly_white",
                )
                st.plotly_chart(fig, use_container_width=True)

            with st.spinner("Generating AI risk summary..."):
                summary = generate_risk_summary(risk_df)
            st.markdown("**AI Risk Summary**")
            st.info(summary)
        else:
            st.info("Not enough data for risk calculations.")
    else:
        st.info("No price data available.")

# ---------------------------------------------------------------------------
# Tab 3 — Forecast
# ---------------------------------------------------------------------------

with tabs[2]:
    st.header("Forecast")

    if not filtered_prices.empty:
        tickers = sorted(filtered_prices["ticker"].unique())
        selected = st.selectbox("Select ticker", tickers, key="fc_ticker")
        horizon = st.slider("Forecast horizon (days)", 5, 60, 30, key="fc_horizon")
        model_choice = st.radio(
            "Forecast model",
            ["Exponential Smoothing", "Linear Regression"],
            key="fc_model",
        )

        group = filtered_prices[filtered_prices["ticker"] == selected].sort_values("date")
        prices = group["close"]

        if len(prices) < 30:
            st.warning("Need at least 30 data points for forecasting.")
        else:
            if model_choice == "Exponential Smoothing":
                fc_df = exp_smooth_forecast(prices, horizon=horizon)
            else:
                fc_df = linear_forecast(prices, horizon=horizon)

            fc = fc_df["forecast"].to_numpy()
            lower = fc_df["lower"].to_numpy()
            upper = fc_df["upper"].to_numpy()
            last_date = group["date"].iloc[-1]
            hist_dates = pd.to_datetime(group["date"])
            fc_dates = pd.date_range(
                start=pd.to_datetime(last_date) + timedelta(days=1),
                periods=horizon,
                freq="B",
            )

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist_dates, y=prices, mode="lines", name="History"))
            fig.add_trace(
                go.Scatter(
                    x=fc_dates, y=fc, mode="lines", name="Forecast", line=dict(dash="dash")
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=list(fc_dates) + list(fc_dates[::-1]),
                    y=list(upper) + list(lower[::-1]),
                    fill="toself",
                    fillcolor="rgba(0,100,80,0.15)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="±1σ",
                )
            )
            fig.update_layout(
                title=f"{selected} — {horizon}-Day Forecast ({model_choice})",
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.metric("Current Price", f"{prices.iloc[-1]:.2f}")
            st.metric(
                "Forecast (end)",
                f"{fc[-1]:.2f}",
                delta=f"{(fc[-1] / prices.iloc[-1] - 1) * 100:.2f}%",
            )
    else:
        st.info("No price data available.")

# ---------------------------------------------------------------------------
# Tab 4 — Research Assistant
# ---------------------------------------------------------------------------

with tabs[3]:
    st.header("Research Assistant")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Ask about European markets...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.spinner("Thinking..."):
            answer = chat_with_data(user_query, top_k=5)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
