"""Tests for RSS feed date filtering."""

from datetime import datetime, timezone

from europulse.rag.news import fetch_feed


def test_fetch_feed_skips_old_articles(monkeypatch):
    """Articles older than `since` should be dropped."""

    def fake_fetch_url(url, **kwargs):
        class Resp:
            @property
            def text(self):
                return """<?xml version="1.0"?>
<rss><channel><item>
  <title>Old News</title>
  <link>http://old.com</link>
  <summary>Old</summary>
  <pubDate>Mon, 01 Jan 2020 00:00:00 GMT</pubDate>
</item><item>
  <title>Recent News</title>
  <link>http://recent.com</link>
  <summary>Recent</summary>
  <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
</item></channel></rss>"""

        return Resp()

    monkeypatch.setattr("europulse.rag.news.fetch_url", fake_fetch_url)

    since = datetime(2023, 6, 1, tzinfo=timezone.utc)
    articles = fetch_feed("Test", "http://fake", since=since)
    assert len(articles) == 1
    assert articles[0]["title"] == "Recent News"


def test_fetch_feed_allows_all_when_since_is_none(monkeypatch):
    """When `since` is None all articles should pass through."""

    def fake_fetch_url(url, **kwargs):
        class Resp:
            @property
            def text(self):
                return """<?xml version="1.0"?>
<rss><channel><item>
  <title>A</title>
  <link>http://a.com</link>
  <summary>A</summary>
  <pubDate>Mon, 01 Jan 2020 00:00:00 GMT</pubDate>
</item></channel></rss>"""

        return Resp()

    monkeypatch.setattr("europulse.rag.news.fetch_url", fake_fetch_url)

    articles = fetch_feed("Test", "http://fake", since=None)
    assert len(articles) == 1
