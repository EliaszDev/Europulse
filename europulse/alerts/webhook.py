"""Slack / Discord webhook alert dispatcher."""

from __future__ import annotations

from typing import Any

from europulse.ingestion.http import request


def send_slack(webhook_url: str, message: str, blocks: list[dict] | None = None) -> bool:
    """Post a plain-text or block-formatted message to a Slack incoming-webhook URL.

    Returns True on success, False otherwise.
    """
    payload: dict[str, Any] = {"text": message}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = request(
            webhook_url,
            method="POST",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def send_discord(webhook_url: str, message: str, embeds: list[dict] | None = None) -> bool:
    """Post a message to a Discord webhook URL.

    Returns True on success, False otherwise.
    """
    payload: dict[str, Any] = {"content": message}
    if embeds:
        payload["embeds"] = embeds

    try:
        resp = request(
            webhook_url,
            method="POST",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def alert_risk_spike(
    webhook_url: str,
    ticker: str,
    metric: str,
    value: float,
    threshold: float,
    platform: str = "slack",
) -> bool:
    """Send a templated risk-spike alert to Slack or Discord."""
    text = f"🚨 *Risk Alert* — {ticker}\n{metric} = {value:.2f} (threshold {threshold:.2f})"
    if platform.lower() == "slack":
        return send_slack(webhook_url, text)
    return send_discord(webhook_url, text)
