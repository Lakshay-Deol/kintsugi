"""§5.1 Retrieval gate + §5.3 Citation check.

§5.1 Refuse BEFORE any LLM call if:
  1. Model number not found in corpus
  2. No retrieved chunk belongs to the matched model
  3. best raw vector cosine < MIN_VECTOR_SCORE AND best BM25 < MIN_BM25_SCORE

DO NOT threshold on RRF scores — rank-based, not comparable across queries.
Thresholds from env vars, calibrated on dev split, reported on test split.

§5.3 After LLM call:
  - Every cited page must exist in the retrieved set for the matched model.
  - Strip or flag citations to pages not in retrieved set.
  - If no valid citation remains after 1 retry: show retrieved passages verbatim.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kintsugi.config import get_config

log = logging.getLogger(__name__)


class ReasonCode(str, Enum):
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    NO_MODEL_EVIDENCE = "NO_MODEL_EVIDENCE"
    LOW_RELEVANCE = "LOW_RELEVANCE"
    HAZARD_REFERRAL = "HAZARD_REFERRAL"
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"


@dataclass
class RefusalResult:
    should_refuse: bool
    reason_code: ReasonCode
    message: str
    matched_model: str = ""  # which variant matched (for logging)


@dataclass
class CitationCheckResult:
    valid_citations: list[dict[str, Any]]
    stripped_pages: list[int]
    fallback_to_verbatim: bool
    warning: str = ""


# ── §5.1 Retrieval gate ───────────────────────────────────────────────────────

def retrieval_gate(
    model: str,
    chunks: list[dict[str, Any]],
    best_vector_score: float,
    best_bm25_score: float,
    matched_manual: dict[str, Any] | None,
) -> RefusalResult:
    """
    Run §5.1 retrieval gate. Called BEFORE any LLM call.
    Must be called with results from hybrid_search + model_exists_in_corpus.
    """
    cfg = get_config()

    # Gate 1: model not found in corpus
    if matched_manual is None:
        return RefusalResult(
            should_refuse=True,
            reason_code=ReasonCode.MODEL_NOT_FOUND,
            message=(
                f"I don't have a manual for model '{model}' in my corpus. "
                "Please check the model number and try again, or check if your appliance "
                "is listed in the supported models."
            ),
        )

    matched_model_id = matched_manual.get("model", model)

    # Gate 2: no retrieved chunk belongs to the matched model
    model_chunks = [c for c in chunks if c.get("model", "").upper() == matched_model_id.upper()]
    if not model_chunks:
        return RefusalResult(
            should_refuse=True,
            reason_code=ReasonCode.NO_MODEL_EVIDENCE,
            message=(
                f"The manual for '{matched_model_id}' is in my corpus, but I couldn't find "
                "relevant passages for your question. Try rephrasing with more specific terms "
                "from the manual (e.g., component names, error codes)."
            ),
            matched_model=matched_model_id,
        )

    # Gate 3: both scores below thresholds
    below_vector = best_vector_score < cfg.min_vector_score
    below_bm25 = best_bm25_score < cfg.min_bm25_score
    if below_vector and below_bm25:
        log.info(
            "LOW_RELEVANCE: vector=%.3f (min=%.3f) bm25=%.2f (min=%.2f)",
            best_vector_score, cfg.min_vector_score, best_bm25_score, cfg.min_bm25_score,
        )
        return RefusalResult(
            should_refuse=True,
            reason_code=ReasonCode.LOW_RELEVANCE,
            message=(
                "My search didn't find passages in the manual that are relevant enough "
                "to answer your question confidently. "
                "This question may not be covered in the available documentation."
            ),
            matched_model=matched_model_id,
        )

    return RefusalResult(
        should_refuse=False,
        reason_code=ReasonCode.ANSWERED,
        message="",
        matched_model=matched_model_id,
    )


# ── §5.3 Citation check ───────────────────────────────────────────────────────

def citation_check(
    claimed_citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> CitationCheckResult:
    """
    §5.3: Every cited page must exist in the retrieved set for the matched model.
    Strip or flag citations to pages not in retrieved set.
    """
    retrieved_pages = {c.get("page") for c in retrieved_chunks if c.get("page")}

    valid = []
    stripped = []
    for cite in claimed_citations:
        page = cite.get("page")
        if page in retrieved_pages:
            valid.append(cite)
        else:
            log.warning("Citation to page %s not in retrieved set — stripped", page)
            stripped.append(page)

    fallback = len(valid) == 0

    warning = ""
    if stripped:
        warning = f"Note: {len(stripped)} citation(s) to pages not in retrieved set were removed."

    return CitationCheckResult(
        valid_citations=valid,
        stripped_pages=stripped,
        fallback_to_verbatim=fallback,
        warning=warning,
    )


def verbatim_fallback(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved passages verbatim when citation check fails completely."""
    parts = []
    for chunk in chunks:
        page = chunk.get("page", "?")
        text = chunk.get("text", "").strip()
        parts.append(f"[Page {page}]\n{text}")
    return "\n\n---\n\n".join(parts)
