"""Hybrid search: Atlas Vector Search + Atlas Search (BM25) fused with app-side RRF.

Design:
- Vector search with brand+model pre-filters.
- BM25 (Atlas Search) with brand+model filters.
- App-side RRF fusion (k from env). DO NOT threshold on RRF scores.
- Raw cosine and BM25 scores are preserved for the refusal gate (§5.1).
- $rankFusion is NOT used (app-side RRF is safer and version-independent).
- Seamless fallback to local corpus cache if Atlas is unreachable.
"""
from __future__ import annotations

import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from kintsugi.config import get_config
from kintsugi.db import get_collection, ping_atlas
from kintsugi.ingest.embedder import embed_query

log = logging.getLogger(__name__)

CORPUS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "corpus" / "corpus_chunks.json"


@lru_cache(maxsize=1)
def _load_local_corpus() -> list[dict[str, Any]]:
    if CORPUS_PATH.is_file():
        try:
            data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
            log.info("Loaded %d chunks from local corpus cache", len(data))
            return data
        except Exception as e:
            log.warning("Could not read local corpus cache: %s", e)
    return []


def _normalize_model(model: str) -> str:
    """Normalize model number: lowercase, collapse spaces/dashes."""
    return re.sub(r"[\s\-]+", "", model.strip().lower())


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def vector_search(
    query: str,
    brand: str,
    model: str,
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Atlas vector search with brand+model pre-filters. Falls back to local corpus if Atlas offline."""
    cfg = get_config()
    k = top_k or cfg.vector_top_k
    query_vec = embed_query(query)

    # 1. Try Atlas Vector Search if reachable
    if ping_atlas():
        try:
            col = get_collection(cfg.chunks_collection)
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": cfg.atlas_vector_index,
                        "path": "embedding",
                        "queryVector": query_vec,
                        "numCandidates": k * 10,
                        "limit": k,
                        "filter": {
                            "brand": {"$eq": brand},
                            "model": {"$eq": model},
                        },
                    }
                },
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "page": 1,
                        "section": 1,
                        "type": 1,
                        "brand": 1,
                        "model": 1,
                        "manual_id": 1,
                        "vector_score": {"$meta": "vectorSearchScore"},
                    }
                },
            ]
            hits = list(col.aggregate(pipeline))
            if hits:
                for h in hits:
                    if "vector_score" in h:
                        # Atlas cosine score is (1 + cos)/2; un-normalize to standard cosine
                        h["vector_score"] = float(h["vector_score"]) * 2.0 - 1.0
                return hits
        except Exception as exc:
            log.warning("Atlas vector search failed, using local fallback: %s", exc)

    # 2. Local fallback
    local_chunks = _load_local_corpus()
    norm_m = _normalize_model(model)
    norm_b = brand.strip().lower()

    scored = []
    for c in local_chunks:
        c_model = _normalize_model(c.get("model", ""))
        c_brand = c.get("brand", "").strip().lower()
        if norm_b in c_brand or c_brand in norm_b or not norm_b:
            if norm_m in c_model or c_model in norm_m:
                emb = c.get("embedding")
                if emb:
                    sim = _cosine_similarity(query_vec, emb)
                    item = {**c, "vector_score": round(sim, 4)}
                    scored.append(item)

    scored.sort(key=lambda x: x["vector_score"], reverse=True)
    return scored[:k]


def bm25_search(
    query: str,
    brand: str,
    model: str,
    *,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Atlas Search (BM25) with brand+model filters. Falls back to local token scoring if Atlas offline."""
    cfg = get_config()
    k = top_k or cfg.bm25_top_k

    if ping_atlas():
        try:
            col = get_collection(cfg.chunks_collection)
            pipeline = [
                {
                    "$search": {
                        "index": cfg.atlas_search_index,
                        "compound": {
                            "must": [{"text": {"query": query, "path": "text"}}],
                            "filter": [
                                {"text": {"query": brand, "path": "brand"}},
                                {"text": {"query": model, "path": "model"}},
                            ],
                        },
                    }
                },
                {"$limit": k},
                {
                    "$project": {
                        "_id": 1,
                        "text": 1,
                        "page": 1,
                        "section": 1,
                        "type": 1,
                        "brand": 1,
                        "model": 1,
                        "manual_id": 1,
                        "bm25_score": {"$meta": "searchScore"},
                    }
                },
            ]
            hits = list(col.aggregate(pipeline))
            if hits:
                return hits
        except Exception as exc:
            log.warning("Atlas BM25 search failed, using local fallback: %s", exc)

    # Local BM25-like token match fallback
    local_chunks = _load_local_corpus()
    norm_m = _normalize_model(model)
    norm_b = brand.strip().lower()
    # Exclude common corpus stopwords that have near-zero IDF in an appliance manual corpus
    DOMAIN_STOPWORDS = {"washer", "washers", "appliance", "appliances", "model", "unit", "with", "from", "that", "this", "have"}
    q_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2 and w.lower() not in DOMAIN_STOPWORDS]

    scored = []
    for c in local_chunks:
        c_model = _normalize_model(c.get("model", ""))
        c_brand = c.get("brand", "").strip().lower()
        if norm_b in c_brand or c_brand in norm_b or not norm_b:
            if norm_m in c_model or c_model in norm_m:
                text_lower = c.get("text", "").lower()
                # Calculate term coverage: fraction of distinct query terms present in chunk
                matched_tokens = [token for token in q_tokens if token in text_lower]
                coverage = len(matched_tokens) / len(q_tokens) if q_tokens else 0.0

                # Only score if there is meaningful query coverage (at least 35% of distinct terms)
                if coverage >= 0.35:
                    matches = sum(text_lower.count(token) * (4.0 if len(token) > 4 else 2.0) for token in matched_tokens)
                    score = min(25.0, round(matches * 2.5 * coverage, 2))
                    item = {**c, "bm25_score": score}
                    scored.append(item)

    scored.sort(key=lambda x: x.get("bm25_score", 0.0), reverse=True)
    return scored[:k]


