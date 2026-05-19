# EuroPulse

> Zero-GPU European financial intelligence platform — local RAG pipeline, LLM-powered synthesis, automated daily reporting.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-FFF000?style=flat-square&logo=duckdb&logoColor=black)](https://duckdb.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/cloud)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Free_Tier-6366f1?style=flat-square)](https://openrouter.ai)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

---

## Overview

EuroPulse ingests multi-source European financial data, runs a local RAG pipeline on financial news, and uses an LLM to generate macro regime narratives, risk summaries, and alert explanations — all without a GPU, at zero monthly cost.

Built to demonstrate production-level AI/ML engineering practices relevant to European fund administration, sovereign debt analysis, and UCITS-style risk reporting.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  yfinance (OHLCV)  │  FRED / ECB SDW (macro)  │  RSS (news)    │
└────────────┬────────────────────┬──────────────────┬────────────┘
             │                    │                  │
             ▼                    ▼                  ▼
┌─────────────────────┐  ┌──────────────┐  ┌────────────────────┐
│   ingestion layer   │  │  macro.py    │  │    news.py         │
│   prices.py         │  │  (FRED+ECB)  │  │  (RSS+trafilatura) │
│   quality.py        │  └──────┬───────┘  └────────┬───────────┘
└──────────┬──────────┘         │                   │
           │                    │                   ▼
           ▼                    ▼          ┌────────────────────┐
┌──────────────────────────────────┐       │   rag.py           │
│           DuckDB                 │       │   ChromaDB         │
│  prices │ macro │ alerts │ cache │       │   MiniLM-L6-v2     │
└──────────────────┬───────────────┘       └────────┬───────────┘
                   │                                │
                   ▼                                ▼
┌──────────────────────────────────────────────────────────────┐
│                     ANALYSIS LAYER                           │
│   regimes.py (EU macro regime)  │  risk.py (UCITS metrics)  │
│   forecast.py (baseline models) │  alerts.py (thresholds)   │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                         │
│   llm_client.py (OpenRouter + DuckDB cache + fallback)       │
│   synthesizer.py (narrative / risk / chat / alerts)          │
└───────────────────────┬──────────────────────────────────────┘
                        │
           ┌────────────┴──────────────┐
           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│   Streamlit UI      │     │   HTML / PDF report  │
│   4-tab dashboard   │     │   Jinja2 + weasyprint│
│   RAG chat          │     │   GitHub Actions     │
└─────────────────────┘     └─────────────────────┘
```

---

## Features

**ETL & Storage**
- Multi-source ingestion: GPW equities, EU indices, FX rates, FRED macro series, ECB rates, RSS news feeds
- DuckDB for structured data (prices, macro, alerts, LLM cache, logs) — single portable file
- Incremental (`--incremental`) and full backfill (`--backfill`) ingestion modes
- Data quality validation: stale tickers, missing trading days, zero-volume detection

**Analysis**
- EU macro regime detection (inflation, yield curve, ECB policy stance → composite `Expansion / Slowdown / Contraction / Recovery`)
- UCITS-style risk metrics: rolling volatility, max drawdown, Sharpe ratio, correlation matrix, beta to benchmark
- Baseline price forecasting: Exponential Smoothing and Linear Regression with confidence bands
- Threshold-based alert system: VIX spike, yield curve inversion, GPW drawdown, PLN weakness

**AI / RAG**
- Local embeddings with `sentence-transformers/all-MiniLM-L6-v2` (~80 MB, CPU-only)
- ChromaDB vector store with ticker-mention metadata filtering
- Full-text news extraction via `trafilatura`
- LLM synthesis via OpenRouter (`deepseek/deepseek-r1:free`): regime narratives, risk summaries, alert explanations, data chat
- Prompt-level DuckDB cache — repeated queries return instantly at $0 cost
- Template fallback ensures the UI never breaks on rate limits or API outages

**Interface & Reporting**
- Streamlit dashboard: regime timeline, correlation heatmap, forecast chart, risk table
- RAG-powered chat tab with source citations (URL + published date)
- Jinja2 HTML reports with embedded charts; optional WeasyPrint PDF export
- GitHub Actions CI/CD: runs ETL + report generation every weekday at 07:00 UTC

---

## Quickstart

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Free [OpenRouter](https://openrouter.ai) API key

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/europulse
cd europulse

uv sync

cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Run

```bash
# Full historical ingestion (first run)
uv run python scripts/ingest_all.py --backfill

# Launch dashboard
uv run streamlit run europulse/ui/app.py
```

Open `http://localhost:8501` in your browser.

### Daily incremental update

```bash
uv run python scripts/ingest_all.py --incremental
uv run python scripts/generate_report.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key — free tier sufficient |
| `OLLAMA_BASE_URL` | No | Optional local LLM fallback (e.g. `http://localhost:11434`) |

---

## Data Sources

| Source | Data | Cost |
|---|---|---|
| `yfinance` | OHLCV prices for GPW, EU indices, global benchmarks, FX | Free |
| FRED (via `pandas-datareader`) | `FEDFUNDS`, `T10Y2Y`, `CPIAUCSL`, `UNRATE`, HY spreads, VIX | Free |
| ECB SDW | `ECBMLFR` (ECB lending rate), `EA19HICP` (Euro area inflation) | Free |
| Reuters / FT RSS | Financial news headlines + full-text via trafilatura | Free |

Sovereign spread proxy (Italy 10Y minus Germany 10Y) is computed in the analysis layer from FRED series `TMBMKIT-10Y` and `TMBMKDE-10Y`.

---

## Project Structure

```
europulse/
├── europulse/
│   ├── config.py              # tickers, thresholds, RSS feeds
│   ├── ingestion/
│   │   ├── db.py              # DuckDB connection + schema + upsert helpers
│   │   ├── prices.py          # yfinance OHLCV ingestion
│   │   ├── macro.py           # FRED + ECB macro ingestion
│   │   ├── news.py            # RSS fetch + trafilatura full-text
│   │   └── quality.py         # stale data, missing dates, zero-volume checks
│   ├── analysis/
│   │   ├── regimes.py         # EU macro regime detection
│   │   ├── risk.py            # volatility, drawdown, Sharpe, beta, correlation
│   │   ├── forecast.py        # ExponentialSmoothing + LinearRegression baselines
│   │   └── alerts.py          # threshold-based alert rules
│   ├── intelligence/
│   │   ├── rag.py             # ChromaDB embed, upsert, query, ticker tagging
│   │   ├── llm_client.py      # OpenRouter client with DuckDB cache + fallback
│   │   ├── prompts.py         # typed prompt-builder functions
│   │   └── synthesizer.py     # regime narrative, risk summary, chat, alerts
│   ├── reporting/
│   │   ├── html_generator.py  # Jinja2 → HTML report
│   │   └── pdf_generator.py   # optional WeasyPrint PDF export
│   └── ui/
│       └── app.py             # Streamlit 4-tab dashboard + RAG chat
├── scripts/
│   ├── ingest_all.py          # ETL entrypoint (--incremental / --backfill)
│   └── generate_report.py     # builds daily HTML report
├── templates/
│   └── report_template.html   # Jinja2 base template
├── tests/
│   ├── test_ingestion.py
│   ├── test_analysis.py
│   ├── test_intelligence.py   # mock LLM + RAG
│   └── test_quality.py
├── .github/workflows/
│   └── daily_refresh.yml      # weekday 07:00 UTC ETL + report
├── pyproject.toml
└── .env.example
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

Tests use in-memory DuckDB and `respx` to mock HTTP calls — no API key required.

---

## Cost

| Component | Monthly cost |
|---|---|
| yfinance, FRED, RSS | $0 |
| DuckDB + ChromaDB (file-based) | $0 |
| MiniLM-L6-v2 embeddings (CPU) | $0 |
| OpenRouter free tier (200 req/day) | $0 |
| Streamlit Cloud | $0 |
| GitHub Actions (public repo) | $0 |
| **Total** | **$0** |

Upgrading to a paid OpenRouter model costs approximately $1–3/month for personal use.

---

## Luxembourg & EU Fund Administration Relevance

EuroPulse tracks the data that matters most to European fund administrators:

- **ECB policy regime** — marginal lending facility rate and its implications for fixed-income portfolios
- **Sovereign spread (IT–DE 10Y)** — a key risk indicator for Euro area credit exposure
- **UCITS-style risk metrics** — volatility, drawdown, and Sharpe ratio computed against `^STOXX50E` as benchmark
- **PLN/EUR dynamics** — relevant for cross-border funds with Polish asset exposure under Luxembourg CSSF oversight

---

## Hardware Notes

Tested on Ryzen 7 3700X / AMD RX 5500 XT 8 GB VRAM / 32 GB RAM.
No GPU is required for any part of the core pipeline. All embeddings run on CPU (~2–3 seconds per batch). LLM inference is API-based via OpenRouter.

---

## Roadmap

- [ ] FinBERT sentiment scoring on news chunks before embedding (`ProsusAI/finbert`, CPU, ~150 MB)
- [ ] NBP (Polish National Bank) free API for official PLN cross-rates
- [ ] Luxembourg Stock Exchange (LuxSE) tickers
- [ ] FastAPI webhook endpoint to forward regime-shift alerts to Discord / Slack
- [ ] Paid OpenRouter model upgrade (`deepseek/deepseek-chat`, `moonshotai/kimi-k2.6`)

---

## License

MIT — see [LICENSE](LICENSE).
