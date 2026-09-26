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
- **Header:** "GP Screening Cost Estimator" with a blue "POC v1.0" badge
- **5 tabs** across the top: Estimator · Data Package · Code Inventory · Dependencies · Model Specs
- The **Estimator** tab is active by default, with a left-side input panel and a right-side results area showing the "Progressive Unlock" table

---

## 1. Understanding the Layout (Estimator Tab)

The Estimator tab is split into two columns:

**Left Column — Input Panel (5 cards, top to bottom):**

| Card | What It Does |
|---|---|
| **1. Core Inputs** | Project archetype, location, basis year, scope type, project name. *Required* — nothing runs without archetype + location. |
| **2. Equipment List** | Add equipment items (type + count) for the EquipmentVector model. This is the best broad model (66% ±30% accuracy). |
| **3. Facility & Capacity** | Facility type, primary capacity, and units. Unlocks calculator models. Also shows pipeline / offshore / LNG-specific fields when those archetypes are selected. |
| **4. SURF Subsea Scope** | Only appears for offshore archetypes. Subsea trees, flowlines, risers, manifolds, umbilicals. Unlocks the SURF_User model. |
| **5. Scope Items (Composite)** | Multi-item scope builder for the Composite chip-matching model. |

**Right Column — Results Panel:**
- Before running: shows the "Progressive Unlock" guide
- After running: shows Model Readiness indicators, 3-Up Hero Cards (P50, Range, Confidence), bar chart, model details, analogues, bid validation, what-if sensitivity, and a downloadable HTML report

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

**Model Readiness Panel (right side, top):**
- 🟢 **Benchmark** — shows a dollar estimate (e.g. ~$600–800M)
- 🟢 **Calculator_Onshore** — shows a dollar estimate (e.g. ~$350–400M)
- 🟡 EquipmentVector **Needs:** equipment list
- 🟡 Composite — **Needs: at least 1 scope item**
- ⚪ Others — gray, showing what inputs they need

**3-Up Hero Cards:**

| Card | What It Shows | What It Means |
|---|---|---|
| **Best Estimate (P50)** | e.g. ~$500M | The median of surviving model estimates after spread gating. This is the single-number screening estimate. |
| **Range (P20-P80)** | e.g. $300M — $800M | The uncertainty band. P20 = "there's a 20% chance it's below this." P80 = "80% chance it's below this." |
| **Confidence** | MEDIUM or MEDIUM-HIGH | How many models agree. HIGH = 3+ models within ±30%. MEDIUM = 2 models, some disagreement. LOW = 1 model only. |

**Bar Chart:**
- Colored bars for each model that fired, with error bars showing each model's own range
- A dashed red horizontal line = the ensemble P50
- You can hover over bars to see exact values

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

### Step 2 — Equipment List (Card 2)

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

### Step 3 — Facility & Capacity (Card 3)

| Field | Value |
|---|---|
| Topsides Weight (tonnes) | **25000** |
| Water Depth (m) | **1800** |
| Hull Type | **FPSO newbuild** |

> **What this means:** 25,000 tonnes topsides is a large FPSO (Liza Unity class).
> 1,800m water depth puts us in the deepwater regime. The Calculator_Offshore
> model uses topsides weight as its primary cost driver.

### Step 4 — SURF Subsea Scope (Card 4)

Expand **"Define subsea scope for SURF estimate"** and enter:

| Field | Value | What It Means |
|---|---|---|
| Subsea Trees | **12** | 12 subsea wells connected |
| Flowlines | **6** | 6 flowline segments |
| Risers | **4** | 4 steel catenary risers to FPSO |
| Manifolds | **2** | 2 subsea manifolds |
| Umbilicals | **3** | 3 control/power umbilicals |

> **Water Depth** is inherited from Card 3 (shown as a metric at bottom of Card 4).

### Step 5 — Click "Run Screening Estimate"

### What You Should See

