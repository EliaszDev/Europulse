"""Central configuration for EuroPulse."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tickers
# ---------------------------------------------------------------------------

GPW_TICKERS: list[str] = [
    "PKN.WA",
    "CDR.WA",
    "PKO.WA",
    "PZU.WA",
    "LPP.WA",
    "KGH.WA",
    "ALE.WA",
    "DNP.WA",
]

EU_TICKERS: list[str] = [
    "^STOXX50E",
    "EZU",
    "^FTSE",
    "^GDAXI",
    "^FCHI",
]

GLOBAL_TICKERS: list[str] = [
    "SPY",
    "QQQ",
    "^VIX",
    "GLD",
    "TLT",
]

FX_TICKERS: list[str] = [
    "EURPLN=X",
    "USDPLN=X",
    "EURUSD=X",
]

ALL_PRICE_TICKERS: list[str] = GPW_TICKERS + EU_TICKERS + GLOBAL_TICKERS + FX_TICKERS

# ---------------------------------------------------------------------------
# Macro series
# ---------------------------------------------------------------------------

FRED_SERIES: list[str] = [
    "FEDFUNDS",
    "T10Y2Y",
    "CPIAUCSL",
    "UNRATE",
    "BAMLH0A0HYM2",
    "VIXCLS",
    "TMBMKIT-10Y",
    "TMBMKDE-10Y",
]

ECB_SERIES: list[str] = [
    "ECBMLFR",
    "EA19HICP",
]

# ---------------------------------------------------------------------------
# News RSS feeds
# ---------------------------------------------------------------------------

RSS_FEEDS: dict[str, str] = {
    "Reuters Business": "https://feeds.reuters.com/reuters/businessNews",
    "FT Markets": "https://www.ft.com/?format=rss",
}

# ---------------------------------------------------------------------------
# Ticker aliases for mention tagging
# ---------------------------------------------------------------------------

TICKER_ALIASES: dict[str, list[str]] = {
    "PKN.WA": ["PKN", "PKN Orlen", "Orlen"],
    "CDR.WA": ["CDR", "CD Projekt", "CD Projekt Red"],
    "PKO.WA": ["PKO", "PKO BP", "PKO Bank Polski"],
    "PZU.WA": ["PZU"],
    "LPP.WA": ["LPP"],
    "KGH.WA": ["KGH", "KGHM", "KGHM Polska Miedz"],
    "ALE.WA": ["ALE", "Allegro"],
    "DNP.WA": ["DNP", "Dino Polska"],
    "SPY": ["S\u0026P 500", "SPY"],
    "QQQ": ["Nasdaq 100", "QQQ"],
    "GLD": ["Gold", "GLD"],
    "TLT": ["Treasury", "TLT"],
    "^VIX": ["VIX", "volatility index"],
}

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

REGIME_THRESHOLDS: dict[str, float] = {
    "inflation_high": 3.0,
    "inflation_low": 1.5,
    "policy_restrictive": 2.5,
    "policy_accommodative": 0.5,
    "yield_curve_inverted": 0.0,
}

RISK_WINDOWS: dict[str, int] = {
    "volatility": 30,
    "drawdown": 252,
}

ALERT_THRESHOLDS: dict[str, float] = {
    "vix_high": 30.0,
    "yield_curve_inversion_days": 30.0,
    "gpw_drawdown_pct": 15.0,
    "eurpln_high": 4.50,
    "rsi_overbought": 70.0,
    "rsi_oversold": 30.0,
    "volume_spike": 2.0,
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DB_PATH: str = "data/europulse.duckdb"
CHROMA_PATH: str = "data/chroma"
NEWS_RAW_DIR: str = "data/news_raw"
REPORTS_DIR: str = "reports"
