# Technical Decisions Log

Every technical choice, fallback, switch and verified limit is logged here with timestamp and source.

---

## Phase 0 — Setup

### 2026-10-17 | Gemma model ID
**Status:** NEEDS VERIFICATION (first task in Phase 0)
**Action:** Call Google AI Studio API, list available models, pick newest that fits free-tier limits.
**Reference:** https://ai.google.dev/gemini-api/docs/models
**To verify:** Is the model `gemma-3-27b-it` or `gemma-3-12b-it`? Does Gemma 4 exist on free tier?
**Log observed rate limits here:** req/min = UNVERIFIED, tokens/min = UNVERIFIED, req/day = UNVERIFIED

### 2026-10-17 | Database: MongoDB Atlas M0
**Chosen:** Atlas M0 (free)
**Reason:** Free tier, Vector Search supported, 512 MB storage, 3 search/vector indexes per project.
**Verified:** PENDING — create test cluster, test doc, test vector index.

### 2026-10-17 | Embeddings: Option A (fastembed bge-small-en-v1.5 ONNX)
**Status:** PENDING memory test
**Pass criterion:** Service stays well under 512 MB RAM on Render with margin for requests.
**If fails:** Switch to Option B (hosted embedding API, free tier). Log switch here with timestamp.

### 2026-10-17 | Atlas $rankFusion availability
**Status:** NEEDS VERIFICATION
**Default:** App-side RRF (k=60 from env). If $rankFusion available and confirmed on M0, evaluate switching.
**Decision:** Use app-side RRF by default (safer, version-independent).

### 2026-10-17 | Atlas index creation method
**Status:** NEEDS VERIFICATION
**Claim to verify:** "UI only" may be outdated. Check Atlas CLI / Admin API / driver support.
**Document exact index JSON:** see docs/atlas_indexes.md

### 2026-10-17 | Google AI Studio free-tier data terms
**Status:** NEEDS VERIFICATION
**Action:** Read current terms at https://ai.google.dev/gemini-api/terms
**Required for:** Privacy note in UI and README (§3 Phase 3).
**Log findings here.**

### 2026-10-17 | Reference repo credit
**Source:** raghuram-chittibomma/ai-repair-assistant (Apache-2.0)
**Used for:** Safety gate pattern, citation abstain pattern, chunk metadata structure, API schema pattern.
**What changed:** New DB (Atlas vs Postgres), new embeddings (fastembed vs sentence-transformers),
new LLM (Gemma/AI Studio vs OpenAI GPT), new deployment (Render vs LAN Docker),
new retrieval (Atlas Vector+Search vs pgvector+SQL), new eval set (30Q Kintsugi),
new UI with privacy note/demo-mode/fix-outcome form, new gate scripts.
**Full ledger:** docs/reuse_ledger.md

### 2026-10-17 | Hosting: Render free web service
**Specs:** 512 MB RAM, 0.1 CPU, spins down after 15 min idle, 30–60 s cold start, 750 instance-hours/month.
**Keep-alive:** UptimeRobot every 10 min on /health (configured in Phase 3).
**Fallback:** Render $7 Starter ONLY if OOM or unacceptable cold start. MUST ASK OWNER before switching.

### 2026-10-17 | LLM adapter design
**Decision:** OpenAI-compatible interface (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).
**Gemma system prompt note:** Gemma 3 handles system prompts poorly — fold instructions into user turn.
**JSON mode:** No reliable JSON mode — parse structured output defensively with retry cap of 1.

---

## Phase 1 — Data Layer
*(populate during Phase 1)*

---

## Phase 2 — Retrieval & Safety
*(populate during Phase 2)*

---

## Phase 3 — Product Surface
*(populate during Phase 3)*

---

## Phase 4 — Proof
*(populate during Phase 4)*

---

## Fallback Switches Log
*(append each switch here with ISO timestamp and reason)*

| Timestamp | Primary | Fallback | Reason |
|---|---|---|---|
| — | — | — | — |
