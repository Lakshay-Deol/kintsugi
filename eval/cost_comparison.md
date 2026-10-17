# Cost Comparison and Unit Economics

**Document Date:** October 17, 2026  
**Project:** Kintsugi — Manual-Grounded Repair Assistant  
**Challenge:** DEV × Hacktoberfest 2026 (Side Hustle Edition)

---

## 1. Token Budget per Query

Based on actual measurements across the 30-question evaluation benchmark (`eval/results.json`):

| Component | Average Tokens | Notes |
|---|---|---|
| User query + appliance metadata | 35 | Model number, brand, symptom |
| Retrieved evidence pack (top-5 chunks) | 1,120 | Verbatim manual passages with page citations |
| System instructions & schema | 250 | Grounding rules, citation formatting |
| **Total Prompt (Input) Tokens** | **1,405** | Measured average per query |
| **Generated Answer (Output) Tokens** | **220** | Diagnostic steps + structured citation array |
| **Total Tokens / Query** | **1,625** | Total per completed lookup |

---

## 2. API Pricing Comparison

Prices verified on October 17, 2026 from official pricing pages:

| Provider & Model | Input Price (/1M tokens) | Output Price (/1M tokens) | Source URL | Cost per Query (1,405 in, 220 out) |
|---|---|---|---|---|
| **Google Gemma 3 (via AI Studio Free Tier)** | **$0.00** | **$0.00** | https://ai.google.dev/pricing | **$0.00000** |
| Google Gemini 1.5 Flash (Paid Tier) | $0.075 | $0.30 | https://ai.google.dev/pricing | $0.00017 |
| OpenAI GPT-4o mini | $0.15 | $0.60 | https://openai.com/api/pricing/ | $0.00034 |
| Anthropic Claude 3.5 Haiku | $0.80 | $4.00 | https://www.anthropic.com/pricing | $0.00200 |
| Local Open-Weight (Ollama on Laptop) | $0.00 | $0.00 | Self-hosted hardware | Hardware amortization (~$0.00005 elec.) |

---

## 3. Cost at Scale (10,000 Lookups / Month)

For an active network of independent technicians, small appliance repair shops, and Repair Café volunteers:

| Model / Provider | Monthly API Cost (10k queries) | Annual API Cost |
|---|---|---|
| **Gemma 3 (Google AI Studio Free Tier)** | **$0.00** | **$0.00** |
| Google Gemini 1.5 Flash | $1.71 | $20.52 |
| OpenAI GPT-4o mini | $3.43 | $41.16 |
| Anthropic Claude 3.5 Haiku | $20.04 | $240.48 |

---

## 4. Break-Even Scenario for a Side Hustle / Micro-SaaS

> [!NOTE]
> This is a hypothetical scenario illustrating unit economics, not validated pricing.

### Assumptions:
- **Subscription Price:** $19 / month per technician / repair shop.
- **Estimated usage per shop:** 150 lookups / month (5 repairs/day × 30 days).
- **Fixed Infrastructure Costs:**
  - Render Web Service: $0 (Free Tier) or $7 / month (Starter plan).
  - MongoDB Atlas M0: $0 (Free Tier, 512 MB).
  - Custom `.tech` Domain: $0 (Hacktoberfest free promo).
  - Total Fixed Costs: **$7.00 / month** (assuming paid Render service for 0% cold start).
- **Variable LLM Costs (GPT-4o mini fallback):** 150 lookups × $0.00034 = $0.051 / shop / month.
- **Variable LLM Costs (Gemma Free Tier):** **$0.00**.

### Break-Even Calculation:
- **Net Margin per subscriber (at $19/mo with Gemma):** $19.00 - $0.00 = $19.00.
- **Break-even Subscribers:**
  $$\\text{Break-even} = \\frac{\\text{Fixed Costs (\$7/mo)}}{\\text{Net Margin (\$19/mo)}} \\approx 1 \\text{ subscriber}$$
- **Just 1 paying repair shop** covers all hosting and infrastructure costs for the entire platform.
- At **10 paying shops ($190/mo revenue)**: Gross profit is **$183 / month ($2,196 / year)** on zero marginal AI cost.

---

## 5. Why Open Innovation Matters

1. **Zero Inference Marginal Cost:** Gemma open weights allow local deployment via Ollama for technicians with poor workshop Wi-Fi, completely removing API bill anxiety.
2. **Deterministic Safety without Token Tax:** Because Kintsugi uses deterministic §5.1 retrieval gates and §5.2 regex hazard detection *before* invoking an LLM, 100% of out-of-domain and hazardous queries are stopped with zero LLM API calls and zero latency penalty.
3. **Reproducibility:** Technicians and Repair Café volunteers aren't subject to closed vendor model deprecations or sudden token price hikes.\n