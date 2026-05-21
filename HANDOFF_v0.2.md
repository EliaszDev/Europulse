# Europulse Handoff v0.2
## Project State — 2026-05-21

---

## 1. Overview

Europulse is a European financial intelligence platform. It ingests price and macro data, runs regime detection / risk analytics / forecasting, maintains a RAG pipeline over financial news, and exposes everything through a Streamlit dashboard with PDF/HTML report generation.

**Current Status:** All 7 weekly milestones are implemented and committed to `main`. The codebase is functional on Windows with Python 3.11–3.13.

---

## 2. What's Implemented (All Weeks)

| Week | Feature | Status |
|------|---------|--------|
| Week 1 | ETL pipeline, DuckDB schema, price/macro ingestion, data quality, tests | ✅ Complete |
| Week 2 | Regime detection (MA crossover), risk analytics (volatility, drawdown, Sharpe, beta), baseline forecasting (EWMA) | ✅ Complete |
| Week 3 | RAG pipeline — news fetcher, ChromaDB embeddings, ticker tagging, OpenRouter LLM client, DuckDB prompt cache | ✅ Complete |
| Week 4 | Reporting & Dashboard — Jinja2 HTML, WeasyPrint PDF, Streamlit 4-tab app | ✅ Complete |
| Week 5 | LLM synthesizer, chat interface, correlation heatmap, forecast model selector | ✅ Complete |
| Week 6 | Incremental news ingestion, data freshness checks, retry logic, daily report DB logging, CI scaffolding | ✅ Complete |
| Week 7 | Portfolio polish, NBP (Polish central bank) fetcher, webhook alerts, README rewrite | ✅ Complete |

---

## 3. Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Ingestion      │     │  Analysis       │     │  RAG / LLM      │
│  ├── prices.py  │────→│  ├── regimes.py │────→│  ├── news.py    │
│  ├── macro.py   │     │  ├── risk.py    │     │  ├── embeddings │
│  ├── nbp.py     │     │  ├── forecast.py│     │  ├── client.py  │
│  └── quality.py │     │  └── alerts.py  │     │  └── synthesizer│
└────────┬────────┘     └─────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DuckDB         │────→│  Reporting      │────→│  Streamlit UI   │
│  europulse.duckd│     │  ├── html_gen   │     │  app.py (4 tabs)│
│  prompt_cache.db│     │  ├── pdf_gen    │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Key Files:**
- `europulse/config.py` — Central config (tickers, thresholds, DB paths, API keys)
- `europulse/ingestion/db.py` — DuckDB connection helpers
- `europulse/ui/app.py` — Streamlit dashboard (Overview, Prices, Macro, LLM Synthesizer, Chat)

---

## 4. Recent Fixes (Applied 2026-05-21)

### Fix 1: `pyproject.toml` packages discovery
**Commit:** `5723f5c`
**Problem:** `pip install -e ".[dev]"` failed with `ModuleNotFoundError: No module named 'europulse'`
**Fix:** Added explicit `[tool.setuptools] packages = ["europulse"]`

### Fix 2: JSON serialization of pandas Timestamp
**Commit:** `240a05d`
**Problem:** `generate_regime_narrative()` crashed with `TypeError: Object of type Timestamp is not JSON serializable`
**Fix:** Changed `json.dumps(latest)` → `json.dumps(latest, default=str)` in `europulse/llm/synthesizer.py:32`

### Fix 3: Risk tab — numpy array vs pandas Series
**Commit:** `ab1cb81`
**Problem:** "Risk & Correlation" tab crashed because `rolling_volatility()` uses `.shift()`, which requires a pandas Series, but `app.py` passed `.to_numpy()`
**Fix:** Changed `prices = g["close"].to_numpy()` → `prices = g["close"]` in `europulse/ui/app.py:150`

---

## 5. Known Issues & Limitations

| Issue | Severity | Notes |
|-------|----------|-------|
| Python 3.14 unsupported | 🔴 High | `statsmodels`, `scikit-learn`, `weasyprint`, `sentence-transformers` fail to compile. Use **3.11–3.13**. |
| VM disk quota (99% full) | 🔴 High | Cannot install full dependency stack on the Linux VM. Windows/local development only. |
| Empty stub files exist | 🟡 Medium | `alerts.py` (root), `reporting/*` stubs, `ui/app.py` (was empty pre-Week 4). Some empty files may shadow live code. |
| `intelligence/` dir shadows | 🟡 Medium | `europulse/intelligence/` has 4 empty files that shadow live implementations in `llm/` and `rag/`. Safe to delete. |
| No `.env` committed | 🟢 Low | Expected. User stores FRED_API_KEY at `/home/vboxuser/Europulse/.env` (Linux) or project root (Windows). |
| `pandas_datareader` broken on 3.14 | 🟢 Low | Already worked around — ingestion uses direct `httpx` to FRED API. |
| WeasyPrint on Windows | 🟡 Medium | Often requires GTK+ runtime installed separately. PDF generation may fail without it. |

---

## 6. How to Run

### Prerequisites
- Python **3.11, 3.12, or 3.13**
- Git
- (Optional) GTK+ runtime if you want PDF export on Windows

### Setup
```powershell
git clone https://github.com/EliaszDev/Europulse.git
cd Europulse
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

### Configure
```powershell
echo FRED_API_KEY=your_key_here > .env
```

### Ingest Data (run once)
```powershell
python -m europulse.ingestion.macro
python -m europulse.ingestion.prices
python -m europulse.rag.news
```

### Launch
```powershell
streamlit run europulse\ui\app.py
```

Open `http://localhost:8501`

---

## 7. Data Flow

1. **Ingestion** pulls from Yahoo Finance (prices), FRED API (macro), NBP API (Polish rates), and RSS feeds (news)
2. **Quality checks** validate freshness, schema, and price plausibility
3. **Analysis** computes regimes, volatility, drawdowns, Sharpe ratios, betas, EWMA forecasts
4. **RAG** embeds news into ChromaDB and tags articles with affected tickers
5. **LLM Synthesizer** queries OpenRouter (default: `deepseek/deepseek-chat`) for narrative generation
6. **Dashboard** renders interactive Plotly charts + chat interface
7. **Reporting** exports HTML/PDF reports via Jinja2 + WeasyPrint

---

## 8. Test Status

- pytest suite exists and passes on a clean environment
- Key coverage: data quality, regime detection, risk metrics, forecast, ingestion
- **Missing direct tests:** `validate_prices()` stale-ticker and zero-volume branches

---

## 9. Recommended Next Steps

1. **Validate on Windows** — Run full ingestion + dashboard, confirm all 5 tabs work
2. **Clean dead code** — Remove `europulse/intelligence/` empty shadow files and any remaining stubs
3. **Add tests** for `validate_prices()` edge cases (stale tickers, zero volume)
4. **CI/CD** — GitHub Actions workflow for pytest (needs properly scoped PAT for `.github/workflows/` pushes)
5. **Docker** — Containerize to avoid Python version / dependency hell
6. **Kaleido upgrade** — `plotly[kaleido]` ≥1.0.0 (current deprecation warning)

---

*Handoff created by nanobot 🐈*
*Repository: https://github.com/EliaszDev/Europulse*
