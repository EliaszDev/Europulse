"""Shared HTTP utilities with retry logic."""

from __future__ import annotations

import httpx
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

DEFAULT_MAX_ATTEMPTS = 3


def set_default_max_attempts(n: int) -> None:
    """Override the global default retry attempts for fetch_url."""
    global DEFAULT_MAX_ATTEMPTS
    DEFAULT_MAX_ATTEMPTS = n


def _is_retryable(exc: BaseException) -> bool:
    """Return True for transient network errors and specific HTTP status codes."""
    if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


def _fetch_once(url: str, **kwargs) -> httpx.Response:
    with httpx.Client() as client:
        response = client.get(url, **kwargs)
        response.raise_for_status()
        return response


def fetch_url(url: str, max_attempts: int | None = None, **kwargs) -> httpx.Response:
    """GET *url* with automatic retries on transient errors.

    Retries on connection errors, timeouts, and HTTP 429/5xx status codes.
    *max_attempts* overrides the module default when provided.
    """
    attempts = max_attempts if max_attempts is not None else DEFAULT_MAX_ATTEMPTS
    retryer = Retrying(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    for attempt in retryer:
        with attempt:
            return _fetch_once(url, **kwargs)
