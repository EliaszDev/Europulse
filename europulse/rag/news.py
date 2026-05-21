"""RSS article fetcher with deduplication and date parsing."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import feedparser
from trafilatura import extract

from europulse import config
from europulse.ingestion.http import fetch_url


def _hash(text: str) -> str:
    """Return a SHA-256 hex digest of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    """Try to extract a datetime from a feed entry."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except (ValueError, TypeError):
                continue
    # Fallback to string fields
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                return datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                try:
                    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S%z")
                except ValueError:
                    continue
    return None


def fetch_feed(
    name: str, url: str, max_articles: int = 20, since: datetime | None = None
) -> list[dict]:
    """Fetch and parse a single RSS feed.

    Returns a list of article dicts with keys:
        title, link, summary, published, source, content_hash
    """
    try:
        resp = fetch_url(url, timeout=15.0, follow_redirects=True)
        parsed = feedparser.parse(resp.text)
    except Exception as exc:
        print(f"  Warning: failed to fetch {name}: {exc}")
        return []

    articles = []
    for entry in parsed.entries[:max_articles]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        summary = entry.get("summary", "").strip()
        published = _parse_published(entry)

        if since is not None and published is not None:
            since_naive = since.replace(tzinfo=None)
            if published < since_naive:
                continue

        # Use title+summary for dedup hash; fetch full text if link present
        text_for_hash = f"{title} {summary}"
        content_hash = _hash(text_for_hash)

        articles.append(
            {
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "source": name,
                "content_hash": content_hash,
            }
        )

    return articles


def fetch_all_feeds(
    max_articles_per_feed: int = 20, since: datetime | None = None
) -> list[dict]:
    """Fetch all configured RSS feeds."""
    all_articles = []
    for name, url in config.RSS_FEEDS.items():
        articles = fetch_feed(name, url, max_articles=max_articles_per_feed, since=since)
        all_articles.extend(articles)
    return all_articles


def deduplicate(articles: list[dict]) -> list[dict]:
    """Remove articles with duplicate content_hash, keeping the first."""
    seen: set[str] = set()
    unique = []
    for art in articles:
        h = art["content_hash"]
        if h not in seen:
            seen.add(h)
            unique.append(art)
    return unique


def scrape_article(link: str, max_len: int = 4000) -> str | None:
    """Fetch and extract article text via trafilatura."""
    try:
        html = fetch_url(link, timeout=20.0, follow_redirects=True).text
        text = extract(html, include_comments=False, include_tables=False)
        if text:
            return text[:max_len]
        return None
    except Exception:
        return None
