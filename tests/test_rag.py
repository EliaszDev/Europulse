"""Tests for the RAG pipeline."""

from europulse.rag.news import deduplicate, fetch_feed, _hash
from europulse.rag.ticker_tagging import tag_article


def test_hash_deterministic():
    h1 = _hash("hello world")
    h2 = _hash("hello world")
    assert h1 == h2
    assert len(h1) == 64


def test_deduplicate():
    articles = [
        {"title": "A", "link": "http://a.com", "content_hash": "abc123"},
        {"title": "B", "link": "http://b.com", "content_hash": "abc123"},
        {"title": "C", "link": "http://c.com", "content_hash": "def456"},
    ]
    result = deduplicate(articles)
    assert len(result) == 2
    assert result[0]["title"] == "A"
    assert result[1]["title"] == "C"


def test_tag_article_orlen():
    art = {
        "title": "PKN Orlen reports strong Q3 earnings",
        "summary": "The Polish oil giant saw revenue growth.",
    }
    tickers = tag_article(art)
    assert "PKN.WA" in tickers


def test_tag_article_allegro():
    art = {
        "title": "Allegro expands into new markets",
        "summary": "The e-commerce platform plans European growth.",
    }
    tickers = tag_article(art)
    assert "ALE.WA" in tickers


def test_tag_article_no_match():
    art = {
        "title": "Weather forecast for Warsaw",
        "summary": "Sunny skies expected this weekend.",
    }
    tickers = tag_article(art)
    assert tickers == []
