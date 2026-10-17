---
title: "Kintsugi: A Manual-Grounded Repair Assistant That Knows When to Refuse"
published: false
tags: devchallenge, hf26challenge, gemma, mongodb, ai, python
canonical_url: https://kintsugi-repair.tech
cover_image: https://raw.githubusercontent.com/kintsugi-repair/kintsugi/main/docs/images/kintsugi-banner.png
---

# Kintsugi: A Manual-Grounded Repair Assistant That Knows When to Refuse

> *"The product's value is refusing correctly. In physical appliance repair, a confident hallucination can burn out a motor or shock a technician. Refusal is not a bug; it is the core safety feature."*

---

## 1. What I Built

Every weekend, thousands of independent repair technicians, small appliance fix shops, and Repair Café volunteers troubleshoot complex consumer appliances. When an error code like `F5E2` or `E18` flashes on a digital console, guessing is dangerous. High-voltage capacitors store lethal charges, gas valves risk explosion, and misdiagnosing an inverter drive motor wastes hundreds of dollars in unnecessary parts.

Generic LLMs are notorious for "helpful guessing" — inventing non-existent reset codes or suggesting steps from a top-load washer for a sealed front-load drum.

**Kintsugi** (named after the Japanese art of repairing broken pottery with gold lacquer) is a manual-grounded AI repair assistant engineered for repair technicians and side-hustle repairers. 

### The User Scenario & Business Model
- **Target User:** Independent technicians and Repair Café volunteers earning side income repairing household appliances.
- **The Problem:** Technicians lose 20–45 minutes per job searching fragmented online PDF service manuals, schematics, and service bulletins.
- **The Solution:** The user inputs an appliance model number (`WFW5620HW0`) and symptom (`error F5E2 door lock`). Kintsugi retrieves evidence **exclusively from that specific model's manufacturer manual**, enforces strict deterministic pre-LLM gates, and returns cited page-grounded instructions with direct excerpts.
- **Who Pays & Why:** Small repair shops and independent contractors pay a $19/month micro-SaaS subscription because getting an authoritative, grounded diagnostic in 30 seconds saves an hour of unbillable triage on every job.

---

## 2. Demo

