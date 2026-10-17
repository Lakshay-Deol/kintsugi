from __future__ import annotations

from pathlib import Path
"""Kintsugi FastAPI application.

Endpoints:
  GET  /health      — Atlas ping, version, demo_mode flag
  POST /answer      — Main Q&A: retrieval gate -> hazard gate -> LLM -> citation check
  POST /fix-outcome — Store fix-outcome record (§2 schema only)
  GET  /            — Redirect to UI
"""

import datetime
import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from kintsugi import __version__
from kintsugi.api.rate_limit import check_rate_limit
from kintsugi.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    AnswerStatus,
    CitationOut,
    FixOutcomeRequest,
    FixOutcomeResponse,
    HealthResponse,
    ReasonCode,
)
from kintsugi.config import get_config
from kintsugi.db import get_collection, ping_atlas
from kintsugi.llm.adapter import LLMError, LLMRateLimitError, LLMTimeoutError, complete_json
from kintsugi.retrieval.search import hybrid_search, model_exists_in_corpus
from kintsugi.safety.gates import (
    ReasonCode as GateReasonCode,
    citation_check,
    retrieval_gate,
    verbatim_fallback,
)
from kintsugi.safety.hazard import check_hazard
from kintsugi.safety.prompts import build_answer_prompt

log = logging.getLogger(__name__)

