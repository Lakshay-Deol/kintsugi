# Reuse Ledger

This file tracks all reused code, ideas and patterns per the Kintsugi instructions (§1 Rule 1, §6 Phase 0).
Open-source reuse is allowed if changes are significant and credited.

| File / Idea | Source Repo | Source License | What Was Reused | What Changed |
|---|---|---|---|---|
| Safety gate pattern | raghuram-chittibomma/ai-repair-assistant | Apache-2.0 | allow/warn/escalate/block policy structure, output hazard check, ungrounded abstain | Adapted for Kintsugi retrieval gate (§5.1), hazard gate (§5.2), citation gate (§5.3); reason_code enum extended; MongoDB instead of Postgres |
| Citation abstain pattern | raghuram-chittibomma/ai-repair-assistant | Apache-2.0 | needs_grounding_citation logic, verbatim fallback on parse fail | Extended with page-in-retrieved-set check (§5.3); strip-or-flag per citation |
| Chunk metadata structure | raghuram-chittibomma/ai-repair-assistant | Apache-2.0 | {brand, model, manual_id, page, section, type} schema | Added vector cosine score and BM25 score fields; Atlas document format vs Postgres rows |
| API schema pattern | raghuram-chittibomma/ai-repair-assistant | Apache-2.0 | HealthResponse, request/response Pydantic structure | Rewrote for /answer endpoint with {status, answer, citations[], reason_code, warnings[]}; removed Postgres/pgvector deps |
| Hybrid retrieval concept | raghuram-chittibomma/ai-repair-assistant | Apache-2.0 | vector + BM25 fusion idea | Completely reimplemented: Atlas Vector Search + Atlas Search (BM25) + app-side RRF; new score thresholds; new filter logic |

## Notes
- None of the metrics, screenshots, eval numbers or quotes from the reference repo are used as Kintsugi evidence.
- All gate scripts, eval questions, and results are generated fresh from Kintsugi's own runs.
- The reference repo uses Postgres/pgvector/OpenAI/LAN Docker. Kintsugi uses Atlas/fastembed/Gemma/Render — a substantively different deployment.
