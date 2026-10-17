# Kintsugi — Complete Project Workflow & System Guide

> **Project Name:** Kintsugi  
> **Tagline:** The manual-grounded AI repair assistant that refuses before it hallucinates.  
> **Event:** DEV × Hacktoberfest 2026 (Week 2 — Side Hustle Theme)  
> **Live Demo:** [https://kintsugi-hx3b.onrender.com/ui/index.html](https://kintsugi-hx3b.onrender.com/ui/index.html)  
> **Repository:** [https://github.com/Lakshay-Deol/kintsugi](https://github.com/Lakshay-Deol/kintsugi)

---

## 1. Executive Summary & Design Principle

In appliance repair, an inaccurate answer is substantially more dangerous than a refusal. A fabricated torque specification strips threading; a hallucinated electrical test creates a shock hazard; a made-up diagnostic code leads a repair technician to replace an expensive control board unnecessarily.

**Kintsugi** is built around one governing principle:  
> **Refusing queries deterministically before calling an LLM is a safety and cost-control feature.**

Kintsugi retrieves exclusively from the matched service manual for the appliance model entered by the technician. If the manual is absent, if search scores indicate low relevance, or if the procedure presents severe safety hazards (gas connections, sealed refrigerants, live mains electricity), Kintsugi **refuses deterministically with zero LLM API cost**. When evidence is found, claims are cross-checked against retrieved manual pages.

---

## 2. Complete End-to-End Workflow Diagram

```
[ Technician / Repair Café Volunteer ]
                  │
                  ▼
       1. Enter Model & Symptom
                  │
                  ▼
       2. Rate Limiting Check (Token Bucket: 5 req/min/IP)
          - Evaluates X-Forwarded-For header to support reverse proxy routing
                  │
                  ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 1: Deterministic Hazard Filter (§5.2)           │
  │  - Scans for Gas lines, R134a/Freon, 240V Mains       │
  └────────────────────────────────────────────────────────┘
         │                               │
    [Safe Query]                  [Hazard Detected]
         │                               │
         │                               ▼
         │                 REFUSAL: HAZARD_REFERRAL
         │                 (Immediate professional referral,
         │                  Zero DB / Zero LLM calls)
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  HYBRID RETRIEVAL & APP-SIDE FUSION                    │
  │  1. Vector Search ($vectorSearch on 'vector_index')   │
  │     - FastEmbed 384-dim ONNX embeddings (local CPU)   │
  │  2. BM25 Full-Text Search ($search on 'bm25_index')   │
  │  3. Reciprocal Rank Fusion (RRF, k=60) in application │
  │  * Offline Fallback: Local Cosine + In-Memory BM25    │
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 2: Deterministic Retrieval Gate (§5.1)          │
  │  - Model lookup: MODEL_NOT_FOUND if unknown           │
  │  - Thresholds: v_score >= 0.70 AND bm25 >= 5.0        │
  └────────────────────────────────────────────────────────┘
         │                               │
    [Evidence Found]              [Scores Below Threshold]
         │                               │
         │                               ▼
         │                 REFUSAL: LOW_RELEVANCE
         │                 (e.g., "baking bread in washer",
         │                  Zero LLM cost)
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  GROUNDED PROMPT ASSEMBLY & LLM SYNTHESIS              │
  │  - Prompt constrained to model's retrieved excerpts   │
  │  - Calls Google Gemma / Gemini API (or local Ollama)  │
  │  - Requests JSON: { answer, citations: [{page, ...}] }│
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 3: Programmatic Citation Verifier (§5.3)         │
  │  - Checks cited pages against retrieved passages set  │
  │  - Strips citations to ungrounded or absent pages     │
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  RESPONSE & TELEMETRY                                  │
  │  - Answer displayed with verified [Page X] badges     │
  │  - History retained only in browser localStorage      │
  │  - Optional technician outcome feedback: /fix-outcome  │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Flow Breakdown

### Phase 1: Request & Safety Interception
1. **User Input:** The technician enters a model identifier (e.g. `WFW5620HW0`) and a symptom or fault description.
2. **Reverse-Proxy Rate Limiting:** The server inspects the `X-Forwarded-For` header so that individual client IPs are distinguished behind Render's reverse proxy, enforcing 5 requests/minute per client IP.
3. **Hazard Gate (§5.2):** Before any database query or LLM invocation, the query is checked against regular expressions covering:
   - High-voltage mains tampering (tapping live wires, bypassing fuses)
   - Natural gas / propane repairs
   - Sealed-system refrigerants (R134a, R600a)
   - *Outcome:* Hazardous queries return an immediate `HAZARD_REFERRAL` with safety warnings and a recommendation to call a licensed specialist.

### Phase 2: Hybrid Retrieval & App-Side RRF Fusion
4. **Local ONNX Embedding:** The query string is encoded into a 384-dimensional dense vector using `BAAI/bge-small-en-v1.5` via the FastEmbed ONNX runtime locally in ~8 ms.
5. **Atlas Queries:**
   - **Vector Search:** Atlas `$vectorSearch` runs over the `vector_index`, pre-filtered by `brand` and `model`.
   - **Text Search:** Atlas `$search` executes a BM25 keyword query on `bm25_index`.
6. **App-Side Fusion:** In `src/kintsugi/retrieval/search.py`, rankings are combined via application-side Reciprocal Rank Fusion:
   `RRF Score = 1 / (60 + rank_vector) + 1 / (60 + rank_bm25)`
   The top 5 fused passages are selected.
7. **Offline Fallback:** If Atlas is unreachable, the system executes local in-memory cosine similarity and tokenized BM25 matching across `corpus/corpus_chunks.json`.

### Phase 3: Out-of-Domain Retrieval Gate (§5.1)
8. **Threshold Validation:**
   - If the model is not present in the manual corpus: returns `MODEL_NOT_FOUND`.
   - If both vector cosine score is below $0.70$ and BM25 score is below $5.0$: returns `LOW_RELEVANCE`.
   - *Result:* Unanswerable queries (e.g. asking how to bake sourdough bread in a washing machine) are refused before making any LLM call.

### Phase 4: Grounded LLM Generation
9. **Bounded Prompt:** Only the retrieved manual excerpts for that model are formatted into the prompt.
10. **Model Generation:** The LLM (Google Gemma / Gemini or local Ollama) is invoked with structured JSON output instructions.

### Phase 5: Programmatic Citation Verification (§5.3)
11. **Citation Check:** Because LLMs can occasionally cite non-existent pages even when instructed not to, `citation_check()` validates all cited page numbers against the set of retrieved pages. Any ungrounded page citation is programmatically stripped.
12. **Privacy Policy:** No customer symptom text or personal data is stored on our server. The raw prompt text is transmitted to the configured model provider (e.g., Google AI Studio) subject to their standard API terms of service. Queries are retained only in the user's browser `localStorage`.

---

## 4. Modes of Operation

| Feature / Behavior | Demo Mode (`DEMO_MODE=true`) | Full Mode (`DEMO_MODE=false`) |
| :--- | :--- | :--- |
| **Header Badge** | Amber badge: `⚡ Demo Mode` | Emerald badge: `✔ Production` |
| **Seeded Baseline** | Whirlpool `WFW5620HW0`, GE `GTW685BSLWS`, Bosch `WAT28400UC` (26 chunks total). | Same initial corpus; ingestion script available for adding more models. |
| **Telemetry Storage** | Stores repair outcomes in local file if Atlas permissions are read-only. | Stores outcomes directly into Atlas `kintsugi.fix_outcomes`. |
| **Rate Limiter** | Standard 5 req/min/IP with informative "demo busy" message on cap. | Enforces strict IP limits. |
| **Live App State** | **Currently active** on `https://kintsugi-hx3b.onrender.com`. | Toggleable via `DEMO_MODE=false` in Render dashboard. |

---

## 5. Sponsor Integrations

### 1. MongoDB Atlas
- **Storage & Search:** Hosts the `kintsugi` database with collections for manuals, chunks, and fix outcomes.
- **Atlas Vector Search:** `vector_index` indexes 384-dimensional FastEmbed embeddings with cosine metric and filter fields on `brand` and `model`.
- **Atlas Text Search:** `bm25_index` indexes text for exact error code and component lookups.
- **Telemetry:** Records voluntary technician feedback via `/fix-outcome` in `kintsugi.fix_outcomes`.

### 2. Google Gemma & Gemini
- **Model:** Primary inference runs via Google AI Studio (`gemini-3.1-flash-lite` / `gemma-3-27b-it`) using the `google-genai` SDK.
- **Model-Swap Capability:** Tested against local open-weights `gemma3:12b` via Ollama for offline workshop environments.

### 3. Render
- **Infrastructure:** Hosted as a Python web service defined in [`render.yaml`](file:///c:/Users/laksh/OneDrive/Desktop/ksp/mlh/kintsugi/render.yaml).
- **Configuration:** Uvicorn with `proxy_headers=True` and `forwarded_allow_ips="*"` for accurate per-IP rate limiting behind Render's edge proxy.
- **Monitoring:** `/health` endpoint checks database connectivity and reports demo mode status.


## 6. Evaluation & Latency Measurements

The evaluation suite (`eval/run_eval.py`) runs against a **30 hand-written test question dataset** (`eval/questions.json`) covering error codes, component testing, maintenance, hazardous tasks, and out-of-domain queries across the 3 baseline manuals.

| Metric | Measured Value | Scope & Details |
| :--- | :--- | :--- |
| **Refusal Accuracy** | **100.0%** (10 / 10) | Correctly refused unknown models (`MODEL_NOT_FOUND`), hazards (`HAZARD_REFERRAL`), and irrelevant queries (`LOW_RELEVANCE`) |
| **Citation Precision** | **100.0%** | All cited pages matched the retrieved ground-truth manual pages |
| **Hybrid RRF Hit@K** | **100.0%** (15 / 15) | Gold manual page appeared within top-5 retrieved passages for all 15 answerable questions |
| **Retrieval P50 Latency** | **58.5 ms** | **Retrieval only**: fastembed ONNX query embedding + local/hybrid search (does NOT include LLM generation) |
| **End-to-End P50 Latency (Hosted)** | **~845 ms** | Complete pipeline: Rate limit $\rightarrow$ Hazard gate $\rightarrow$ Hybrid search $\rightarrow$ Google Cloud LLM synthesis $\rightarrow$ Citation check |
| **End-to-End P50 Latency (Local Ollama)**| **~3,250 ms**| Complete pipeline with local `gemma3:12b` running on consumer CPU/GPU hardware |

*Note on corpus size:* This evaluation was conducted on a curated baseline corpus of 3 washer service manuals (26 chunks). The 100% scores represent a reproducible validation sanity check on this calibrated subset rather than a claim of general performance across all appliance categories.
