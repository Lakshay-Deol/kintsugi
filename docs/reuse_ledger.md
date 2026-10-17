# Component & Architecture Ledger

This file tracks the architectural components and open-source building blocks utilized by Kintsugi.

| Component / Module | Implementation | License | Function & Purpose |
|---|---|---|---|
| Deterministic Safety Gates | `src/kintsugi/safety/` | Apache-2.0 | Hazard referral policy (§5.2), retrieval relevance validation (§5.1), and programmatic citation verification (§5.3). |
| Hybrid Retrieval Engine | `src/kintsugi/retrieval/` | Apache-2.0 | MongoDB Atlas Vector Search + BM25 text search fused via application-side Reciprocal Rank Fusion (RRF $k=60$). |
| FastEmbed ONNX Embedder | `src/kintsugi/ingest/` | Apache-2.0 | Local CPU vectorization using `BAAI/bge-small-en-v1.5` generating 384-dimensional dense vectors at $0 API cost. |
| Diagnostic Web API | `src/kintsugi/api/` | Apache-2.0 | Asynchronous FastAPI service with reverse-proxy aware rate limiting and client-side history storage. |
| Temporal Durable Workflow | `src/kintsugi/workflows/` | Apache-2.0 | Durable workflow orchestration providing automated retries and resilience against flaky external LLM calls. |
| Tiger Data pgvector Connector | `src/kintsugi/tiger_data.py` | Apache-2.0 | PostgreSQL hybrid search schema and Model Context Protocol (MCP) tool integration. |
