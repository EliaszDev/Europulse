# EuroPulse

**European financial intelligence, automated daily.**

EuroPulse monitors EU macro regimes, Polish and Eurozone equity risk, and financial news — then synthesises it into plain-language narratives, alerts, and downloadable reports using an AI research assistant you can ask questions directly.

[![Live Demo](https://img.shields.io/badge/Live_Demo-Open_App-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://YOUR_APP.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)

---

## What it does

**Regime monitoring** — Tracks ECB policy stance, Euro area inflation, and yield curve shape. Classifies the current macro environment daily and flags when it shifts.

**Risk reporting** — Computes volatility, drawdown, Sharpe ratio, and correlation across GPW and Eurozone equities. Highlights the top risks in a one-page summary.

**News intelligence** — Pulls financial news from Reuters and the FT, links articles to relevant tickers, and surfaces them in the AI chat as cited sources.

**Automated reports** — Generates a dated HTML report every weekday morning with the latest regime assessment, risk table, and active alerts. No manual work required.

**AI research assistant** — Ask questions like *"Why is EURPLN rising?"* or *"What's the current risk outlook for PKN.WA?"* and get answers grounded in today's data with source citations.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                               │
│   yfinance (OHLCV)   │   FRED / ECB SDW (macro)   │   RSS (news)   │
└──────────┬───────────────────────┬─────────────────────┬────────────┘
           │                       │                     │
           ▼                       ▼                     ▼
┌──────────────────┐   ┌───────────────────┐   ┌─────────────────────┐
│ ingestion layer  │   │    macro.py        │   │      news.py        │
│ prices.py        │   │    (FRED+ECB)      │   │  (RSS+trafilatura)  │
│ quality.py       │   └─────────┬─────────┘   └──────────┬──────────┘
└────────┬─────────┘             │                         │
         │                       │                         ▼
         └───────────┬───────────┘             ┌─────────────────────┐
                     ▼                         │       rag.py        │
        ┌────────────────────────┐             │      ChromaDB       │
        │         DuckDB         │             │    MiniLM-L6-v2     │
        │ prices│macro│alerts│cache            └──────────┬──────────┘
        └────────────┬───────────┘                        │
                     └─────────────────┬──────────────────┘
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                      ANALYSIS LAYER                      │
        │  regimes.py (EU macro regime) │ risk.py (UCITS metrics)  │
        │  forecast.py (baseline models)│ alerts.py (thresholds)   │
        └──────────────────────────────┬───────────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                    INTELLIGENCE LAYER                    │
        │   llm_client.py  (OpenRouter + DuckDB cache + fallback)  │
        │   synthesizer.py (narrative / risk / chat / alerts)      │
        └───────────────────┬──────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
┌─────────────────────────┐   ┌───────────────────────────┐
│       Streamlit UI      │   │     HTML / PDF report     │
│   4-tab dashboard       │   │   Jinja2 + weasyprint     │
│   RAG chat              │   │   GitHub Actions          │
└─────────────────────────┘   └───────────────────────────┘
```

---

## Getting started

You need Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and a free [OpenRouter](https://openrouter.ai) API key.

```bash
git clone https://github.com/YOUR_USERNAME/europulse
cd europulse
uv sync
cp .env.example .env   # paste your OPENROUTER_API_KEY
uv run python scripts/ingest_all.py --backfill
uv run streamlit run europulse/ui/app.py
```

Then open `http://localhost:8501`.

For daily updates, run:

```bash
uv run python scripts/ingest_all.py --incremental
uv run python scripts/generate_report.py
```

Or let GitHub Actions do it automatically every weekday morning.

---

## Built with

Python · DuckDB · ChromaDB · sentence-transformers · OpenRouter · Streamlit · Plotly · GitHub Actions

All data sources are free. No GPU required. Monthly cost: **$0**.

---

## Roadmap

- Sentiment scoring on news articles (FinBERT)
- Polish National Bank (NBP) official exchange rate feed
- Luxembourg Stock Exchange (LuxSE) tickers
- Slack / Discord alert webhooks

---

## License

MIT — see [LICENSE](LICENSE).
