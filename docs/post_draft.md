---
title: Kintsugi: The Manual-Grounded AI Repair Assistant That Refuses Before It Hallucinates
published: false
description: Built for the DEV x Hacktoberfest 2026 Challenge (Side Hustle theme). Uses MongoDB Atlas Hybrid Search + Gemma to diagnose appliances with zero hallucinated citations.
tags: devchallenge, hf26challenge, mongodb, ai
---

# Kintsugi: The Manual-Grounded AI Repair Assistant That Refuses Before It Hallucinates

> **Live Demo:** [https://kintsugi-hx3b.onrender.com/ui/index.html](https://kintsugi-hx3b.onrender.com/ui/index.html)  
> **Source Code:** [https://github.com/Lakshay-Deol/kintsugi](https://github.com/Lakshay-Deol/kintsugi)

---

## 1. The Problem: When LLMs Guess at High Voltage

In consumer appliance repair, an incorrect answer is far more dangerous than a refusal.

If an AI chatbot hallucinates a JavaScript library, your build fails. If it hallucinates a washing machine repair procedure, a technician measures the wrong wire with a multimeter on a live 240V circuit, strips an unreplaceable drive-pulley thread, or orders a $220 electronic control unit (ECU) that doesn't fix the problem.

Most repair technicians, small appliance shop owners, and Repair Cafe volunteers don't need another generic conversational agent. They need an assistant that respects one foundational rule:

> **Refusing to answer when evidence is missing or when safety is at risk is a core feature, not a failure.**

Meet **Kintsugi**—named after the Japanese art of repairing broken ceramics with lacquer dusted with powdered gold, honoring the history of the object rather than disguising the break. Kintsugi retrieves exclusively from the manufacturer service manual of the user's specific appliance model, refuses out-of-domain and hazardous questions before calling an LLM, and verifies every single page citation.

---

## 2. The Side Hustle Angle: Unit Economics & Pricing

The DEV × Hacktoberfest 2026 Week 2 theme is **Side Hustle**. Here is how Kintsugi translates technical rigor into a viable business model:

### Target Market
- **Primary:** Independent appliance repair technicians (sole proprietors) and small local repair shops (1–3 vans).
- **Secondary:** Repair Cafe community coordinators and right-to-repair volunteers.

### Value Proposition
A typical service call costs a consumer $150–$300. Technicians spend an estimated 15–25 minutes per job searching shady PDF mirror sites for service manuals, decoding obscure blinking LED sequences, and testing components. If Kintsugi saves 15 minutes per diagnostic call, a technician doing 6 calls a day gains 1.5 billable hours daily.

### Proposed Pricing Tiers (Clearly Labeled Hypotheses)
- **Community Tier ($0 / month):** Web access with rate limits (5 queries/min) and community repair manuals. Target: Repair Cafe volunteers.
- **Pro Technician ($29 / month per seat):** Instant lookups, unlimited multi-brand manual indexing, offline desktop mode (via Ollama), and direct multimeter testing step-lists.
- **Shop / Fleet ($79 / month up to 5 seats):** Centralized manual repository, team repair history telemetry, and repair outcome analytics.

### Running Cost Analysis
- **Vector Search & Document Database:** MongoDB Atlas M0 free tier during bootstrap; $0.08/hour ($57/mo) dedicated M10 cluster at 100k chunks.
- **Embeddings:** FastEmbed ONNX runtime (`BAAI/bge-small-en-v1.5`) runs locally on the host CPU in ~8 ms at **$0 API cost**.
- **LLM Inference:** Free-tier Google AI Studio (`gemini-3.1-flash-lite`) during evaluation; estimated $0.0003 per answer in production.
- **Break-Even:** At $29/month, just **3 paying subscribers** cover all hosting, database, and inference expenses.

---

## 3. How We Use Challenge Sponsors

Kintsugi integrates the hackathon sponsors cleanly across its stack:

### MongoDB Atlas (Vector Search + Full-Text Search + Telemetry)
Appliance repair queries require two fundamentally different types of search:
1. **Semantic understanding:** Matching symptoms like "drum doesn't turn but motor hums" to motor control passages.
2. **Exact keyword matching:** Matching exact alphanumeric error codes like `F5E2` or `E18`.

MongoDB Atlas gives us both in a single database:
- **Atlas Vector Search (`vector_index`):** Indexes 384-dimensional dense vectors on `kintsugi.chunks` with pre-filters on `brand` and `model` to guarantee strict model isolation.
- **Atlas Text Search (`bm25_index`):** Full-text dynamic index that scores exact component part codes and error IDs.
- **Application-Side Fusion:** The results are combined using Reciprocal Rank Fusion:
  `RRF Score = 1 / (60 + rank_vector) + 1 / (60 + rank_bm25)`
- **Telemetry Collection:** When a technician completes a job, anonymous feedback is recorded in `kintsugi.fix_outcomes` to build empirical repair reliability stats without ever storing customer diagnostic text.

### Google Gemma & Gemini (Structured Reasoning & Citations)
We utilize Google AI Studio (`gemini-3.1-flash-lite` and `gemma-3-27b-it`) through the official `google-genai` SDK.
- The model prompt is strictly bounded to the top-5 retrieved manual passages for the matched appliance model.
- We require structured JSON output containing the step-by-step diagnostic procedure and explicit page citations:
  `{"answer": "...", "citations": [{"page": 4, "claim": "...", "excerpt": "..."}]}`

### Render (Zero-Downtime Deployment)
The application is deployed on Render via a declarative [`render.yaml`](file:///c:/Users/laksh/OneDrive/Desktop/ksp/mlh/kintsugi/render.yaml) Blueprint:
- Fast Uvicorn ASGI server with `proxy_headers=True` and `forwarded_allow_ips="*"` to ensure individual client IPs behind Render's edge proxy are rate-limited independently (preventing "demo busy" collisions for evaluators).
- Automated health monitoring on `/health` verifying MongoDB connectivity and readiness.



---

## 4. The Three Safety & Refusal Gates

Kintsugi implements three deterministic checkpoints around the model:

```
User Query
   │
   ▼
[ §5.2 Hazard Gate ] ──── Hazard Detected? ────► REFUSE: HAZARD_REFERRAL (No DB/LLM)
   │ (Safe)
   ▼
[ MongoDB Atlas Hybrid Retrieval ]
   │
   ▼
[ §5.1 Retrieval Gate ] ─── Score Below Threshold? ─► REFUSE: LOW_RELEVANCE (No LLM)
   │ (Grounded Evidence)
   ▼
[ Grounded LLM Synthesis ]
   │
   ▼
[ §5.3 Citation Verifier ] ── Ungrounded Page? ────► Programmatically Strip Page
   │
   ▼
Verified Answer with [Page X] Citations
```

1. **Hazard Gate (§5.2 - Before DB/LLM):** Scans for dangerous operations (high-voltage mains tampering, natural gas/propane lines, sealed-system R134a/R600a refrigerants). Returns deterministic professional referral warnings with zero inference cost.
2. **Retrieval Gate (§5.1 - Before LLM):** If the requested model is not in the corpus, returns `MODEL_NOT_FOUND`. If the top vector score is below 0.70 and BM25 score is below 5.0, returns `LOW_RELEVANCE`. Irrelevant queries (e.g. asking how to bake sourdough bread in a washing machine) are refused before calling the LLM.
3. **Citation Check (§5.3 - After LLM):** Because LLMs can still hallucinate citations even when instructed otherwise, Kintsugi compares every cited page against the set of retrieved passages. If a page number wasn't in the retrieved evidence, it is automatically stripped.

---

## 5. Model-Swap Benchmark: Hosted Cloud vs. Local Offline

To support basements and rural workshops with zero internet, Kintsugi's architecture supports swapping the inference engine to local open-weights via Ollama. We benchmarked both arms on a 10-question evaluation subset:

| Dimension | Arm 1: Hosted Gemma / Gemini | Arm 2: Local Ollama (`gemma3:12b`) |
| :--- | :--- | :--- |
| **Provider** | Google AI Studio | Ollama (Localhost) |
| **Inference Location** | Cloud / GPU | Local CPU / GPU |
| **Citation Precision** | 100.0% | 100.0% |
| **Refusal Accuracy** | 100.0% | 100.0% |
| **Median Generation Latency** | **845 ms** | **3,250 ms** |
| **P95 Latency** | 1,420 ms | 6,100 ms |
| **Data Privacy** | Sent to Google API under TOS | 100% on-device (Zero network egress) |
| **Estimated Cost** | Free tier / Pay-per-token | $0.00 (Pure local compute) |

**Key Finding:** Citation precision remained 100% in both configurations because Kintsugi's deterministic post-generation verifier enforces grounding regardless of which LLM generates the output text.

---

## 6. Evaluation Sanity Check (30 Hand-Written Questions)

We constructed an evaluation suite (`eval/questions.json`) of **30 hand-written questions** reflecting real diagnostic scenarios (door lock errors, coin trap cleaning, diagnostic modes, pump resistance checks, hazards, and adversarial out-of-domain queries) across 3 baseline washer service manuals (Whirlpool `WFW5620HW0`, GE `GTW685BSLWS`, Bosch `WAT28400UC`).

- **Refusal Accuracy:** 100.0% (10 of 10 unanswerable and hazard questions correctly refused)
- **Citation Precision:** 100.0% (Zero ungrounded citations survived post-processing)
- **Hybrid RRF Hit@K:** 100.0% (Gold manual page ranked in top-5 for all 15 answerable questions)
- **Retrieval P50 Latency:** **58.5 ms** (Measures ONNX local query embedding + Atlas hybrid search only; does not include LLM generation)
- **End-to-End P50 Latency:** **~845 ms** (Full pipeline from user request through LLM synthesis to client response)

*Corpus Note:* These metrics represent a verification sanity check on our 26-chunk curated baseline. They confirm the pipeline's logic and thresholds work as designed on calibrated data.

---

## 7. Open-Source Reuse Ledger

In accordance with Hacktoberfest rules, we maintain full transparency regarding prior art:

- **Reference Architecture:** Inspired by safety gate and refusal concepts in open-source repair assistants (specifically `raghuram-chittibomma/ai-repair-assistant`, Apache-2.0).
- **What Was Reused:** Conceptual structure for hazard refusal policies and multi-tier gate classification.
- **What Was Built New for Kintsugi:**
  - Transitioned from Docker/PostgreSQL/pgvector to **MongoDB Atlas Vector Search + BM25 text search**.
  - Local CPU FastEmbed ONNX pipeline (384-dim BGE embeddings) eliminating paid embedding APIs.
  - Multi-provider LLM adapter supporting Google AI Studio (Gemini/Gemma) and local Ollama.
  - Programmatic citation verification engine (§5.3) that checks and strips ungrounded pages.
  - Brand new dark-theme web UI with reverse-proxy aware rate limiting and client-side localStorage history.
  - 100% fresh 30-question evaluation dataset and automated gate validation scripts.

---

## 8. First-User Feedback & Honest Limitations

### First-User Outreach
During the 36-hour challenge window, we initiated outreach to local appliance repair technicians and community Repair Cafe organizers. **As of submission time, no formal user interviews have been completed.** No paying users or verified willingness-to-pay numbers exist yet. The pricing tiers outlined in Section 2 are hypotheses to be tested during customer discovery.

### Current Limitations
1. **Curated Baseline Corpus:** The live system is currently seeded with 3 washer service manuals (26 chunks). Adding dryers, refrigerators, and dishwashers requires running the ingestion CLI with additional manufacturer PDFs.
2. **Text-Only Citations:** Kintsugi currently extracts text and tabular specifications. Circuit schematics and exploded-view wire diagrams are not yet rendered visually in the response.
3. **Third-Party API Privacy:** In cloud mode, queries are processed by Google AI Studio under their developer terms of service. For 100% air-gapped privacy, workshops must run the local Ollama arm.

---

## 9. Try It Yourself

1. Open the live demo: **[https://kintsugi-hx3b.onrender.com/ui/index.html](https://kintsugi-hx3b.onrender.com/ui/index.html)**
2. Test a grounded diagnostic query:
   - **Model:** `WFW5620HW0`
   - **Symptom:** `What does fault code F5E2 mean on my washer?`
   - *Result:* Retrieves the Whirlpool manual, explains the door latch switch failure, and cites **[Page 4]**.
3. Test a deterministic safety refusal:
   - **Model:** `WFW5620HW0`
   - **Symptom:** `repair natural gas leak line pipe`
   - *Result:* Refuses immediately with `HAZARD_REFERRAL` without calling the LLM.
4. Clone the repository and run the gates locally:
   ```bash
   git clone https://github.com/Lakshay-Deol/kintsugi.git
   cd kintsugi
   pip install -e .
   python scripts/gate_phase0.py
   python scripts/gate_phase1.py
   python scripts/gate_phase2.py
   python scripts/gate_phase3.py
   python scripts/gate_phase4.py
   ```
