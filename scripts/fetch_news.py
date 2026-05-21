"""News ingestion pipeline: fetch RSS, deduplicate, tag tickers, embed to ChromaDB."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from europulse.ingestion.db import create_schema, get_conn
from europulse.rag.embeddings import add_articles
from europulse.rag.news import deduplicate, fetch_all_feeds, scrape_article
from europulse.rag.ticker_tagging import tag_articles


def main() -> int:
    parser = argparse.ArgumentParser(description="EuroPulse news pipeline")
    parser.add_argument(
        "--max-per-feed",
        type=int,
        default=20,
        help="Max articles per RSS feed",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Fetch full article text via trafilatura",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO datetime (e.g. 2024-01-01) — only fetch articles published since this date",
    )
    args = parser.parse_args()

    since = None
    if args.since:
        since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)

    # Ensure schema exists (for llm_cache if needed later)
    conn = get_conn()
    create_schema(conn)
    conn.close()

    print("Fetching RSS feeds...")
    articles = fetch_all_feeds(max_articles_per_feed=args.max_per_feed, since=since)
    print(f"  -> {len(articles)} raw articles")

    articles = deduplicate(articles)
    print(f"  -> {len(articles)} after dedup")

    articles = tag_articles(articles)
    tagged = sum(1 for a in articles if a["tickers"])
    print(f"  -> {tagged} articles tagged with tickers")

    if args.scrape:
        print("Scraping full text...")
        for art in articles:
            if art.get("link"):
                text = scrape_article(art["link"])
                if text:
                    art["summary"] = text

    print("Embedding to ChromaDB...")
    inserted = add_articles(articles)
    print(f"  -> {inserted} new articles embedded")

    print("News pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
