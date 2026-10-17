"""Temporal durable workflow implementation for Kintsugi repair diagnostic assistant.

Makes the diagnostic agent durable by wrapping the pipeline in a Temporal Workflow:
- Recovers from flaky LLM API calls with exponential backoff retries.
- Preserves checkpointed execution state across crashes and server restarts.
- Activities separate retrieval, LLM generation, and citation verification.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

log = logging.getLogger(__name__)


@dataclass
class DiagnosticInput:
    model_number: str
    symptom: str
    brand: str = ""


@dataclass
class DiagnosticOutput:
    status: str
    answer: str
    citations: list[dict[str, Any]]
    reason_code: str
    warnings: list[str]
    matched_model: str


# ---------------------------------------------------------------------------
# Temporal Activities
# ---------------------------------------------------------------------------

@activity.defn
async def check_hazard_activity(symptom: str) -> dict[str, Any]:
    """Execute deterministic hazard gate before expensive queries."""
    from kintsugi.safety.hazard import check_hazard
    hazard = check_hazard(symptom)
    return {
        "is_hazard": hazard.is_hazard,
        "warning_text": hazard.warning_text,
        "block_generation": hazard.block_generation,
    }


@activity.defn
async def hybrid_retrieval_activity(inp: DiagnosticInput) -> dict[str, Any]:
    """Retrieve grounded passages using MongoDB Atlas hybrid search or Tiger Data."""
    from kintsugi.retrieval.search import hybrid_search, model_exists_in_corpus
    from kintsugi.safety.gates import retrieval_gate

    model_match = model_exists_in_corpus(inp.model_number, inp.brand)
    chunks, best_v, best_b = hybrid_search(inp.symptom, inp.brand, inp.model_number)

    gate = retrieval_gate(inp.model_number, chunks, best_v, best_b, model_match)
    return {
        "should_refuse": gate.should_refuse,
        "reason_code": gate.reason_code.value,
        "message": gate.message,
        "matched_model": gate.matched_model,
        "chunks": chunks,
    }


@activity.defn
async def execute_llm_activity(args: dict[str, Any]) -> dict[str, Any]:
    """Execute LLM call with built-in activity retries for flaky model endpoints."""
    from kintsugi.llm.adapter import generate_answer
    from kintsugi.safety.prompts import build_answer_prompt

    symptom = args["symptom"]
    matched_model = args["matched_model"]
    chunks = args["chunks"]

    prompt = build_answer_prompt(symptom, matched_model, chunks)
    res = generate_answer(prompt, chunks)
    return {
        "answer": res.answer,
        "citations": [c.model_dump() for c in res.citations],
        "warnings": res.warnings,
    }


@activity.defn
async def verify_citations_activity(args: dict[str, Any]) -> dict[str, Any]:
    """Durable execution of post-LLM citation verifier."""
    from kintsugi.safety.gates import citation_check

    claimed = args["citations"]
    retrieved = args["chunks"]

    check_res = citation_check(claimed, retrieved)
    return {
        "valid_citations": check_res.valid_citations,
        "stripped_pages": check_res.stripped_pages,
        "warning": check_res.warning,
    }


# ---------------------------------------------------------------------------
# Temporal Workflow
# ---------------------------------------------------------------------------

@workflow.defn
class DiagnosticWorkflow:
    """Durable diagnostic workflow that orchestrates repair diagnosis with Temporal."""

    @workflow.run
    async def run(self, inp: DiagnosticInput) -> DiagnosticOutput:
        llm_retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3,
        )

        # 1. Deterministic Hazard Gate
        hazard = await workflow.execute_activity(
            check_hazard_activity,
            inp.symptom,
            start_to_close_timeout=timedelta(seconds=5),
        )

        if hazard["is_hazard"] and hazard["block_generation"]:
            refusal_text = (
                f"{hazard['warning_text']}\n\n"
                "This type of repair requires a licensed technician. "
                "I cannot provide step-by-step procedures for gas or refrigerant work."
            )
            return DiagnosticOutput(
                status="refused",
                answer=refusal_text,
                citations=[],
                reason_code="HAZARD_REFERRAL",
                warnings=[hazard["warning_text"]],
                matched_model="",
            )

        # 2. Hybrid Retrieval & Relevance Gate
        retrieval = await workflow.execute_activity(
            hybrid_retrieval_activity,
            inp,
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=llm_retry_policy,
        )

        if retrieval["should_refuse"]:
            return DiagnosticOutput(
                status="refused",
                answer=retrieval["message"],
                citations=[],
                reason_code=retrieval["reason_code"],
                warnings=[],
                matched_model=retrieval["matched_model"],
            )

        # 3. Durable LLM Synthesis (Retries automatically on 429/503/timeout)
        llm_res = await workflow.execute_activity(
            execute_llm_activity,
            {
                "symptom": inp.symptom,
                "matched_model": retrieval["matched_model"],
                "chunks": retrieval["chunks"],
            },
            start_to_close_timeout=timedelta(seconds=45),
            retry_policy=llm_retry_policy,
        )

        # 4. Programmatic Citation Verifier
        verified = await workflow.execute_activity(
            verify_citations_activity,
            {
                "citations": llm_res["citations"],
                "chunks": retrieval["chunks"],
            },
            start_to_close_timeout=timedelta(seconds=5),
        )

        warnings = list(llm_res.get("warnings", []))
        if verified.get("warning"):
            warnings.append(verified["warning"])

        return DiagnosticOutput(
            status="answered",
            answer=llm_res["answer"],
            citations=verified["valid_citations"],
            reason_code="ANSWERED",
            warnings=warnings,
            matched_model=retrieval["matched_model"],
        )
