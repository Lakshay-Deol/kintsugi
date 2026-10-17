"""Embedding via fastembed (Option A: ONNX bge-small-en-v1.5).

Never mixes embedding models: the same model is used for ingest and query.
If Option A fails the RAM test on Render, switch to Option B and re-embed everything.
See docs/decisions.md for the decision log.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from kintsugi.config import get_config

log = logging.getLogger(__name__)

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        cfg = get_config()
        log.info("Loading fastembed model: %s", cfg.embedding_model)
        _embedder = TextEmbedding(model_name=cfg.embedding_model)
        log.info("fastembed model loaded (dims=%d)", cfg.embedding_dims)
    return _embedder


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    embedder = get_embedder()
    return [v.tolist() for v in embedder.embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
