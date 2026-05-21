"""Tests for Slack / Discord webhook dispatcher."""

from unittest.mock import MagicMock, patch

import pytest

from europulse.alerts.webhook import (
    alert_risk_spike,
    send_discord,
    send_slack,
)


def test_send_slack_success():
    """send_slack should return True on 200."""

    fake_resp = MagicMock()
    fake_resp.status_code = 200

    with patch("europulse.alerts.webhook.request", return_value=fake_resp):
        ok = send_slack("https://hooks.slack.com/fake", "hello")
    assert ok is True


def test_send_slack_failure():
    """send_slack should return False on exception."""

    with patch("europulse.alerts.webhook.request", side_effect=Exception("timeout")):
        ok = send_slack("https://hooks.slack.com/fake", "hello")
    assert ok is False


def test_send_discord_success():
    """send_discord should return True on 204."""

    fake_resp = MagicMock()
    fake_resp.status_code = 204

    with patch("europulse.alerts.webhook.request", return_value=fake_resp):
        ok = send_discord("https://discord.com/api/webhooks/fake", "hello")
    assert ok is True


def test_send_discord_failure():
    """send_discord should return False on exception."""

    with patch("europulse.alerts.webhook.request", side_effect=Exception("timeout")):
        ok = send_discord("https://discord.com/api/webhooks/fake", "hello")
    assert ok is False


def test_alert_risk_spike_slack():
    """alert_risk_spike should dispatch to Slack when platform='slack'."""

    fake_resp = MagicMock()
    fake_resp.status_code = 200

    with patch("europulse.alerts.webhook.request", return_value=fake_resp):
        ok = alert_risk_spike(
            "https://hooks.slack.com/fake",
            ticker="SX5E",
            metric="RSI",
            value=75.0,
            threshold=70.0,
            platform="slack",
        )
    assert ok is True


def test_alert_risk_spike_discord():
    """alert_risk_spike should dispatch to Discord otherwise."""

    fake_resp = MagicMock()
    fake_resp.status_code = 204

    with patch("europulse.alerts.webhook.request", return_value=fake_resp):
        ok = alert_risk_spike(
            "https://discord.com/api/webhooks/fake",
            ticker="SX5E",
            metric="RSI",
            value=75.0,
            threshold=70.0,
            platform="discord",
        )
    assert ok is True
