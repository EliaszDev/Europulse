"""LLM synthesizer for narrative generation and chat."""

from __future__ import annotations

import json

import pandas as pd

from europulse.llm.client import query_llm
from europulse.rag.embeddings import query_similar


def generate_regime_narrative(regime_df: pd.DataFrame) -> str:
    """Generate an AI narrative interpreting the latest macro regime snapshot.

    Parameters
    ----------
    regime_df : pd.DataFrame
        Output of :func:`europulse.analysis.regimes.detect_regimes`.

    Returns
    -------
    str
        LLM-generated narrative or an error message.
    """
    if regime_df.empty:
        return "No regime data available."

    latest = regime_df.iloc[-1].to_dict()
    prompt = (
        "You are a senior European macro strategist. Interpret the following "
        f"regime snapshot for a professional investor: {json.dumps(latest)}"
    )
    try:
        return query_llm(prompt, max_tokens=512)
    except Exception as exc:  # pragma: no cover
        return f"AI narrative unavailable: {exc}"


def generate_risk_summary(risk_df: pd.DataFrame) -> str:
    """Generate an AI summary of portfolio risk metrics.

    Parameters
    ----------
    risk_df : pd.DataFrame
        DataFrame with columns such as ``ticker``, ``volatility``,
        ``max_drawdown``, ``sharpe``, ``beta``.

    Returns
    -------
    str
        LLM-generated summary or an error message.
    """
    if risk_df.empty:
        return "No risk data available."

    prompt = (
        "You are a portfolio risk manager. Summarize the following risk "
        f"metrics and highlight the biggest exposures: {risk_df.to_json(orient='records')}"
    )
    try:
        return query_llm(prompt, max_tokens=512)
    except Exception as exc:  # pragma: no cover
        return f"AI summary unavailable: {exc}"


def chat_with_data(query: str, top_k: int = 5) -> str:
    """Answer a user query using RAG over the news archive.

    Parameters
    ----------
    query : str
        User question.
    top_k : int, optional
        Number of similar articles to retrieve, by default 5.

    Returns
    -------
    str
        LLM-generated answer or an error message.
    """
    rag_results = query_similar(query, n_results=top_k)
    context_items = []
    for result in rag_results:
        meta = result.get("metadata", {})
        title = meta.get("title", "Untitled")
        source = meta.get("source", "Unknown")
        document = result.get("document", "")
        context_items.append(f"- {title} ({source}): {document[:300]}")

    context = "\n".join(context_items) or "No relevant articles found."

    prompt = (
        "You are a research assistant for European financial markets.\n\n"
        f"Context from news archive:\n{context}\n\n"
        f"User question: {query}\n"
        "Provide a concise, evidence-based answer."
    )
    try:
        return query_llm(prompt, max_tokens=1024)
    except Exception as exc:  # pragma: no cover
        return f"Chat error: {exc}"
