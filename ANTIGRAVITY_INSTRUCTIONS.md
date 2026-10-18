# Antigravity Operating Instructions — Kintsugi (Final, 36-Hour Edition)

> **Event:** DEV × Hacktoberfest 2026 (Week 2, Side Hustle).
> **Hard deadline:** Oct 18, 2026, 11:59 PM PDT (= Oct 19, ~12:29 PM IST).
> **Working target:** everything shipped and verified logged-out by **Oct 19, 06:00 IST**. The last 6 hours are buffer only.
>
> Place this file where Antigravity reads workspace rules (verify the current path in Antigravity's docs), and keep a copy at repo root as `ANTIGRAVITY_INSTRUCTIONS.md`.

---

## 0. Product in One Paragraph

Kintsugi (formerly FixMyAppliance Pro) is a manual-grounded repair assistant for repair technicians, small shops and Repair Café volunteers. The user enters an appliance model number and a symptom. The system retrieves from **that model's manual only** (MongoDB Atlas hybrid search: vector + BM25 fused with RRF), refuses if the evidence is not there, and otherwise answers with Gemma using page citations. Hazard topics get deterministic warnings. Hosted on Render and **served from a `.tech` domain**.

**The product's value is refusing correctly.** A refusal is a feature.

---

## 1. Standing Rules (Never Violate)

1. **Config over code.** Every model name, threshold, URL, index name, collection name, rate limit and API key lives in an environment variable (read via `os.environ`) or a gitignored config. Commit a `.env.example` with placeholder values only.
2. **Honesty is a feature.** Never invent manual content, citations, fix outcomes, evaluation numbers, users, quotes, prices or willingness-to-pay. If something does not exist, say so in the output and in the docs.
3. **Evidence per phase.** A phase is done only when its gate script exits 0 and its evidence files exist on disk. Claiming "done" without the script passing is a violation.
4. **Fallback first.** Every external dependency has a fallback in `docs/decisions.md`. If a primary fails, switch, log the switch with a timestamp, and continue. Do not stop and wait if a fallback exists.
5. **Cut order is fixed.** If time runs short, cut in this order: **photo/model-plate vision → figure/table chunks → pricing UI → local-model arm reduced to a 10-question subset**. Never cut: hybrid search, refusal gate, citation check, evaluation numbers, the privacy note, the writing block (see `plan.md` §9).
6. **Evidence comes only from this project's own runs.** Never copy metrics, screenshots, quotes or results from a reference repository.
7. **If these instructions conflict with a reference repository, these instructions win.**

---

## 2. Pre-Approvals (so you do not stall)

The owner has pre-approved the following. Everything else not listed requires asking.

| Item | Approved scope |
|---|---|
| Gemma provider | **Google AI Studio free tier** (default). Fallbacks: NVIDIA NIM free tier, then Ollama local |
| Database | **MongoDB Atlas M0** (free) |
| Hosting | **Render free web service** (fallback: $7 Starter only if OOM or unacceptable cold start. Log the reason, then ask before switching) |
| Domain | One `.tech` domain via the Hacktoberfest promo (hacktoberfest.com/my/promos). The app itself is served from it |
| Customer data | Only the **fix-outcome record** below, nothing else |
| Embeddings | Option A (local ONNX) first. Option B (hosted embedding API) **only if** Option A fails the memory test, **free tier only**, and the switch is logged |
| Uptime pinger | UptimeRobot free (or GitHub Actions cron as backup) |

**Fix-outcome record (the only customer-related data allowed in Atlas):**

```
{ model: string, symptom_category: enum, outcome: enum[fixed|partially|not_fixed|unsafe_referred],
  created_at: timestamp }
```

No free text. No names, emails, IPs, device IDs or photos. Job history stays in the browser's `localStorage` only.

**Still requires asking:** any paid service beyond the Render fallback above, any new data stored about users, deleting or overwriting evidence files.

---

## 3. Verified Constraints and Items to Verify

**Treat as true (from the plan):**
- Atlas M0: Vector Search supported, 512 MB storage, max 3 search/vector indexes per project.
- Render free: 512 MB RAM, 0.1 CPU, spins down after 15 min idle, 30–60 s cold start, 750 instance-hours/month (one always-on service fits).
- Gemma via AI Studio free tier: approx. 30 req/min, 15K tokens/min, 14.4K req/day for Gemma 3 models. **Log the actual limits observed in `docs/decisions.md`.**

**Verify in the first hour and log results in `docs/decisions.md` (do not assume):**
- The current Gemma generation and exact model ID on AI Studio (MLH materials mention Gemma 4; Gemma 3 IDs look like `gemma-3-12b-it`, not `-instruct`). Use the newest model that fits the free-tier limits and log it.
- Whether search/vector indexes can be created via driver, Atlas CLI or Admin API (the older claim "UI only" may be outdated). If not, use the UI and document the exact index JSON in `docs/atlas_indexes.md`.
- Whether `$rankFusion` is available on the M0 cluster's MongoDB version. If unsure, use app-side RRF (default).
- Current Google AI Studio free-tier data-use terms (needed for the privacy note).
- Embedding RAM on Render (Option A test below).

---

## 4. Architecture Decisions (Locked Unless a Gate Fails)

- **Backend:** FastAPI (or Flask), minimal dependencies, `PYTHONMALLOC=malloc`, no heavy runtime models.
- **Embeddings:** the same model for ingest and query. Never mix models.
  - **Option A:** quantized ONNX `bge-small-en-v1.5` via fastembed. Test peak RAM inside a Render-sized container during the slice phase. Pass if the service stays well under 512 MB with margin for requests.
  - **Option B (if A fails):** one hosted embedding model on a free tier for **both** ingest and query. Re-embed everything. Log the switch.
- **Retrieval:** Atlas vector search with `brand` and `model` pre-filters, plus Atlas Search (BM25) over the same filtered set, fused with RRF in app code (k from env).
- **Chunks:** page-aware, with metadata `brand, model, manual_id, page, section, type`. Figure/table chunks are cut-order item 2.
- **LLM adapter:** OpenAI-compatible interface using `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Gemma 3 handles system prompts poorly, so fold instructions into the user turn. There is no reliable JSON mode, so parse structured output defensively with a retry cap of 1.
- **Rate limiting:** per-IP and global caps (env-configured) on `/answer` so a public demo cannot burn the Gemma quota. Return a clear "demo busy" message.

---

## 5. Safety and Refusal Design

### 5.1 Retrieval gate (runs BEFORE any LLM call)

Refuse if **any** of these hold:
1. The normalized model number matches no manual in the corpus (normalize: case, spaces, dashes. Support documented suffix-variant matching, and log which variant matched).
2. No retrieved chunk belongs to the matched model.
3. The best **raw vector cosine score** is below `MIN_VECTOR_SCORE` **and** the best BM25 score is below `MIN_BM25_SCORE`.

**Do not threshold on RRF scores.** RRF scores are rank-based and not comparable across queries. Use RRF only for ordering.

Thresholds come from env vars, calibrated on the **dev split** of the eval set and reported on the **test split** (see §8).

Refusal responses include a reason code (`MODEL_NOT_FOUND`, `NO_MODEL_EVIDENCE`, `LOW_RELEVANCE`, `HAZARD_REFERRAL`) and a plain-language message. No agent retry loop may bypass this gate.

### 5.2 Hazard gate

- Keyword/pattern check on the symptom and the question for mains voltage, gas, refrigerant and similar hazards. Include synonyms and common misspellings, and test them.
- Hazard warnings are **static, curated text**, clearly labeled "General safety notice, not from the manual", prepended to any answer.
- For gas and refrigerant handling, do **not** generate step-by-step procedures. Return the manual's relevant cited passages if present, plus a referral to a licensed technician.

### 5.3 Citation check (after the LLM call)

- Ask Gemma for structured output: a list of `{claim, page}` items (plus the prose answer).
- Every cited page must exist in the retrieved set for the matched model. If not, strip that claim or flag the answer.
- If parsing fails after one retry, or no valid citation remains, **fall back to showing the retrieved passages verbatim** with page numbers, with no generated text.
- Each citation in the UI shows the page number and a short excerpt, linking to the source manual where permitted.

---

## 6. Phases, Time Boxes and Gates

Time boxes are ceilings. If a phase exceeds its box by 1 hour, apply the cut order or the fallback table and log the decision.

### Phase 0 — Setup and Risk-First Slice (≈ 3 h)

1. **Challenge rules (new-project rule):** the project and repo must be started and completed inside the challenge window (Oct 12–18). Create a **fresh repo (`git init`, not a fork)** with LICENSE, README stub, `.gitignore`, `.env.example`, secrets-scan config (gitleaks). Do not copy in any pre-Oct-12 code. Reuse of open-source code is allowed only if changes are significant and it is credited: keep `docs/reuse_ledger.md` (file/idea, license, what changed). Read the Week 2 challenge page and official rules, check eligibility and prize tax paperwork, and log differences in `docs/decisions.md`. Claim promos (Render credits, `.tech` code) at hacktoberfest.com/my/promos.
2. Atlas M0 cluster. Create a test doc and a test vector index.
3. Google AI Studio key. Test call to the verified Gemma model. Log observed rate limits.
4. **Deploy a thin slice to Render:** `/health` that also performs an Atlas ping. Commit a first `render.yaml`.
5. Embedding Option A memory test. Pick A or B. Log in `docs/decisions.md`.
6. Select 3 manuals (up to 5 only if time allows). Record license and excerpt rights per manual in `docs/manuals.md`. **Prefer openly licensed or clearly redistributable manuals.** If rights are unclear, the demo shows short excerpts plus a link to the original, never full pages.
7. Register the `.tech` domain, add it as a Render custom domain and set DNS immediately (DNS can lag). Confirm HTTPS before building on top. Fallback: if not working by T+20 h, serve a `.tech` landing page that links to the Render URL, and log it.
8. Message 3–5 potential users (technicians, shops, Repair Café volunteers). **Non-blocking.** Log who was contacted and when in `docs/first_user.md`.

**Gate (`scripts/gate_phase0.py`):** test doc present in Atlas, Gemma call returns text, `/health` reachable on the Render URL, `docs/manuals.md` and `docs/decisions.md` exist, and outreach is logged.

### Phase 1 — Data Layer (≈ 6 h)

1. Collections: `manuals`, `chunks`, `error_codes`, `fix_outcomes`, `ingest_jobs`.
2. Ingestion script (local, offline): PDF → page-aware chunks with metadata → embeddings → Atlas. Ingestion never runs on Render.
3. One vector index (filters: `brand`, `model`) and one Atlas Search (BM25) index. Document both index definitions in `docs/atlas_indexes.md`.
4. `error_codes` seed only from a source whose license is verified. If unverified, skip the seed and log it.
5. Hybrid search function: vector (filtered) + BM25 (filtered) → app-side RRF.
6. Write `evidence/phase1_chunks.json` (chunk counts per manual, generated by the ingestion script).

**Gate (`scripts/gate_phase1.py`):** chunk counts file exists and is non-zero per manual; 5 test questions return the expected gold pages in the top-k; filtered search with brand + model returns only that model's chunks.

### Phase 2 — Retrieval, Safety and Answers (≈ 6 h)

1. Implement §5.1 retrieval gate, §5.2 hazard gate, §5.3 citation check.
2. LLM adapter and `/answer` endpoint returning `{status: answered|refused, answer, citations[], reason_code, warnings[]}`.
3. Per-job logging of model calls and tokens (no user text persisted server-side).
4. Rate limiting (§4).

**Gate (`scripts/gate_phase2.py`):** every unanswerable dev question is refused before an LLM call (verify via logs), and no answer cites a page outside its retrieved set (programmatic check).

### Phase 3 — Product Surface (≈ 4 h)

1. UI (works on phone and laptop): model number input, symptom box, cited answer display, follow-up box, clear refusal display.
2. Job log in `localStorage` only.
3. Fix-outcome form storing only the §2 record. Include an empty state.
4. **Privacy note in the UI and README, accurate to behavior:** queries are sent to the hosted Gemma provider (Google AI Studio), and on the free tier the provider's terms may allow use of prompts for product improvement (state what the verified terms say). Job history stays in the browser. Only the minimal fix-outcome record is stored on the server.
5. **"Demo Mode" label** visible whenever a hosted Gemma endpoint is active.
6. The **full app** is reachable on the `.tech` domain over HTTPS (Render custom domain).
7. `/health` keep-alive: UptimeRobot every 10 min on the single service. Document in README. **Pre-warm the service before recording the video and before the deadline.**
8. Finalize `render.yaml`. It must deploy from the repo.

**Gate (`scripts/gate_phase3.py` plus manual check):** public URL works on phone and laptop; one cited answer and one refusal visible; Demo Mode label visible; privacy note present; `render.yaml` present; keep-alive configured.

### Phase 4 — Proof and User Validation (≈ 4 h)

1. Run the eval (§8) via script → `eval/results.json`.
2. **Model-swap comparison → `eval/model_swap.json`** (~1.5 h): run the same eval questions through the adapter with only env vars changed. Arm 1: Gemma via Google AI Studio. Arm 2: an open-weight model run locally (Ollama), as large as the laptop handles. Report citation precision, correctness on the reviewed subset, latency, tokens and cost. State honestly that in Arm 2 retrieval still uses Atlas, so it is not a fully offline claim. If short on time, run a 10-question subset and say so.
3. `eval/cost_comparison.md`:
   - Cost per query with Gemma (free tier = $0; also compute the equivalent paid cost if published pricing exists).
   - Cost per query with a closed API (e.g., GPT-4o mini, Claude Haiku) from **logged tokens × current published prices**. Include the date prices were checked and the source URL.
   - Break-even number of paying shops at a stated hypothetical price per month. Label it clearly as a **scenario, not validated pricing**.
4. User sessions (2–3 users, 2 real lookups each) **if anyone replied**. Ask: What did it get wrong? Would you pay, and how much per month? What do you want next? Record answers in their own words **with permission**. If nobody replied, write an honest statement of none in `docs/first_user.md`.
4. Fix wrong answers found.

**Gate (`scripts/gate_phase4.py`):** `eval/results.json` valid and complete, `eval/model_swap.json` exists, `eval/cost_comparison.md` has break-even and price sources, `docs/first_user.md` exists (quotes or honest "none").

### Phase 5 — Submission (≈ 5 h including buffer)

0. **Writing block (judged most heavily):** protect at least 3 h for the post; the draft (`docs/post_draft.md`) starts in Phase 2. Frame the user as an independent repair person or Repair Café volunteer earning on the side (theme: Side Hustle; confirm on the Week 2 page). Lead with the refusal story. Credit the base repo and any non-trivial prior work. Posts must be in English to be prize-eligible.
1. Demo video that **includes one refusal**.
2. README: architecture diagram, setup, license, sourced statistics, known limitations, the privacy note.
3. DEV post with the exact required template:
   - **What I Built:** technician scenario, who pays, why.
   - **Demo:** live Render link + video.
   - **Code:** repo link, eval set, results.
   - **How I Built It:** Gemma + Render + embedding model + Atlas + hybrid search + RRF.
   - **Why Does Open Innovation Matter?:** direct answer with measured cost numbers.
   - **My Agent Session:** optional (use the agent-session notes, §10).
   - **My First User:** feedback, exact quotes, willingness to pay (or honest "none yet").
   - **Prize Categories:** Gemma, Render, MongoDB Atlas, .tech: one sentence each, each pointing to a concrete feature.
4. Before publishing: read the official challenge rules once more and map every requirement to evidence. Run the secrets scan. Confirm the repo is public.
5. Submit well before the deadline.

**Gate:** post live with `devchallenge` and `hf26challenge` tags. **Every link works when logged out** (test in a private window and on mobile data).

---

## 7. Fallback Table

| Primary | Fallback | Trigger |
|---|---|---|
| Atlas Vector Search | Qdrant Cloud free tier OR in-app cosine over the filtered set | Index creation fails on M0 |
| Gemma via Google AI Studio | NVIDIA NIM free tier OR Ollama local | Rate limit or outage |
| Render free web service | Render $7 Starter (**ask first**) | OOM or unacceptable cold start |
| Local ONNX embeddings (Option A) | Hosted embedding API on free tier (Option B) | Memory test fails |
| Atlas `$rankFusion` | App-side RRF | Unavailable or unsure |
| Structured JSON from Gemma | Show retrieved passages verbatim | Parse fails after 1 retry |
| 3 users messaged | Honest "none yet" in `docs/first_user.md` | No reply by T+24 h |

Every switch is logged in `docs/decisions.md` with timestamp and reason. If a reference repo depends on a failed primary, use the fallback above, not the reference's dependency.

---

## 8. Evaluation Design

- **Size:** 30 questions: 20 answerable, 10 unanswerable.
  - Unanswerable mix: 4 unknown model, 3 known model with an out-of-manual question, 3 hazard/unsafe request.
- **Gold labels first:** write the gold page(s) for every answerable question **before** running anything.
- **Split:** `dev` (used to calibrate thresholds) and `test` (never used for tuning). Report test-split numbers as the headline.
- **Retrieval arms (own numbers):** vector-only vs BM25-only vs hybrid RRF, hit@k against gold pages.
- **Metrics recorded in `eval/results.json`:**
  - refusal accuracy (target: all unanswerable refused)
  - citation precision (target: 100%, no non-retrieved page cited)
  - retrieval hit@k per arm
  - answer correctness (human review, with the reviewer noted)
  - latency (median, p95)
  - tokens and cost per query (average)
- **Provenance in the file:** commit hash, config snapshot (with secrets excluded), timestamp, model IDs, number of questions. Results are generated only by `eval/run_eval.py`. **Never hand-edit `eval/results.json`.**
- State honestly in the README that 30 questions is a small sanity check, not a statistically strong benchmark.
- If photo/vision is shipped: evaluate it separately on about 10 real plate photos and report that number separately. If not shipped, do not claim it.

---

## 9. Evidence File Contract

| File | Contents | Phase |
|---|---|---|
| `docs/decisions.md` | Every technical choice, fallback, switch and verified limit | 0+ |
| `docs/manuals.md` | Manuals, licenses, excerpt rights | 0 |
| `docs/atlas_indexes.md` | Exact index definitions | 1 |
| `evidence/phase1_chunks.json` | Chunk counts per manual (script-generated) | 1 |
| `eval/results.json` | All metrics plus provenance | 2, 4 |
| `eval/cost_comparison.md` | Cost per query, price sources, break-even scenario | 4 |
| `docs/first_user.md` | Real quotes with permission, or honest "none" | 4 |
| `eval/model_swap.json` | Hosted-Gemma vs local-model comparison | 4 |
| `docs/reuse_ledger.md` | Reused pieces, licenses, what changed | 0+ |
| `render.yaml` | Deploy config | 3 |
| `README.md` | Architecture, setup, license, stats, limits, privacy | 5 |
| DEV post | Published with tags | 5 |
| Demo video | Includes one refusal | 5 |

**Gate scripts:** `scripts/gate_phase0.py` … `gate_phase4.py` check the files and conditions above and exit non-zero on any failure. Build each gate script at the start of its phase, so "done" is verified, not claimed.

---

## 10. Working Style for the Agent

- Produce a short plan artifact at the start of each phase and wait for owner approval only at: new paid service, new stored user data, deleting or overwriting evidence, Render paid upgrade.
- Keep terminal command review on for destructive commands (`rm`, force-push, DB drops, overwriting `eval/`, `evidence/`).
- Never commit `.env`. Run the secrets scan before the first public push and again before submission.
- Keep an **agent-session log** (`docs/agent_session.md`): what the agent did, what the owner corrected, and notable failures. This feeds the optional DEV post section.
- When uncertain about a fact (limits, licenses, prices, model IDs), **look it up and log the source in `docs/decisions.md`**, or mark it "unverified". Never fill it in from memory.
- Check time at each phase boundary. State elapsed time and remaining buffer.

---

## 11. Reference Repositories (Optional, Use at Most 2–3)

Reference only. Verify each URL, license and current architecture before adapting anything. They are not endorsements and not evidence for any gate.

| Repository | Use for | Phase | Cautions |
|---|---|---|---|
| `raghuram-chittibomma/ai-repair-assistant` | Safety-gate and citation patterns for manual Q&A | 2 | LAN-oriented. Adapt deployment. Verify license |
| `luisrodriguesphd/mcp-rag-agent` | Atlas vector + full-text + RRF structure, eval organization | 1, 4 | Replace hardcoded config |
| `MigueIAngel/docuchat-ai` | Render free-plan deployment and cold-start notes | 3 | Do not copy customer-data storage |
| `JaNNi10n/rag-retrieval-eval-gate` | BM25/dense/hybrid comparison structure | 1, 4 | Reference metrics are not project evidence |
| `jkelly-dev1/citation-abstention-rag` | Reason codes, citation verification | 2 | Keep this project's gates |
| `aliceli-dev/AgenticAI-RAG-HomeManualsAgent` | Evidence-grading flow | 2 | Retries must not bypass the refusal gate |
| `hriday-sehgal/RAG-Chatbot` | Atlas + Gemma + FastAPI wiring | 1, 2 | Confirm M0 limits |
| `vishalkoriyalearning/rag-serve` | Render API structure | 3 | No unapproved providers |
| `da3387745-ship-it/DEV-COMPASS` | `render.yaml` and backend layout | 3 | Verify license. Remove hardcoded config |

Before adapting any code: confirm license compatibility, remove hardcoded values (use env vars), confirm no paid or customer-data dependency, and never import its metrics or screenshots.

---

## 12. When Blocked

1. Check `docs/decisions.md` for a documented fallback.
2. If one exists, switch, log it, continue.
3. If none exists, **stop and ask**. Do not improvise a paid service, invent data, or skip a gate.
4. If a reference repo is inaccessible, unlicensed or incompatible, log it and continue with the documented fallback or ask.

## 13. What "Done" Means

A phase is done only when all its tasks are complete, its **gate script exits 0**, its evidence files exist on disk, and the next phase's prerequisites are met. Consulting a reference repository never makes a phase done.consider this and transform the given folder into this
</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-10-17T18:49:17+05:30.
</ADDITIONAL_METADATA>
<USER_SETTINGS_CHANGE>
The user changed setting `Model Selection` from None to Claude Sonnet 4.6 (Thinking). No need to comment on this change if the user doesn't ask about it. If reporting what model you are, please use a human readable name instead of the exact string.
</USER_SETTINGS_CHANGE>