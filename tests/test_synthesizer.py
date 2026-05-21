"""Tests for LLM synthesizer."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from europulse.llm.synthesizer import (
    chat_with_data,
    generate_regime_narrative,
    generate_risk_summary,
)


def test_generate_regime_narrative_empty():
    assert generate_regime_narrative(pd.DataFrame()) == "No regime data available."


def test_generate_regime_narrative_success():
    df = pd.DataFrame(
        {"composite_regime": ["growth"], "signals_json": ['{"inflation": "high"}']}
    )
    with patch("europulse.llm.synthesizer.query_llm", return_value="Bullish regime."):
        result = generate_regime_narrative(df)
    assert result == "Bullish regime."


def test_generate_risk_summary_empty():
    assert generate_risk_summary(pd.DataFrame()) == "No risk data available."


def test_generate_risk_summary_success():
    df = pd.DataFrame({"ticker": ["A"], "volatility": [0.2]})
    with patch("europulse.llm.synthesizer.query_llm", return_value="Low risk."):
        result = generate_risk_summary(df)
    assert result == "Low risk."


def test_chat_with_data_success():
    with patch(
        "europulse.llm.synthesizer.query_similar",
        return_value=[
            {
                "metadata": {"title": "News", "source": "Reuters"},
                "document": "Content",
            }
        ],
    ):
        with patch(
            "europulse.llm.synthesizer.query_llm", return_value="Answer"
        ):
            result = chat_with_data("What is the market?")
    assert result == "Answer"