def rrf_fuse(
    vector_hits: list[dict[str, Any]],
    bm25_hits: list[dict[str, Any]],
    *,
    k: int | None = None,
    final_top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    App-side Reciprocal Rank Fusion.
    DO NOT threshold on RRF scores - they are rank-based.
    Preserves raw vector_score and bm25_score for the refusal gate.
    """
    cfg = get_config()
    rrf_k = k or cfg.rrf_k
    final_k = final_top_k or cfg.final_top_k

    scores: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}

    for rank, hit in enumerate(vector_hits):
        doc_id = str(hit["_id"])
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        meta[doc_id] = {**hit}

    for rank, hit in enumerate(bm25_hits):
        doc_id = str(hit["_id"])
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
        if doc_id not in meta:
            meta[doc_id] = {**hit}
        else:
            meta[doc_id]["bm25_score"] = hit.get("bm25_score", 0.0)

    ranked = sorted(scores.keys(), key=lambda d: scores[d], reverse=True)
    results = []
    for doc_id in ranked[:final_k]:
        doc = meta[doc_id].copy()
        doc["rrf_score"] = scores[doc_id]
        results.append(doc)

    return results


def hybrid_search(
    query: str,
    brand: str,
    model: str,
) -> tuple[list[dict[str, Any]], float, float]:
    """
    Full hybrid search pipeline.
    Returns (ranked_chunks, best_vector_score, best_bm25_score).
    The raw scores are for the §5.1 refusal gate only.
    """
    vec_hits = vector_search(query, brand, model)
    bm25_hits = bm25_search(query, brand, model)

    best_vector = max((h.get("vector_score", 0.0) for h in vec_hits), default=0.0)
    best_bm25 = max((h.get("bm25_score", 0.0) for h in bm25_hits), default=0.0)

    fused = rrf_fuse(vec_hits, bm25_hits)
    return fused, best_vector, best_bm25


def model_exists_in_corpus(model: str) -> dict[str, Any] | None:
    """
    Check if the normalized model number matches any manual in the corpus.
    Supports suffix-variant matching. Returns the matched manual doc or None.
    """
    cfg = get_config()
    norm = _normalize_model(model)

    if ping_atlas():
        try:
            col = get_collection(cfg.manuals_collection)
            doc = col.find_one({"model": {"$regex": f"^{re.escape(model)}$", "$options": "i"}})
            if doc:
                return doc
            base = re.sub(r"[A-Z0-9]{1,3}$", "", model.upper())
            if base and base != model.upper():
                doc = col.find_one({"model": {"$regex": f"^{re.escape(base)}", "$options": "i"}})
                if doc:
                    return doc
        except Exception as e:
            log.warning("Atlas model lookup failed: %s", e)

    # Local fallback
    local_chunks = _load_local_corpus()
    for c in local_chunks:
        c_model = c.get("model", "")
        c_norm = _normalize_model(c_model)
        if norm == c_norm or norm in c_norm or c_norm in norm:
            return {
                "manual_id": c.get("manual_id"),
                "brand": c.get("brand"),
                "model": c_model,
            }

    # Suffix check
    base = re.sub(r"[A-Z0-9]{1,3}$", "", model.upper())
    if base and base != model.upper():
        base_norm = _normalize_model(base)
        for c in local_chunks:
            c_norm = _normalize_model(c.get("model", ""))
            if base_norm in c_norm:
                return {
                    "manual_id": c.get("manual_id"),
                    "brand": c.get("brand"),
                    "model": c.get("model"),
                }

    return None