- **Live Application:** [https://kintsugi-repair.tech](https://kintsugi-repair.tech) (hosted on Render over HTTPS)
- **Direct Render URL:** [https://kintsugi.onrender.com](https://kintsugi.onrender.com)
- **Demo Video:** [Watch the 3-minute Walkthrough & Live Refusal Demo](https://youtu.be/kintsugi-demo) *(Demonstrates exact pinout diagnostic test, followed by an intentional refusal when asked to service a high-risk gas line and an unknown model)*.

---

## 3. Code & Reproducibility

- **GitHub Repository:** [https://github.com/laksh/kintsugi](https://github.com/laksh/kintsugi) (Apache-2.0 License)
- **Evaluation Suite:** Complete 30-question gold-labeled test suite in `eval/questions.json`
- **Benchmark Results:** Provenance-stamped execution log in `eval/results.json`

### Tested Performance Across 30 Real Scenarios:
| Metric | Benchmark Result | Target |
|---|---|---|
| **Refusal Accuracy (Unanswerable & Hazard)** | **100.0%** | 100% |
| **Citation Precision (Zero Hallucinated Pages)** | **100.0%** | 100% |
| **Retrieval Hit@K (Hybrid RRF)** | **100.0%** | >90% |
| **Median Response Latency** | **845 ms** | <2000 ms |
| **Cost per Diagnostic Query** | **$0.000** | Free Tier |

---

## 4. How I Built It

Kintsugi transforms the manual retrieval problem through an authoritative 4-stage pipeline:

```
[User Input: Model + Symptom]
           │
           ▼
┌─────────────────────────┐
│   §5.2 Hazard Gate      │ ──[Gas / Refrigerant]──► Refuse & Refer to Licensed Tech
└─────────────────────────┘
           │ (Safe Query)
           ▼
┌─────────────────────────┐
│   §5.1 Retrieval Gate   │
│  - Normalized Model Match
│  - Atlas Hybrid Search  │ ──[Low Relevance / No Model]──► Refuse Gracefully
│    (Vector + BM25 + RRF)│
└─────────────────────────┘
           │ (Authoritative Passages)
           ▼
┌─────────────────────────┐
│  Gemma 3 (27B IT) LLM   │
│  - Zero System Prompts  │
│  - Structured JSON Mode │
└─────────────────────────┘
           │ (Generated Claims)
           ▼
┌─────────────────────────┐
│  §5.3 Citation Check    │ ──[Uncited / Hallucinated Page]──► Strip Claim or Fallback to Verbatim
└─────────────────────────┘
           │
           ▼
[Cited Answer with Verbatim Excerpts & Page Links]
```

### Core Architecture:
1. **Google Gemma 3 (27B IT via Google AI Studio):** Powers grounded diagnosis without system-prompt fragility by packaging grounding rules and extracted excerpts directly into the single turn.
2. **MongoDB Atlas Hybrid Search:** Combines HNSW Vector Search (`bge-small-en-v1.5` 384-dim ONNX embeddings) with Atlas Search BM25 full-text queries, fused using app-side Reciprocal Rank Fusion ($k=60$).
3. **Deterministic Safety Architecture:**
   - **Pre-LLM Retrieval Gate (§5.1):** Rejects any query whose cosine similarity is below 0.70 and BM25 score is below 5.0, saving LLM calls.
   - **Hazard Detection (§5.2):** Deterministically catches mains voltage, gas lines, and refrigerants with static safety warnings.
   - **Post-LLM Citation Verification (§5.3):** Programmatically validates every claimed citation against retrieved passages. If an uncited page is found, it is stripped or replaced with verbatim manual text.
4. **Render Deployment:** Single unified web service deployed via `render.yaml` with continuous health checks and UptimeRobot keep-alives.

---

## 5. Why Does Open Innovation Matter?

In our comparative cost analysis (`eval/cost_comparison.md`), we calculated the exact unit economics of closed proprietary APIs versus open-weight models:

- A closed commercial model (GPT-4o mini or Claude 3.5 Haiku) costs between **$0.34 and $2.00 per 1,000 diagnostic queries**.
- For a small repair business or Repair Café processing 10,000 lookups a month, proprietary API fees create unpredictable marginal costs that penalize usage.
- **Open Innovation changes the equation:** Gemma open weights provide state-of-the-art diagnostic reasoning at **$0.00 marginal cost**. Furthermore, as demonstrated in our model-swap benchmark (`eval/model_swap.json`), technicians in low-connectivity rural workshops can run Kintsugi completely offline using local Ollama on their laptop without changing a single line of application code.

Open weights empower independent workers to build self-sustaining side hustles without vendor lock-in.

---

## 6. My Agent Session

Developing Kintsugi was pair-programmed with Google Antigravity IDE:
- **What the Agent Did Well:** Implemented mathematical RRF rank fusion, deterministic regex hazard filtering, and written test client simulations rapidly.
- **Where the Agent Struggled:** Handled PowerShell multiline quote escaping poorly when generating static HTML directly, and initially counted domain stopwords ("washer") toward BM25 relevance until corrected.
- **Key Takeaway:** Agentic workflows excel when constrained by strict phase gates and evidence files (`scripts/gate_phaseX.py`). Having automated gates eliminated hallucinated claims of "done".

---

## 7. My First User Feedback

During early testing, we engaged local repairers to test Kintsugi against real washer error queries:
- **Participant:** Independent Appliance Specialist & Volunteer Repairer
- **Reaction:** *"Most AI chatbots just tell you to check the breaker or call someone. Seeing the exact pinout numbers on the DL3 connector and knowing it came from page 10 of the actual manual gives me immediate confidence."*
- **Willingness to Pay:** Stated they would comfortably pay $15–$25/month if the corpus is expanded to include refrigerators and dryers.
- Full interview notes documented in `docs/first_user.md`.

---

## 8. Prize Category Mapping

- **Gemma:** Powered by Google Gemma 3 (27B IT) for structured manual-grounded extraction and diagnostic synthesis.
- **Render:** Hosted on Render with automatic deployments, environment management, and `/health` monitoring via `render.yaml`.
- **MongoDB Atlas:** Leverages MongoDB Atlas M0 for unified vector search and BM25 search with brand/model pre-filtering.
- **.tech Domain:** Production web application served with SSL from custom `.tech` domain ([https://kintsugi-repair.tech](https://kintsugi-repair.tech)).

---

*Built with care for Hacktoberfest 2026. Keep fixing, keep learning.*\n