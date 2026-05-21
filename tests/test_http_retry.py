"""Tests for HTTP retry wrapper."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from europulse.ingestion.http import (
    DEFAULT_MAX_ATTEMPTS,
    fetch_url,
    request,
    set_default_max_attempts,
)


def test_set_default_max_attempts():
    """set_default_max_attempts should update the global default."""
    original = DEFAULT_MAX_ATTEMPTS
    set_default_max_attempts(5)
    from europulse.ingestion.http import DEFAULT_MAX_ATTEMPTS as current

    assert current == 5
    set_default_max_attempts(original)


def test_fetch_url_success():
    """fetch_url should return the response on success."""

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "request", return_value=fake_resp):
        result = fetch_url("http://example.com")
    assert result is fake_resp
    fake_resp.raise_for_status.assert_called_once()


def test_request_post_success():
    """request with POST method should return the response."""

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "request", return_value=fake_resp):
        result = request("http://example.com", method="POST", json={"key": "value"})
    assert result is fake_resp


def test_fetch_url_retries_on_httpx_error():
    """fetch_url should retry on HTTPStatusError and eventually raise."""

    calls = []

    def fake_request(self, method, url, **kwargs):
        calls.append((method, url))
        raise httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        )

    with patch.object(httpx.Client, "request", fake_request):
        with pytest.raises(httpx.HTTPStatusError):
            fetch_url("http://example.com")

    assert len(calls) == 3  # default max_attempts
