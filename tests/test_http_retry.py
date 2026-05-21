"""Tests for HTTP retry wrapper."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from europulse.ingestion.http import fetch_url, set_default_max_attempts


def test_set_default_max_attempts():
    """set_default_max_attempts should update the global default."""
    set_default_max_attempts(5)
    from europulse.ingestion.http import DEFAULT_MAX_ATTEMPTS
    assert DEFAULT_MAX_ATTEMPTS == 5
    set_default_max_attempts(3)  # reset


def test_fetch_url_success():
    """fetch_url should return the response on success."""

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "get", return_value=fake_resp):
        result = fetch_url("http://example.com")
    assert result is fake_resp
    fake_resp.raise_for_status.assert_called_once()


def test_fetch_url_retries_on_httpx_error():
    """fetch_url should retry on HTTPStatusError and eventually raise."""

    calls = []

    def fake_get(self, url, **kwargs):
        calls.append(url)
        raise httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

    with patch.object(httpx.Client, "get", fake_get):
        with pytest.raises(httpx.HTTPStatusError):
            fetch_url("http://example.com")

    assert len(calls) == 3  # default max_attempts