# Valid enums for fix-outcome (§2 schema)
_VALID_SYMPTOM_CATS = {"electrical", "mechanical", "software", "other"}
_VALID_OUTCOMES = {"fixed", "partially", "not_fixed", "unsafe_referred"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_config()
    log.info("Kintsugi v%s starting (env=%s demo_mode=%s)", __version__, cfg.app_env, cfg.demo_mode)
    if not cfg.skip_embedder_warmup:
        try:
            from kintsugi.ingest.embedder import embed_query
            embed_query("warmup")
            log.info("Embedder warmed up")
        except Exception as exc:
            log.warning("Embedder warmup failed: %s", exc)
    yield
    log.info("Kintsugi shutting down")


def create_app() -> FastAPI:
    cfg = get_config()
    app = FastAPI(
        title="Kintsugi Repair Assistant",
        description="Manual-grounded repair assistant. Powered by Gemma + MongoDB Atlas.",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if not cfg.is_production else None,
        redoc_url=None,
    )

    # Serve static UI files
    import pathlib
    ui_dir = pathlib.Path(__file__).parent / "static"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse("/ui/index.html")

    @app.get("/health", response_model=HealthResponse)
    async def health():
        atlas_ok = ping_atlas()
        return HealthResponse(
            status="ok" if atlas_ok else "degraded",
            atlas_ok=atlas_ok,
            version=__version__,
            demo_mode=cfg.demo_mode,
            llm_model=cfg.llm_model,
            embedding_model=cfg.embedding_model,
        )

    @app.post("/answer", response_model=AnswerResponse)
    async def answer(req: AnswerRequest, request: Request):
        client_ip = request.client.host if request.client else "unknown"

        # Rate limiting
        allowed, rate_msg = check_rate_limit(client_ip)
        if not allowed:
            raise HTTPException(status_code=429, detail=rate_msg)

        model_number = req.model_number.strip()
        symptom = req.symptom.strip()
        brand = req.brand.strip() if req.brand else ""

        warnings: list[str] = []

        # §5.2 Hazard gate (BEFORE any retrieval or LLM call)
        hazard = check_hazard(symptom)
        if hazard.is_hazard:
            warnings.append(hazard.warning_text)
            if hazard.block_generation:
                # Gas/refrigerant: return hazard warning + referral, no LLM
                return AnswerResponse(
                    status=AnswerStatus.refused,
                    answer=(
                        hazard.warning_text + "\n\nThis type of repair requires a licensed technician. "
                        "I cannot provide step-by-step procedures for gas or refrigerant work."
                    ),
                    citations=[],
                    reason_code=ReasonCode.HAZARD_REFERRAL,
                    warnings=warnings,
                    demo_mode=cfg.demo_mode,
                )

        # §5.1 Retrieval gate — model lookup
        matched_manual = model_exists_in_corpus(model_number)

        # Hybrid search
        if brand and matched_manual:
            search_brand = brand
        elif matched_manual:
            search_brand = matched_manual.get("brand", "")
        else:
            search_brand = brand

        chunks, best_vector, best_bm25 = hybrid_search(symptom, search_brand, model_number)

        # §5.1 Refusal gate
        gate_result = retrieval_gate(
            model_number, chunks, best_vector, best_bm25, matched_manual
        )

        if gate_result.should_refuse:
            # Map internal reason code to schema enum
            reason_map = {
                GateReasonCode.MODEL_NOT_FOUND: ReasonCode.MODEL_NOT_FOUND,
                GateReasonCode.NO_MODEL_EVIDENCE: ReasonCode.NO_MODEL_EVIDENCE,
                GateReasonCode.LOW_RELEVANCE: ReasonCode.LOW_RELEVANCE,
            }
            return AnswerResponse(
                status=AnswerStatus.refused,
                answer=gate_result.message,
                citations=[],
                reason_code=reason_map.get(gate_result.reason_code, ReasonCode.NO_MODEL_EVIDENCE),
                warnings=warnings,
                matched_model=gate_result.matched_model,
                demo_mode=cfg.demo_mode,
            )

        # LLM call
        prompt = build_answer_prompt(symptom, gate_result.matched_model, chunks)
        try:
            parsed = complete_json(prompt)
        except LLMTimeoutError:
            parsed = None
            warnings.append("LLM timed out — showing retrieved passages verbatim.")
        except LLMRateLimitError:
            raise HTTPException(
                status_code=503,
                detail="The demo is busy (Gemma rate limit). Please try again in a minute.",
            )
        except LLMError as exc:
            log.error("LLM error: %s", exc)
            parsed = None
            warnings.append("LLM error — showing retrieved passages verbatim.")

        # §5.3 Citation check
        if parsed and isinstance(parsed, dict):
            raw_citations = parsed.get("citations", [])
            llm_answer = parsed.get("answer", "").strip()
            cite_result = citation_check(raw_citations, chunks)

            if cite_result.warning:
                warnings.append(cite_result.warning)

            if cite_result.fallback_to_verbatim:
                # No valid citations remain — verbatim fallback
                warnings.append("No verifiable citations found — showing manual passages verbatim.")
                final_answer = verbatim_fallback(chunks)
                final_citations = []
            else:
                final_answer = llm_answer
                final_citations = [
                    CitationOut(
                        claim=c.get("claim", ""),
                        page=c.get("page", 0),
                        excerpt=c.get("excerpt", ""),
                    )
                    for c in cite_result.valid_citations
                ]
        else:
            # Parse failed — verbatim fallback
            warnings.append("Could not parse structured answer — showing manual passages verbatim.")
            final_answer = verbatim_fallback(chunks)
            final_citations = []

        # Prepend hazard warning if present
        if hazard.is_hazard and hazard.warning_text:
            final_answer = hazard.warning_text + "\n\n---\n\n" + final_answer

        return AnswerResponse(
            status=AnswerStatus.answered,
            answer=final_answer,
            citations=final_citations,
            reason_code=ReasonCode.ANSWERED,
            warnings=warnings,
            matched_model=gate_result.matched_model,
            demo_mode=cfg.demo_mode,
        )

    @app.post("/fix-outcome", response_model=FixOutcomeResponse)
    async def fix_outcome(req: FixOutcomeRequest):
        """Store fix-outcome record. §2 schema only — no user text, no PII."""
        if req.symptom_category not in _VALID_SYMPTOM_CATS:
            raise HTTPException(400, f"Invalid symptom_category. Must be one of: {_VALID_SYMPTOM_CATS}")
        if req.outcome not in _VALID_OUTCOMES:
            raise HTTPException(400, f"Invalid outcome. Must be one of: {_VALID_OUTCOMES}")

        record = {
            "_id": str(uuid.uuid4()),
            "model": req.model,
            "symptom_category": req.symptom_category,
            "outcome": req.outcome,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        try:
            if ping_atlas():
                col = get_collection(get_config().fix_outcomes_collection)
                col.insert_one(record)
                return FixOutcomeResponse(recorded=True, id=record["_id"])
        except Exception as exc:
            log.warning("Atlas fix-outcome insert failed, using local fallback: %s", exc)

        # Local fallback store
        try:
            fallback_path = Path(__file__).resolve().parent.parent.parent.parent / "corpus" / "local_fix_outcomes.json"
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            existing = []
            if fallback_path.is_file():
                try:
                    existing = json.loads(fallback_path.read_text(encoding="utf-8"))
                except Exception:
                    existing = []
            existing.append(record)
            fallback_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            log.info("Recorded fix-outcome to local store (id=%s)", record["_id"])
            return FixOutcomeResponse(recorded=True, id=record["_id"])
        except Exception as exc:
            log.error("Local fallback fix-outcome failed: %s", exc)
            return FixOutcomeResponse(recorded=True, id=record["_id"])

    return app


app = create_app()
