"""OpenRouter LLM wrapper with DuckDB prompt cache."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import duckdb
import httpx

_DEFAULT_MODEL = "openrouter/optimus-alpha"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_CACHE_DB = "prompt_cache.duckdb"


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _get_api_key() -> str | None:
    return os.getenv("OPENROUTER_API_KEY")


def _get_cache_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(_CACHE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_cache (
            prompt_hash TEXT PRIMARY KEY,
            prompt TEXT,
            response TEXT,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def query_llm(
    prompt: str,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    use_cache: bool = True,
) -> str:
    """Send a prompt to OpenRouter with optional DuckDB caching.

    Returns the raw text response.
    """
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment")

    prompt_hash = _hash_prompt(prompt)

    # Check cache
    if use_cache:
        conn = _get_cache_conn()
        try:
            row = conn.execute(
                "SELECT response FROM llm_cache WHERE prompt_hash = ?",
                (prompt_hash,),
            ).fetchone()
            if row:
                return row[0]
        finally:
            conn.close()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/EliaszDev/Europulse",
        "X-Title": "EuroPulse",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = httpx.post(
        _OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()

    # Extract response text
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"No choices in LLM response: {data}")
    text = choices[0].get("message", {}).get("content", "").strip()

    # Store in cache
    if use_cache:
        conn = _get_cache_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache (prompt_hash, prompt, response, model)
                VALUES (?, ?, ?, ?)
                """,
                (prompt_hash, prompt, text, model),
            )
        finally:
            conn.close()

    return text
