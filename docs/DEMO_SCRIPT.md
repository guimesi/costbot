# GP Screening Cost Estimator — Live Demo Script

> **Purpose:** Step-by-step guide to walk through a live demonstration of the
> cost-bot application. Each section tells you exactly what to enter, what you
> should see on screen, and what it means.
>
> **Audience:** Stakeholders, reviewers, or anyone evaluating the POC.
>
> **Time required:** ~20 minutes for the full walkthrough; ~8 minutes for the
> highlights-only path (Scenarios 1 + 3).

---

## 0. Prerequisites

| Item | Detail |
|---|---|
| App URL | Open the **cost-bot** Databricks App (Streamlit), or locally: `streamlit run app.py` (see CLAUDE.md for setup) |
| Browser | Chrome / Edge recommended; any modern browser works |
| Data | No setup needed — the app loads all CSV data automatically on startup. Locally this is the MOCK package in `data/`; numbers are synthetic. |
| Credentials | Any user with workspace access can view the app |

When the app opens you will see:
- **Header:** "GP screening cost estimator" with a "POC v1.1" badge and the disclaimer line
- **3 pages** in the top navigation: Estimator · Models · Data
- The **Estimator** page is active by default: input cards on the left, and on the right a **Model readiness** card plus a short "How it unlocks" guide

---

## 1. Understanding the Layout (Estimator Tab)

The Estimator tab is split into two columns:

**Left column, input cards (top to bottom):**

| Card | What it does |
|---|---|
| **Project** | Archetype, location, basis year (2024/2025/2026 buttons), scope type buttons, project name. *Required*: archetype + location. "Optional details" holds process domain. |
| **Equipment list** | Type + count + Add. Same type added twice merges the counts. Unlocks the equipment vector model (best broad model). |
| **Facility and capacity** | Facility type (dropdown you can also type into), capacity + unit. Pipeline / offshore / LNG fields appear for those archetypes. |
| **Subsea scope (SURF)** | Offshore archetypes only. Trees, flowlines, risers, manifolds, umbilicals. |
| **Scope items** | Type + facility name + Add. Unlocks the composite chip model. |
| **Run screening estimate** | Primary button at the bottom. |

