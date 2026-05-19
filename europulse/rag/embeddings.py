"""ChromaDB vector store with sentence-transformers embeddings."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from europulse import config

_DEFAULT_MODEL = "all-MiniLM-L6-v2"


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model."""
    return SentenceTransformer(_DEFAULT_MODEL)


def _get_chroma() -> chromadb.Client:
    """Return a ChromaDB persistent client."""
    os.makedirs(config.CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=config.CHROMA_PATH)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Encode a list of texts into dense vectors."""
    model = _get_model()
    return model.encode(texts, show_progress_bar=False).tolist()


def _doc_id(title: str, link: str) -> str:
    """Generate a deterministic document ID."""
    return hashlib.sha256(f"{title}:{link}".encode()).hexdigest()[:16]


def add_articles(articles: list[dict[str, Any]]) -> int:
    """Embed and store articles in ChromaDB.

    Returns the number of articles inserted.
    """
    if not articles:
        return 0

    client = _get_chroma()
    collection = client.get_or_create_collection("news")

    texts = []
    ids = []
    metadatas = []

    for art in articles:
        text = f"{art.get('title', '')}\n{art.get('summary', '')}"
        doc_id = _doc_id(art.get("title", ""), art.get("link", ""))
        meta = {
            "title": art.get("title", ""),
            "link": art.get("link", ""),
            "source": art.get("source", ""),
            "content_hash": art.get("content_hash", ""),
        }
        # Skip if already exists
        try:
            collection.get(ids=[doc_id])
            continue
        except Exception:
            pass

        texts.append(text)
        ids.append(doc_id)
        metadatas.append(meta)

    if not texts:
        return 0

    embeddings = embed_texts(texts)
    collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts)
    return len(texts)


def query_similar(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Return the top-N most similar articles to a query text."""
    client = _get_chroma()
    collection = client.get_or_create_collection("news")

    embedding = embed_texts([query])
    results = collection.query(
        query_embeddings=embedding,
        n_results=n_results,
    )

    out = []
    for i in range(len(results["ids"][0])):
        out.append(
            {
                "id": results["ids"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
                "metadata": results["metadatas"][0][i],
                "document": results["documents"][0][i],
            }
        )
    return out
