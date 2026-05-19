"""Tag articles with tickers based on config aliases."""

from __future__ import annotations

import re
from typing import Any

from europulse import config


def _compile_patterns() -> dict[str, re.Pattern]:
    """Build regex patterns for each ticker from aliases."""
    patterns: dict[str, re.Pattern] = {}
    for ticker, aliases in config.TICKER_ALIASES.items():
        # Sort by length descending so longer aliases match first
        sorted_aliases = sorted(aliases, key=len, reverse=True)
        escaped = [re.escape(a) for a in sorted_aliases]
        pattern = re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)
        patterns[ticker] = pattern
    return patterns


# Compile once at import time
_ALIAS_PATTERNS = _compile_patterns()


def tag_article(article: dict[str, Any]) -> list[str]:
    """Return a list of tickers mentioned in an article title or summary."""
    text = f"{article.get('title', '')} {article.get('summary', '')}"
    tickers = []
    for ticker, pattern in _ALIAS_PATTERNS.items():
        if pattern.search(text):
            tickers.append(ticker)
    return tickers


def tag_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add 'tickers' key to each article dict."""
    for art in articles:
        art["tickers"] = tag_article(art)
    return articles