**Model Readiness:**
- 🟢 **Benchmark** — analogue estimate
- 🟢 **Calculator_Offshore** — topsides weight curve estimate
- 🟢 **EquipmentVector** — equipment fingerprint estimate
- 🟢 **SURF_User** — subsea component estimate (shown separately as a component)

**Key Result Distinctions:**
- The **3-Up Hero Cards** show the TEC ensemble (from Benchmark + Calculator_Offshore + EquipmentVector)
- **SURF_User** appears separately under "Component Estimates" — it's an *additive* component (subsea scope only), not a total project TEC
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

- 🟢 **Calculator_Pipeline** — rate × length estimate (includes mainline + linepipe + HDD crossings + stations + indirects)
- A yellow **warning banner**: the pipeline calculator is flagged UNVERIFIED because pipeline truth values differ between sources (per the task brief). Say so out loud; it is a feature, not a bug.
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

- 🟢 **Benchmark** — fires and produces an estimate
- ⚪ **Calculator_Onshore** — shows as "Excluded (known failure for refinery_bf)"

> **What this means:** Calculator_Onshore is pre-excluded for refinery brownfield
> projects because the ISBL + TEC multiplier chain produced a 7.0× overshoot in
> testing. The Benchmark model handles brownfield refineries better by finding
> real analogues. This is an intentional safety exclusion.

---

## 5. Bid Validation (Post-Estimate Feature)

After running any scenario, scroll down in the results panel to find
**"Bid / Quote Validation"**.

| Field | Value |
|---|---|
| Bid Amount ($M) | Enter a number (e.g. **500**) |
| Bid Type | **TEC** |
| Click | **Validate Bid** |

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

After running any scenario, scroll to **"What-If Sensitivity"**.

1. Expand "Run sensitivity scenario"
2. **Parameter to change:** select a numeric input that was filled (e.g. Primary Capacity)
3. **Alternate value:** enter a different number (e.g. change 450 KTA to 600 KTA)
4. Click **Run What-If**

### What You Should See

- **3 delta metric cards:** Base P50, What-If P50, and the parameter change
- **Per-model comparison table:** shows each model's base vs. what-if estimate, with dollar and percentage deltas

> **Talking Point:** "This lets the team explore capacity trade-offs. What if we
> upsize from 450 KTA to 600 KTA? — the model shows the cost impact instantly,
> broken out by each independent model."

---

## 7. Exploring the Other Tabs

### Tab 2: Data Package

- Shows the **Data Package Manifest** — all 10 CSV files loaded, with row counts, which models use them, and descriptions
- **Data Preview:** dropdown to inspect the first 50 rows of any table (useful for auditors who want to see the raw pool data)
- **Archetype distribution chart:** horizontal bar chart showing how many projects in the 503-project pool belong to each archetype

> **Talking Point:** "Full data provenance. Every table is traceable, every row
> count is live from the loaded CSVs."

### Tab 3: Code Inventory

- Lists all 16 reference Python modules with line counts, model mapping, and descriptions
- Shows excluded modules (LLM persona files, stale notebooks, deprecated orchestrators)

> **Talking Point:** "This POC reimplements 16 production Python modules as a
> single 2,857-line engine. The reference code is available for validation."

### Tab 4: Dependencies

- **Input → Model Dependency Graph:** which inputs each model requires vs. uses optionally
- **Progressive Unlock Sequence:** the 5-step path from minimal to maximum model coverage
- **Model Routing by Archetype:** which models are eligible for each of the 18 archetypes (from ARCHETYPE_MODELS)

### Tab 5: Model Specs

- **Expandable cards for each model with:** algorithm description, calibration method, LOOCV accuracy, libraries used
- **Accuracy Summary table:** per-archetype accuracy at ±30% tolerance with color-coded bar chart
- Shows the 77% overall accuracy threshold line

> **Talking Point:** "Full transparency on how each model works, how it was
> tested, and where it's strong or weak."

---

## 8. Downloading the Report

At the bottom of the results panel, click **"Download HTML Report"**.

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
