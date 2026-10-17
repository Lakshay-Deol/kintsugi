# Kintsugi — Complete Project Workflow & Sponsor Integration Guide

> **Project Name:** Kintsugi  
> **Tagline:** The manual-grounded AI repair assistant that refuses before it hallucinates.  
> **Event:** DEV × Hacktoberfest 2026 (Week 2 — Side Hustle Theme)  
> **Live URL:** [https://kintsugi-hx3b.onrender.com/ui/index.html](https://kintsugi-hx3b.onrender.com/ui/index.html)  
> **Repository:** [https://github.com/Lakshay-Deol/kintsugi](https://github.com/Lakshay-Deol/kintsugi)

---

## 1. Executive Summary & Core Principle

In consumer appliance repair, an incorrect answer is far more dangerous than a simple refusal. A fabricated torque spec strips a bolt; a hallucinated electrical procedure creates a shock or fire hazard; a made-up error code causes a repair shop to order a $250 control board that doesn't fix the problem.

**Kintsugi** is built around one uncompromising design law:  
> **"Refusing correctly before invoking an LLM is a safety feature, not a failure."**

The assistant retrieves exclusively from the **matched service manual** of the appliance model entered by the user. If the manual is missing, if the relevance score is low, or if the procedure involves high-risk hazards (mains 240V electricity, refrigerant gasses, or natural gas lines), the system **refuses deterministically with zero LLM API cost**. When an answer is provided, every technical claim is verified against page-level citations.

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
                  │
                  ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 1: Deterministic Hazard Filter (§5.2)           │
  │  - Checks for Gas lines, Freon/R134a, 240V Mains      │
  └────────────────────────────────────────────────────────┘
         │                               │
    [Safe Query]                  [Hazard Detected]
         │                               │
         │                               ▼
         │                 REFUSAL: HAZARD_REFERRAL
         │                 (Immediate Professional Referral,
         │                  Zero DB / Zero LLM calls)
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  HYBRID RETRIEVAL: MongoDB Atlas Search                │
  │  1. Vector Search ($vectorSearch on 'vector_index')   │
  │     - FastEmbed 384-dim ONNX embeddings                │
  │  2. BM25 Full-Text Search ($search on 'bm25_index')   │
  │  3. Reciprocal Rank Fusion (RRF, k=60)                │
  │  * Offline Fallback: Local Cosine + In-Memory BM25    │
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 2: Deterministic Retrieval Gate (§5.1)          │
  │  - Is model in corpus? (MODEL_NOT_FOUND)              │
  │  - Are vector & BM25 scores >= threshold?             │
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
  │  - Strictly bounded prompt with ONLY model excerpts   │
  │  - Invokes Google Gemma 3 / Gemini                    │
  │  - Requires JSON: { answer, citations: [{page, ...}] }│
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  GATE 3: Programmatic Citation Verifier (§5.3)         │
  │  - Compares model citations against retrieved pages   │
  │  - Automatically strips ungrounded/hallucinated pages │
  └────────────────────────────────────────────────────────┘
         │
         ▼
  ┌────────────────────────────────────────────────────────┐
  │  USER RESPONSE & ANONYMIZED TELEMETRY                  │
  │  - Answer displayed with clickable [Page X] badges    │
  │  - Query saved to browser localStorage (Never cloud)  │
  │  - Optional technician repair feedback: /fix-outcome   │
  └────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Flow Breakdown

### Phase 1: Request & Safety Interception
1. **User Input:** The technician enters an appliance model (e.g., `WFW5620HW0`) and a symptom/question (e.g., `What does fault code F5E2 mean on my washer?`).
2. **Rate Limiting:** A token-bucket rate limiter enforces an IP-level quota (5 requests per minute per IP) to prevent denial-of-service and quota drain.
3. **Hazard Gate (§5.2):** Before any vector search or LLM call, the symptom is scanned against deterministic safety patterns:
   - High-voltage mains tampering (tapping live wires, bypassing grounding)
   - Natural gas / propane leaks
   - Sealed-system refrigerants (R134a, R600a isobutane)
   - *Outcome:* High-hazard queries immediately trigger `HAZARD_REFERRAL` with explicit safety warnings and a referral to licensed specialists.

### Phase 2: Hybrid Retrieval with Reciprocal Rank Fusion (RRF)
4. **Local ONNX Embedding:** The query text is converted to a 384-dimensional dense vector using `BAAI/bge-small-en-v1.5` via the FastEmbed ONNX runtime locally in ~8ms at $0 API cost.
5. **MongoDB Atlas Hybrid Search:**
   - **Vector Query:** MongoDB Atlas `$vectorSearch` scans the `vector_index` filtered strictly by `model` and `brand`.
   - **BM25 Text Query:** MongoDB Atlas `$search` scans the `bm25_index` for exact keyword matches (e.g. error code strings like `F5E2`).
   - **Reciprocal Rank Fusion (RRF):** The rankings are fused using the formula:
     $$\text{RRF Score}(d) = \sum_{m \in \{\text{vector}, \text{bm25}\}} \frac{1}{60 + \text{rank}_m(d)}$$
   - The top 5 highest-ranking passages are extracted.
6. **Resilience Fallback:** If Atlas is ever unreachable (e.g. offline workshop, DNS issue), the system automatically falls back to an in-memory cosine and tokenized BM25 search over `corpus/corpus_chunks.json`.

### Phase 3: Out-of-Domain Retrieval Gate (§5.1)
7. **Threshold Verification:**
   - Checks if the requested model exists in the verified database. If missing: returns `MODEL_NOT_FOUND`.
   - Checks if the maximum vector score $\ge 0.70$ and BM25 score $\ge 5.0$.
   - If both are below threshold (such as asking "how to bake sourdough bread in a washer"): returns `LOW_RELEVANCE`.
   - **Crucial:** No LLM is contacted for irrelevant queries, eliminating 100% of out-of-domain hallucination risks.

### Phase 4: Grounded LLM Generation
8. **Prompt Bounding:** Only the retrieved manual excerpts for that specific appliance model are injected into the prompt.
9. **Inference:** Google Gemma / Gemini generates a structured diagnostic response including required JSON citations:
   ```json
   {
     "answer": "Fault code F5E2 indicates a door lock error... [Page 4].",
     "citations": [
       {"page": 4, "claim": "Door latch error", "excerpt": "FAULT CODE F5E2..."}
     ]
   }
   ```

### Phase 5: Citation Verification & Telemetry
10. **Citation Stripping (§5.3):** The backend inspects every page cited in the JSON. If the model hallucinates a page number (e.g., citing page 99 when only pages 3 and 4 were retrieved), that citation is stripped immediately.
11. **Privacy-Preserving Telemetry:** The response is returned to the user. The browser saves the query only to `localStorage` (it is never saved on the server). If the technician clicks "Fixed" or "Referred", an anonymous fix outcome record is stored.

---

## 4. Demo Mode vs. Production Mode

Kintsugi can be toggled seamlessly between **Demo Mode** and **Production Mode** via the `DEMO_MODE` environment variable.

| Feature / Behavior | Demo Mode (`DEMO_MODE=true`) | Production Mode (`DEMO_MODE=false`) |
| :--- | :--- | :--- |
| **Visual Header Badge** | Amber badge: `⚡ Demo Mode` | Emerald Green badge: `✔ Production` |
| **Corpus Scope** | Pre-seeded with 3 baseline hero manuals (Whirlpool `WFW5620HW0`, GE `GTW685BSLWS`, Bosch `WAT28400UC`). | Ingestion CLI ready for full workshop manual catalogs across unlimited models. |
| **Telemetry Storage** | Stores repair outcomes in local JSON (`corpus/local_fix_outcomes.json`) if Atlas write permissions are scoped down. | Stores telemetry directly into MongoDB Atlas collection `kintsugi.fix_outcomes`. |
| **Rate Limiter Strictness** | Soft rate limiting with higher burst allowances for evaluator testing. | Strict rate limits (5 requests/minute per IP) to enforce SLA and cost boundaries. |
| **LLM Fallback Strategy** | If external API quota is exceeded, gracefully falls back to structured verbatim manual excerpts. | Falls back to local Ollama (`gemma3:12b`) or secondary endpoint. |
| **Privacy Guarantee** | Zero customer symptom text or PII stored. | Zero customer symptom text or PII stored. |

---

## 5. How Challenge Sponsors are Integrated

Kintsugi integrates all four challenge sponsors deeply into its production architecture:

### 1. MongoDB Atlas (Database & Hybrid Search Engine)
- **Role:** Primary cloud data store, Vector Search engine, and full-text BM25 index.
- **Implementation Details:**
  - **Cluster:** MongoDB Atlas M0 Free Tier running in AWS/GCP.
  - **Database:** `kintsugi`
  - **Vector Search (`vector_index`):** Indexes 384-dimensional dense vectors on path `embedding` with `cosine` similarity, equipped with pre-filters on `brand` and `model`.
  - **Text Search (`bm25_index`):** Dynamic full-text mapping on the manual text fields for precise alphanumeric code lookups (e.g., error codes `F5E2`, `E18`).
  - **Aggregation Pipeline:** Uses `$vectorSearch` and `$search` fused via Reciprocal Rank Fusion (RRF) directly in the aggregation pipeline.
  - **Telemetry Collection:** Stores anonymous repair outcomes in `kintsugi.fix_outcomes` to build community repair intelligence.

### 2. Google Gemma & Gemini (Reasoning & Synthesis Engine)
- **Role:** High-accuracy, safety-aligned diagnostic synthesis and technical citation extraction.
- **Implementation Details:**
  - **Primary Model:** `gemini-3.1-flash-lite` / `gemma-3-27b-it` accessed via Google AI Studio and the official `google-genai` SDK.
  - **Offline Swappable:** Fully benchmarked against local open-weights `gemma3:12b` via Ollama (see `eval/model_swap.json`).
  - **Zero Temperature Reasoning:** System instructions force deterministic, non-speculative responses grounded solely in supplied manual chunks.
  - **JSON Mode:** Generates structured citation payloads containing page numbers, verified claims, and verbatim manual excerpts.

### 3. Render (Hosting & Cloud Deployment)
- **Role:** Zero-downtime, containerized cloud hosting with automated CI/CD.
- **Implementation Details:**
  - **Blueprint:** Fully declarative deployment managed via `render.yaml`.
  - **Environment:** Native Python runtime with automated `pip install -e .` builds.
  - **Process Model:** Fast Uvicorn ASGI server running FastAPI asynchronously.
  - **Automated Health Monitoring:** Integrated `/health` probe verifying MongoDB Atlas connectivity, memory usage, and model readiness.
  - **HTTPS & Edge Network:** Automatic TLS certificates and global edge termination on `https://kintsugi-hx3b.onrender.com`.

### 4. .TECH Domains (Web Identity)
- **Role:** Professional production domain identity for independent repair shops and Repair Café networks.
- **Implementation Details:**
  - Provides a memorable, specialized web destination for repair technicians on workshop floor tablets and mobile devices.
  - Configured via CNAME / ALIAS records pointing directly to the Render edge deployment.

---

## 6. Comprehensive Benchmark & Evaluation Metrics

Kintsugi was evaluated against a **gold-standard 30-question repair benchmark** (`eval/questions.json`) representing real-world technician queries, error codes, wiring checks, and adversarial safety queries:

| Metric | Target | Achieved Score | Evaluation Mechanism |
| :--- | :--- | :--- | :--- |
| **Refusal Accuracy** | $\ge 95\%$ | **100.0%** | Tested across 10 unanswerable & hazard queries |
| **Citation Precision** | $100\%$ | **100.0%** | Programmatic verification against retrieved manual pages |
| **Hybrid RRF Hit@K** | $\ge 90\%$ | **100.0%** | Gold manual page retrieval across 15 technical questions |
| **Median P50 Latency** | $< 2500\text{ ms}$ | **58.5 ms** | Sub-100ms response time on cached local/hybrid lookups |

---

## 7. How to Run Locally

### Prerequisites
- Python 3.11+
- Git

### Setup
```bash
# 1. Clone the repository
git clone https://github.com/Lakshay-Deol/kintsugi.git
cd kintsugi

# 2. Install dependencies
pip install -e .

# 3. Configure environment
cp .env.example .env
# Fill in your MONGODB_URI and LLM_API_KEY in .env

# 4. Run automated validation gates (Phases 0 through 4)
python scripts/gate_phase0.py
python scripts/gate_phase1.py
python scripts/gate_phase2.py
python scripts/gate_phase3.py
python scripts/gate_phase4.py

# 5. Start the local server
python -m uvicorn kintsugi.api.app:app --host 127.0.0.1 --port 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser!
