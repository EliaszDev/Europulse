"""ETL entrypoint — prices + macro + news + quality validation + freshness checks."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from europulse import config
from europulse.ingestion.db import create_schema, get_conn, upsert_macro, upsert_prices
from europulse.ingestion.macro import fetch_ecb, fetch_fred
from europulse.ingestion.prices import fetch_prices
from europulse.ingestion.quality import check_freshness, validate_prices
from europulse.rag.embeddings import add_articles
from europulse.rag.news import deduplicate, fetch_all_feeds
from europulse.rag.ticker_tagging import tag_articles


def _acquire_lock(lock_path: str = "data/.lock") -> bool:
    """Return True if lock acquired, False if already locked."""
    if os.path.exists(lock_path):
        return False
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    with open(lock_path, "w") as f:
        f.write("lock")
    return True


def _release_lock(lock_path: str = "data/.lock") -> None:
    if os.path.exists(lock_path):
        os.remove(lock_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="EuroPulse ETL")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Full 2-year historical refresh",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Fetch last 7 days of prices",
    )
    args = parser.parse_args()

    load_dotenv()

    if not _acquire_lock():
        print("Lock file exists — another instance is running.", file=sys.stderr)
        return 1

    try:
        conn = get_conn()
        create_schema(conn)

        period = "7d" if args.incremental else "2y" if args.backfill else "2y"

        # Prices
        print(f"Fetching prices (period={period})...")
        prices_df = fetch_prices(config.ALL_PRICE_TICKERS, period=period)
        if not prices_df.empty:
            upsert_prices(conn, prices_df)
            print(f"  -> {len(prices_df)} price rows inserted")
            quality = validate_prices(prices_df)
            if quality["stale_tickers"]:
                print(f"  -> Stale tickers: {quality['stale_tickers']}")
        else:
            print("  -> No price data returned")

        # Macro — FRED
        print("Fetching FRED macro data...")
        fred_df = fetch_fred(config.FRED_SERIES)
        if not fred_df.empty:
            upsert_macro(conn, fred_df)
            print(f"  -> {len(fred_df)} FRED rows inserted")
        else:
            print("  -> No FRED data returned")

        # Macro — ECB
        print("Fetching ECB macro data...")
        ecb_df = fetch_ecb(config.ECB_SERIES)
        if not ecb_df.empty:
            upsert_macro(conn, ecb_df)
            print(f"  -> {len(ecb_df)} ECB rows inserted")
        else:
            print("  -> No ECB data returned")

        # News (incremental only)
        if args.incremental:
            print("Fetching news (last 24h)...")
            since = datetime.now(timezone.utc) - timedelta(hours=24)
            articles = fetch_all_feeds(max_articles_per_feed=20, since=since)
            print(f"  -> {len(articles)} raw articles")
            articles = deduplicate(articles)
            articles = tag_articles(articles)
            inserted = add_articles(articles)
            print(f"  -> {inserted} new articles embedded")

        # Data freshness check
        print("Checking data freshness...")
        freshness = check_freshness(conn)
        for table, info in freshness.items():
            status = "OK" if info["ok"] else "STALE"
            print(f"  -> {table}: max_date={info['max_date']}, age_days={info['age_days']:.1f} [{status}]")

        conn.close()
        print("ETL complete.")
        return 0
    finally:
        _release_lock()


if __name__ == "__main__":
    sys.exit(main())
