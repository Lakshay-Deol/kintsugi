# Kintsugi (金継ぎ)

> **Manual-Grounded AI Appliance Repair Assistant**  
> Built for the **DEV × Hacktoberfest 2026 Challenge** (Side Hustle Theme).  
> *The repair assistant that refuses before it hallucinates.*

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/Render-Live%20Demo-brightgreen.svg)](https://kintsugi-hx3b.onrender.com/ui/index.html)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20Vector%20Search-green.svg)](https://www.mongodb.com/atlas)
[![Google Gemma](https://img.shields.io/badge/Google-Gemma%204%20%2F%20Gemini-blue.svg)](https://ai.google.dev/)
[![Temporal](https://img.shields.io/badge/Temporal-Durable%20Workflow-black.svg)](https://temporal.io/)

---

## 1. Overview & Core Philosophy

In consumer appliance repair, an incorrect answer is far more dangerous than a simple refusal. A fabricated torque specification strips threading; an inaccurate electrical test creates a shock or fire hazard; a made-up diagnostic error code leads a technician to replace a costly control board unnecessarily.

**Kintsugi** is built around one uncompromising design principle:  
> **Refusing queries deterministically before calling an LLM is a safety and cost-control feature, not a failure.**

Kintsugi retrieves exclusively from the matched manufacturer service manual of the specific appliance model entered by the technician. If the manual is missing, if relevance scores fall below calibrated thresholds, or if the procedure presents severe safety hazards (natural gas lines, sealed refrigerants, live 240V mains electricity), Kintsugi **refuses deterministically with zero LLM API cost**. When evidence is found, all technical claims are verified against page-level citations.

---

## 2. Live Demo & Repository

- **Live Application URL:** [https://kintsugi-hx3b.onrender.com/ui/index.html](https://kintsugi-hx3b.onrender.com/ui/index.html)
- **Health Check Endpoint:** [https://kintsugi-hx3b.onrender.com/health](https://kintsugi-hx3b.onrender.com/health)
- **GitHub Repository:** [https://github.com/Lakshay-Deol/kintsugi](https://github.com/Lakshay-Deol/kintsugi)

---

## 3. How Challenge Sponsors are Integrated

Kintsugi integrates the hackathon sponsors into its production architecture:

### 1. MongoDB Atlas (Hybrid Search & Telemetry Database)
- **Atlas Vector Search (`vector_index`):** Indexes 384-dimensional dense vectors on `kintsugi.chunks` with pre-filters on `brand` and `model` to guarantee strict model isolation.
- **Atlas Text Search (`bm25_index`):** Dynamic full-text index scoring alphanumeric error codes (e.g., `F5E2`, `E18`) and component IDs.
- **Application-Side Fusion:** Fuses semantic vectors and BM25 keywords via Reciprocal Rank Fusion:
  `RRF Score = 1 / (60 + rank_vector) + 1 / (60 + rank_bm25)`
- **Telemetry Collection:** Stores anonymous technician repair outcomes in `kintsugi.fix_outcomes` to build community repair intelligence without storing customer diagnostic text.

### 2. Google Gemma (Diagnostic Reasoning & Synthesis)
- **Google Cloud Model (`gemma-4-26b-a4b-it`):** Primary production reasoning engine served via Google AI Studio using the official `google-genai` SDK.
- **Offline Open-Weights Model (`gemma3:12b`):** Benchmarked via Ollama for rural repair cafes and air-gapped basement workshops with zero internet.
- **Zero-Hallucination Prompts:** Prompts are bounded strictly to retrieved manual excerpts with required JSON output containing `[Page X]` citations.

### 3. Render (Zero-Downtime Deployment)
- **Infrastructure as Code:** Fully managed via a declarative [`render.yaml`](render.yaml) Blueprint.
- **Reverse Proxy Architecture:** Configured with `proxy_headers=True` and `forwarded_allow_ips="*"` to ensure individual client IPs behind Render's edge proxy are rate-limited independently (preventing "demo busy" collisions for evaluators).
- **Health Monitoring:** Automated `/health` endpoint checks database connectivity and reports demo mode status.

### 4. Temporal (Durable Diagnostic Agent & Flaky Call Recovery)
- **Durable Workflow (`src/kintsugi/workflows/temporal_flow.py`):** Wraps the entire diagnostic pipeline in a Temporal Workflow (`DiagnosticWorkflow`) separating hazard checks, hybrid retrieval, LLM synthesis, and citation verification into distinct Activities.
- **Automated Activity Retries:** Flaky external LLM requests automatically retry with exponential backoff (`initial_interval=1s, backoff=2.0, attempts=3`) so technicians never face dropped connections during critical repairs.

### 5. Tiger Data (pgvector Hybrid Search & Tiger MCP Management)
- **pgvector Storage (`src/kintsugi/tiger_data.py`):** Stores 384-dimensional FastEmbed embeddings with cosine distance (`<=>`) combined with full-text `tsvector` keyword matching on PostgreSQL.
- **Tiger MCP Tools:** Implements Model Context Protocol (MCP) tool schemas (`tiger_search_manual`, `tiger_list_indexed_models`) enabling autonomous coding agents to inspect, query, and manage the repair manual database.

---

## 4. The Three Safety & Refusal Gates

```
User Query (Model + Symptom)
   │
   ▼
[ Gate 1: Hazard Filter (§5.2) ] ──── Hazard Detected? ────► REFUSE: HAZARD_REFERRAL (No DB/LLM)
   │ (Safe)
   ▼
[ MongoDB Atlas Hybrid Retrieval ]
   │
   ▼
[ Gate 2: Retrieval Gate (§5.1) ] ─── Score Below Threshold? ─► REFUSE: LOW_RELEVANCE (No LLM)
   │ (Grounded Evidence Found)
   ▼
[ Grounded Gemma Synthesis ]
   │
   ▼
[ Gate 3: Citation Verifier (§5.3) ] ─ Ungrounded Page? ───► Programmatically Strip Page
   │
   ▼
Verified Diagnostic Answer with [Page X] Citations
```

1. **Hazard Gate (§5.2):** Intercepts dangerous operations (high-voltage mains tampering, natural gas leaks, sealed-system refrigerants) and issues deterministic safety notices.
2. **Retrieval Gate (§5.1):** Rejects unknown models (`MODEL_NOT_FOUND`) and low-relevance queries (`LOW_RELEVANCE`, e.g. baking bread in a washing machine) before calling the LLM.
3. **Citation Check (§5.3):** Programmatically validates all cited page numbers against retrieved chunks, stripping ungrounded pages.

---

## 5. Local Setup & Quick Start

### Prerequisites
- Python 3.11+
- Git

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/Lakshay-Deol/kintsugi.git
cd kintsugi

# 2. Install dependencies in editable mode
pip install -e .

# 3. Configure environment variables
cp .env.example .env
# Edit .env and insert your MONGODB_URI and LLM_API_KEY

# 4. Run the 5 automated verification gates
python scripts/gate_phase0.py
python scripts/gate_phase1.py
python scripts/gate_phase2.py
python scripts/gate_phase3.py
python scripts/gate_phase4.py

# 5. Start the local server
python -m uvicorn kintsugi.api.app:app --host 127.0.0.1 --port 8080
```

Open your browser at **[http://localhost:8080](http://localhost:8080)**.

---

## 6. Evaluation Sanity Check (30 Hand-Written Questions)

We evaluated Kintsugi against a benchmark of **30 hand-written test questions** (`eval/questions.json`) spanning Whirlpool, GE, and Bosch service manuals:

| Metric | Score | Scope & Details |
| :--- | :--- | :--- |
| **Refusal Accuracy** | **100.0%** (10 / 10) | Correctly refused unknown models, hazards, and out-of-domain queries |
| **Citation Precision** | **100.0%** | Zero ungrounded page citations survived programmatic verification |
| **Hybrid RRF Hit@K** | **100.0%** (15 / 15) | Gold manual page ranked in top-5 for all 15 answerable questions |
| **Retrieval P50 Latency** | **58.5 ms** | FastEmbed ONNX query embedding + local/hybrid search (retrieval only) |
| **End-to-End P50 Latency** | **~845 ms** | Complete pipeline including Google Cloud Gemma generation |

---

## 7. License & Disclaimers

- **License:** [Apache 2.0](LICENSE)
- **Privacy Notice:** Diagnostic search strings are not stored on our servers. In cloud mode, queries are processed via Google AI Studio subject to their API terms of service. Technician lookup history is stored solely in the client's browser `localStorage`.
