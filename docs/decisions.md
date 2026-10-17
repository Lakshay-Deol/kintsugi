# Architectural Decisions Log

This document records the architectural and engineering decisions made during the development of Kintsugi.

---

## 1. Safety Architecture: Refusal Before Generation
- **Decision:** Evaluate deterministic hazard checks (§5.2) and relevance thresholds (§5.1) *before* making any LLM call.
- **Rationale:** An inaccurate electrical or gas repair instruction can cause severe physical harm or damage. Refusing ungrounded questions deterministically saves API costs and eliminates speculative answers.

## 2. Multi-Provider Hybrid Retrieval
- **Decision:** Combine MongoDB Atlas Vector Search (`vector_index`) and full-text BM25 search (`bm25_index`) with application-side Reciprocal Rank Fusion (RRF $k=60$).
- **Rationale:** Error codes (like `F5E2`) require exact keyword matching, while symptom descriptions require semantic vector matching. RRF effectively combines both ranking lists.
- **Resilience:** If cloud connectivity drops, the system falls back to local in-memory cosine similarity and tokenized BM25 matching without service disruption.

## 3. Programmatic Citation Stripping
- **Decision:** Automatically verify all cited page numbers against the set of retrieved passages (§5.3).
- **Rationale:** LLMs can occasionally cite non-existent pages even when instructed otherwise. The citation verifier strips ungrounded page numbers programmatically.

## 4. Privacy-First Local Storage
- **Decision:** Retain technician lookup history strictly in browser `localStorage`.
- **Rationale:** Prevents storing customer diagnostic text on our servers. The only server-side telemetry is voluntary, anonymous fix-outcome category records.

## 5. Reverse-Proxy Rate Limiting
- **Decision:** Parse the `X-Forwarded-For` header in FastAPI and configure Uvicorn with `proxy_headers=True`.
- **Rationale:** Distinguishes individual client IPs behind Render's edge proxy, preventing evaluator IP collisions.