**Right column:**
- **Model readiness** updates live as you type, before any Run: each eligible model shows *Ready*, *Needs …*, or *Excluded for this archetype*. This is the "progressive disclosure" from the task brief.
- After Run: three KPI cards (P50, range, confidence), warnings, the **Model estimates** chart (bars = estimates, whiskers = each model's range, dashed line = ensemble P50, colour = role in the ensemble), one tab per model with its detail, **Comparable projects**, **Bid check**, **What-if**, and **Download HTML report**.
- If you change any input after a Run, a notice says the results are stale until you Run again.

---

## Scenario 1: Onshore Petrochemical — Minimal (Simple)

> **Goal:** Show the simplest path — just Core Inputs + Facility & Capacity
> Demonstrates Benchmark + Calculator_Onshore firing together.

### Step 1 — Fill Core Inputs

| Field | Value to Enter | Why |
|---|---|---|
| Project Archetype | **Petrochemical (Onshore)** | Tells the engine which models are eligible |
| Process Domain | *Leave as “— Optional —”* | Optional — helps Benchmark refine analogues |
| Location (CP30 Region) | **US Gulf Coast** | Required — drives location cost normalization (CP30) and EMMA factor |
| Basis Year | **2024** | All pool data is in 2024 USD; selecting 2024 avoids escalation |
| Scope Type | **Greenfield** | Determines TEC multiplier (greenfield = 2.58×, brownfield = 1.30×) |
| Rough size | *Optional* (e.g. **Substantial, $500M to $1B**) | Your order-of-magnitude judgement; narrows the benchmark to similar-sized analogues. Without it the benchmark matches on category only. |
| Project Name | **Demo Polypropylene Plant** | Optional label — appears in reports |

### Step 2 — Fill Facility & Capacity

| Field | Value to Enter |
|---|---|
| Facility Type | select **polypropylene** from the dropdown (the list is every facility type the calculators understand; pick "Other" to type a custom name) |
| Primary Capacity | **450** |
| Unit | **KTA** |

> **What this means:** You're describing a 450 KTA (kilotonnes per annum)
> polypropylene plant on the US Gulf Coast. The engine will look up the
> polypropylene ISBL correlation (base cost $136M at 450 KTA reference capacity)
> and apply the six-tenths scaling rule.

### Step 3 — Click "Run Screening Estimate"

### What You Should See

**Model readiness (right side, top), already visible before you press Run:**
- Benchmark (analogues) **Ready**
- Onshore calculator **Ready**, OSBL overlay **Ready** (automatic)
- Equipment vector *Needs at least one equipment item*
- Composite *Needs at least one scope item*

**KPI cards:**

| Card | What It Shows | What It Means |
|---|---|---|
| **Best estimate (P50)** | e.g. ~$500M | The median of surviving model estimates after spread gating. This is the single-number screening estimate. |
| **Range (P20-P80)** | e.g. $300M — $800M | The uncertainty band. P20 = "there's a 20% chance it's below this." P80 = "80% chance it's below this." |
| **Confidence** | MEDIUM or MEDIUM-HIGH | How many models agree. HIGH = 3+ models within ±30%. MEDIUM = 2 models, some disagreement. LOW = 1 model only. |

**Model estimates chart:**
- One horizontal bar per model that fired, whiskers show each model's own range
- Colour = role: in ensemble, gated out, component (SURF), indirect overlay (OSBL)
- Dashed red vertical line = the ensemble P50; hover for exact values
- Below the chart, one tab per model with the calculation detail and the analogues or equipment matches it used

**Analogues Table:**
- Shows the top 10 most similar projects from the 503-project pool
- Columns: project name, archetype, TEC, location, capacity, similarity score
- These are the projects the Benchmark model used to form its estimate

> **Talking Point:** "With just 6 fields filled in, two independent models
> produced estimates. The Calculator used engineering correlations (ISBL scaling),
> while the Benchmark found similar real projects from our 503-project pool.
> The ensemble mediates between them."

---

## Scenario 2: Offshore FPSO (Full Feature Walkthrough)

> **Goal:** Show all input cards including Equipment List and SURF scope.
> Demonstrates 4 models firing simultaneously.

### Step 1 — Core Inputs

| Field | Value |
|---|---|
| Project Archetype | **Offshore FPSO** |
| Process Domain | *Leave optional* |
| Location | **Guyana** |
| Basis Year | **2024** |
| Scope Type | **Greenfield** |
| Project Name | **Demo Deepwater FPSO** |

> **Note:** When you select "Offshore FPSO", two things happen:
> 1. Card 3 shows **Offshore Parameters** (Topsides Weight, Water Depth, Hull Type)
> 2. Card 4 (SURF Subsea Scope) appears

### Step 2 — Equipment list card

Add the following equipment items one at a time (select type → set count → click "+ Add Equipment"). Only the card refreshes; the rest of the page stays put.

| Equipment Type | Count | What It Represents |
|---|---|---|
| separator | 4 | Production separators (oil/gas/water) |
| compressor | 3 | Gas compression trains |
| pump | 8 | Process and export pumps |
| exchanger | 6 | Heat exchangers |
| vessel | 4 | Pressure vessels |
| swivel | 1 | FPSO turret swivel |

> **What this does:** Builds a 52-dimensional equipment "fingerprint" vector,
> then finds the most similar projects in the pool using cosine similarity.
> Only the 17 process equipment types count — valves, instruments, etc. are
> zeroed out to prevent inflation by ancillary counts.

### Step 3 — Facility and capacity card

| Field | Value |
|---|---|
| Topsides Weight (tonnes) | **25000** |
| Water Depth (m) | **1800** |
| Hull Type | **FPSO newbuild** |

> **What this means:** 25,000 tonnes topsides is a large FPSO (Liza Unity class).
> 1,800m water depth puts us in the deepwater regime. The Calculator_Offshore
> model uses topsides weight as its primary cost driver.

### Step 4 — Subsea scope (SURF) card

The card appears only for offshore archetypes. Enter:

| Field | Value | What It Means |
|---|---|---|
| Subsea Trees | **12** | 12 subsea wells connected |
| Flowlines | **6** | 6 flowline segments |
| Risers | **4** | 4 steel catenary risers to FPSO |
| Manifolds | **2** | 2 subsea manifolds |
| Umbilicals | **3** | 3 control/power umbilicals |

> **Water depth** is inherited from the facility card (shown as a caption at the bottom).

### Step 5 — Click "Run Screening Estimate"

### What You Should See

**Model readiness:**
- Benchmark (analogues) **Ready**
- Offshore calculator **Ready**
- Equipment vector **Ready**
- SURF subsea (component) **Ready**

**Key Result Distinctions:**
- The **KPI cards** show the TEC ensemble (from Benchmark + Calculator_Offshore + EquipmentVector)
- **SURF** appears in the chart in the *Component* colour and in its own tab; it is an *additive* component (subsea scope only), not a total project TEC
- The ensemble does NOT include SURF in the P50 median — it's a breakout line item

> **Talking Point:** "For offshore, we get three independent TEC estimates plus
> a subsea breakout. The SURF estimate is bottom-up from equipment counts —
> calibrated against 4 Guyana deepwater projects. It's additive to TEC."

---

## Scenario 3: Pipeline (Quick Path)

> **Goal:** Show the pipeline-specific input fields and fast turnaround.

### Inputs

| Field | Value |
|---|---|
| Project Archetype | **Pipeline (Mainline)** |
| Location | **US Gulf Coast** |
| Basis Year | **2024** |
| Scope Type | **Greenfield** |
| Pipeline Length (km) | **200** |
| Pipeline Diameter (inches) | **24** |

Click **Run Screening Estimate**.

### What You Should See

- Pipeline calculator **Ready** and Benchmark **Ready** before you press Run
- After Run, a yellow **warning banner**: the pipeline calculator is flagged UNVERIFIED because pipeline truth values differ between sources (per the task brief). Say so out loud; it is a feature, not a bug.
- 🟢 **Benchmark** — analogue matching against pool pipelines
- P50 estimate in the ~$250–350M range for a 200km / 24" oil pipeline on the Gulf Coast

> **Talking Point:** "Pipeline estimates decompose into linepipe material,
> mainline construction, stations, crossings, and indirects. The bar chart
> detail panel shows this breakdown."

---

## Scenario 4: Refinery Brownfield Modification

> **Goal:** Show the brownfield/modification flow and the ARCHETYPE_EXCLUSIONS
> feature (Calculator_Onshore is pre-excluded for refinery_bf).

### Inputs

| Field | Value |
|---|---|
| Project Archetype | **Refinery Brownfield** |
| Location | **US Gulf Coast** |
| Scope Type | **Modification** |
| Facility Type | select **hydrotreater** |
| Primary Capacity | **40000** |
| Unit | **BPD** |

### What You Should See

- Benchmark (analogues) **Ready**
- Onshore calculator **Excluded for this archetype** (red badge, visible before Run)

> **What this means:** Calculator_Onshore is pre-excluded for refinery brownfield
> projects because the ISBL + TEC multiplier chain produced a 7.0× overshoot in
> testing. The Benchmark model handles brownfield refineries better by finding
> real analogues. This is an intentional safety exclusion.

---

## 5. Bid Validation (Post-Estimate Feature)

After running any scenario, scroll down in the results panel to the
**Bid check** card.

| Field | Value |
|---|---|
| Bid amount ($M) | Enter a number (e.g. **500**) |
| Bid type | **TEC** |
| Click | **Check bid** |

### Possible Verdicts

| Verdict | Color | Meaning |
|---|---|---|
| **WITHIN_RANGE** | Green | Bid falls within the P20–P80 ensemble range |
| **ABOVE_RANGE** | Yellow | Bid exceeds P80 — potentially overpriced |
| **BELOW_RANGE** | Red | Bid is below P20 — suspiciously low, risk of underbid |

> **Talking Point:** "This is designed for gate reviews — when a contractor
> submits a bid, the team can instantly sanity-check it against the screening
> model range."

---

## 6. What-If Sensitivity (Post-Estimate Feature)

After running any scenario, scroll to the **What-if** card.

1. **Parameter:** select a numeric input that was filled (e.g. Primary capacity)
2. **New value:** enter a different number (e.g. change 450 KTA to 600 KTA)
3. Click **Run what-if**

### What You Should See

- **3 delta metric cards:** Base P50, What-If P50, and the parameter change
- **Per-model comparison table:** shows each model's base vs. what-if estimate, with dollar and percentage deltas

> **Talking Point:** "This lets the team explore capacity trade-offs. What if we
> upsize from 450 KTA to 600 KTA? — the model shows the cost impact instantly,
> broken out by each independent model."

---

## 7. Exploring the Other Tabs

### Models page

- **Model specs:** one card per model with method, algorithm, reported accuracy and a status badge (best broad model, unverified, miscalibrated, component, automatic)
- **Routing and inputs:** which models each archetype can use and which are excluded, the input to model dependency table, and the ensemble rules in plain words
- **Reported accuracy:** per-archetype hit rate from the reference evaluation, clearly marked as not yet reproduced on this engine

### Data page

- Warning banner when the loaded package is the synthetic one, and the data directory in use
- **Loaded tables:** every CSV with live row and column counts and which model uses it
- **Preview** of any table and the analogue pool distribution by archetype

> **Talking Point:** "Full data provenance. Every table is traceable, every row
> count is live from the loaded CSVs."

> **Talking Point:** "Full transparency on how each model works, how it was
> tested, and where it's strong or weak."

---

## 8. Downloading the Report

At the bottom of the results panel, click **Download HTML report**.

This generates a standalone HTML file containing:
- Project scope summary
- Ensemble results (P50, range, confidence)
- All individual model estimates
- Analogues table
- Disclaimer

The file can be opened in any browser, emailed, or attached to a gate review package.

---

## Key Talking Points Summary

1. **10 independent models** — no single point of failure. The ensemble mediates.
2. **Progressive unlock** — start with 2 fields, get a Benchmark estimate. Add detail, unlock more models.
3. **Accuracy**: the reference evaluation reported **40/52 (77%)** within ±30% (Sep 16 brief). The engine's own number is produced by `scripts/evaluate_truth.py` on the real data package; do not quote a figure until that run has been done.
4. **No AI/LLM** — fully deterministic, reproducible, auditable.
5. **Sub-second response** — all computation is local, no API calls.
6. **Bid validation** — instant sanity check for contractor bids.
7. **What-if analysis** — explore capacity/location/scope trade-offs in real time.
8. **Full data provenance** — every table, every model, every correlation is documented in-app.

---

## Glossary of Terms (for non-technical audience)

| Term | Plain English |
|---|---|
| **TEC** | Total Erected Cost — the full installed cost of a facility, including equipment, materials, labor, and indirect costs |
| **ISBL** | Inside Battery Limits — the core process equipment cost before indirect multipliers |
| **OSBL** | Outside Battery Limits — utilities, infrastructure, and offsite costs (auto-calculated) |
| **EMMA** | Equipment, Materials, Methods, Approach — a location cost adjustment factor |
| **CP30** | Cost Performance 30 — an industry cost index for normalizing costs across locations and time periods |
| **P50** | The median estimate — 50% probability the actual cost is above, 50% below |
| **P20 / P80** | The 20th and 80th percentile of the cost range |
| **Six-tenths rule** | Engineering rule of thumb: cost scales as (capacity ratio)^0.6 |
| **LOOCV** | Leave-One-Out Cross-Validation — testing each project by hiding it and predicting from the rest |
| **Spread gate** | If models disagree by more than 3×, the outlier is removed from the ensemble |
| **Archetype** | Project category (e.g. offshore FPSO, pipeline, refinery brownfield) |
| **Screening** | Class 5 estimate (±50% accuracy target) — used for early-stage decision-making, not budgeting |
| **KTA** | Kilotonnes per annum |
| **BPD** | Barrels per day |
| **MTPA** | Million tonnes per annum |
| **SURF** | Subsea, Umbilicals, Risers, Flowlines — the subsea infrastructure for offshore projects |
