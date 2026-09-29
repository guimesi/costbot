# GP Screening Cost Estimator - Application Documentation

> **Version:** POC v1.0
> **Last Updated:** September 2026
> **Accuracy:** reference evaluation (Sep 16 brief) reports 40/52 (77%) within ±30%.
> The engine's own accuracy has NOT been reproduced yet; run
> `scripts/evaluate_truth.py` against the real data package (see section 14).
> Bug fixes and open decisions since the first build: `REVIEW_2026-09-26.md`, `BACKLOG.md` (same folder).

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Data Sources](#3-data-sources)
4. [Estimation Models (10)](#4-estimation-models)
5. [Ensemble Logic](#5-ensemble-logic)
6. [Confidence Tiers](#6-confidence-tiers)
7. [Key Constants & Thresholds](#7-key-constants--thresholds)
8. [User Interface](#8-user-interface)
9. [Bid Validation](#9-bid-validation)
10. [What-If Sensitivity](#10-what-if-sensitivity)
11. [CP30 Escalation](#11-cp30-escalation)
12. [Archetype Routing](#12-archetype-routing)
13. [Archetype Exclusions](#13-archetype-exclusions)
14. [Testing & Validation](#14-testing--validation)
15. [File Inventory](#15-file-inventory)
16. [Known Limitations](#16-known-limitations)
17. [Glossary](#17-glossary)

---

## 1. Overview

The GP Screening Cost Estimator is a Streamlit web application that produces
Class 5 screening-level cost estimates for capital projects. It runs 10
deterministic estimation models against a scope description provided by the user
and combines their outputs into a single ensemble estimate with confidence
assessment.

**Design principles:**
- **No AI/LLM** — all models are deterministic (scaling correlations, cosine similarity, lookup tables)
- **No Spark / No database** — loads all data from local CSV files at startup
- **Sub-second response** — all computation is in-memory Python
- **Progressive unlock** — users start with 2 required fields (archetype + location) and unlock more models as they add detail
- **Transparent** — every model's estimate, analogues, and reasoning are visible in the UI

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ app.py (entry) + app_pages/{estimator,models,data}.py + ui/         │
│ • st.navigation (top): Estimator, Models, Data                      │
│ • Estimator builds the scope dict on every rerun, shows live         │
│   model_readiness(), calls screen_project() on Run, renders results │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    scope dict (Python dict)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ costbot/ package (engine.py is a compatibility facade)              │
│   constants.py data.py escalation.py models/*.py ensemble.py         │
│   screening.py report.py                                             │
│ screen_project(scope, data)                                         │
│   ├─ ARCHETYPE_MODELS routing → eligible models                     │
│   ├─ ARCHETYPE_EXCLUSIONS → pre-excluded models                     │
│   ├─ For each eligible model: run_<model>(scope, data)               │
│   ├─ CP30 basis-year escalation                                     │
│   ├─ _assess_confidence() → ensemble P50, range, tier               │
│   ├─ OSBL auto-fire (if Calculator_Onshore produced ISBL)           │
│   ├─ Screening floor check ($20M)                                   │
│   └─ Return structured results dict                                 │
│                                                                      │
│ DataStore (loads 10 CSVs at startup)                                │
│   .pool   .truth   .cp30   .frankenstein   .gate_costs              │
│   .equipment_vectors   .archetype_taxonomy   .scope_inputs          │
│   .semantic_chips      .country_to_cp30                             │
└──────────────────────────────────────────────────────────────────────┘
                              │
                    data/ (10 CSVs + 1 JSON)
```

**Deployment:** Databricks App via `app.yaml` (Streamlit on port 8000).
Set `COSTBOT_DATA_DIR=/path/to/real/data` to point the engine at the real
package; the repo's `data/` is a synthetic mock with the same schema.

**Dependencies:** `streamlit` (>= 1.52), `pandas`, `numpy`, `altair`, `scikit-learn` (for cosine similarity in Benchmark model).

---

## 3. Data Sources

All data lives in the `data/` folder. Loaded once at startup via `DataStore` (cached by Streamlit).

| File | Rows | Used By | Description |
|---|---|---|---|
| `ref_are_analogue_pool_v3.csv` | 503 | Benchmark, EquipmentVector | Analogue project pool. 26 columns including archetype, process_domain, scope_type,
facility_type, primary_capacity, capacity_unit, cp30_location, tec_musd_normalized_2024. |
| `project_truth.csv` | ~53 | Evaluation | Verified project actuals with archetype labels. Used for accuracy testing, not runtime estimation. |
| `frankenstein.csv` | ~857 | Composite | "Chip library" — cost breakdown elements from 68 projects. Each chip has a type, facility name, and costs. |
| `gate_costs.csv` | varies | Evaluation | Validated gate-level cost data. |
| `ref_equipment_vectors.csv` | ~593 | EquipmentVector | 52-dimensional equipment fingerprint vectors for pool projects. |
| `ref_archetype_taxonomy.csv` | 18 | All | Master archetype definitions and metadata. |
| `ref_project_scope_inputs_v2.csv` | varies | Calculators | Rich scope/capacity inputs for key projects (used in golden baseline testing). |
| `ref_semantic_chip_classifications.csv` | varies | Composite | AI-classified cost line items for chip matching. |
| `ref_cp30_combined_indices.csv` | varies | All | CP30 cost indices for 27 locations across multiple years. Used for location/time normalization. |
| `ref_country_to_cp30_location.csv` | varies | All | Maps country/location names to CP30 canonical location names. |
| `data/extracted_files/_golden_baseline.json` | 35 cases | Testing | Golden baseline expected values from reference calculators. |

---

## 4. Estimation Models

The engine runs up to 10 models per project. Each model is independent and
produces its own estimate. Not all models fire for every project — eligibility
depends on archetype and available inputs.

### 4.1 Calculator_Onshore

**Algorithm:** Six-tenths power-law scaling.

```
ISBL = base_cost × (user_capacity / reference_capacity) ^ 0.6
ISBL_at_location = ISBL × EMMA_factor
TEC = ISBL_at_location × TEC_multiplier
```

**Inputs required:** primary_capacity (+ capacity_unit). facility_type is optional: the UI offers a dropdown of every name the models understand (`FACILITY_TYPE_OPTIONS`) with an "Other" option; an unknown or empty name falls back to the generic process-plant correlation with a warning, as the reference does.
**TEC Multipliers:** GF 2.58×, BF-expansion 2.61×, BF-unit-mod 1.30×; any other scope-type string 2.58×. The API sends BF-expansion for every brownfield / expansion / modification scope; BF-unit-mod is forced when the facility name contains modification / conversion / debottleneck.
**ISBL Correlations:** 18 power-law tuples (base_cost_M, reference_capacity, exponent, unit), all back-solved from one or two truth projects (`CALIBRATION_STATUS` says which), plus one independent IC Library curve: a single crude distillation unit, linear in kB/SD, valid 50 to 500.
**Contingency:** none added. The multipliers were calibrated on TEC truth that already includes contingency (reference D.5 fix).
**EMMA Factor:** Location cost index relative to GOM 2000 baseline (202). Factor = local_index / 202.
**Note:** Pre-excluded for `refinery_bf` archetype (7.0× overshoot on brownfield refineries).

### 4.2 Calculator_Offshore

**Algorithm:** Topsides weight → cost curves + hull parametric.

- **Topsides:** weight-based cost curve ($/tonne varies by weight bracket)
- **Hull:** parametric by hull type (FPSO_newbuild, FPSO_converted, semi_sub, jacket_shallow)
- **Indirects:** ~40% of directs
- EMMA is set to 1.0 (intentionally removed — was causing ~1.88× inflation for locations like Guyana)

**Inputs required:** topsides_weight_te (or KBPD capacity for offshore_platform)
**Optional:** water_depth_m, hull_type

### 4.3 Calculator_Pipeline

**Algorithm:** Rate-per-km × length, with component breakdown.

- **Linepipe material:** diameter-based $/ft pricing
- **Mainline construction:** labor + equipment rate × length
- **Facilities:** MLV stations (auto-calculated every 25km), pump stations (auto-calculated for oil), pig launchers/receivers
- **HDD crossings:** rate × length × count
- **Indirects:** engineering + survey + contingency + escalation
- Location factor and congestion factor applied

**Inputs required:** length_km + od_inches (diameter)
**Optional:** service, congestion, grade, num_hdd_crossings, avg_hdd_length_m, num_pump_stations

### 4.4 Calculator_LNG

**Algorithm:** CET subsystem regressions × location rates.

42 subsystem regression equations scaled by LNG capacity (MTPA). Known to be miscalibrated for the POC — not relied upon.

**Inputs required:** lng_capacity_mtpa
**Warning:** LNG estimates carry high uncertainty. The Calculator_LNG model was ported from reference code but not recalibrated. Benchmark is the preferred model for LNG projects.

### 4.5 Benchmark (Analogue Estimator)

**Algorithm:** faithful port of `analogue_estimator.py` v3.0: one-hot categorical encoding + cosine similarity, optional size band from a user size bucket or explicit size (no capacity heuristic).

This is the most broadly applicable model. It works for any archetype with at least archetype + location.

**Process:**
1. **Encode user scope into a 6D feature vector:** process_domain (one-hot), scope_type (one-hot), facility_type match, location match, capacity proximity, CP30 location match
2. Encode every project in the 503-row pool the same way
3. Compute cosine similarity between user vector and each pool project
4. Also compute a size similarity signal from capacity (for grassroots/expansion only)
5. **Blend:** combined = 0.5 × cosine_similarity + 0.5 × size_similarity
6. Take top-N analogues, compute P20/P50/P80 from their TEC distribution

**LOOCV:** When the user's project is IN the pool (identified by name match), its own entry is excluded from the analogue set to prevent circular estimation. The pool TEC is used as a size signal instead.

**Libraries:** numpy, pandas, scikit-learn (StandardScaler, cosine_similarity)

### 4.6 EquipmentVector

**Algorithm:** 52-dimensional equipment composition vector + cosine similarity.

1. User provides an equipment list (type + count)
2. Build a 52-dimensional vector (one dimension per equipment type in the schema)
3. **Only process equipment types count (17 types:** pumps, exchangers, towers, etc.) — instruments, valves, etc. are zeroed to prevent ancillary count inflation
4. L2-normalize the vector
5. Compute cosine similarity against 593 pool equipment vectors
6. Top-5 weighted average produces the estimate

**Accuracy:** 66% ±30% on N=29 — the best broad model across diverse project types.

### 4.7 Unconventional

**Algorithm:** Facility-type median lookup from pool, with optional log-linear capacity interpolation.

Designed specifically for `onshore_unconventional` archetype (pads, compressor stations, gas plants, pipelines in unconventional plays).

**Process:**
1. Map facility_type to one of 6 canonical types via aliases (e.g. 'compressor_station' → 'cold_separation_train')
2. Look up median TEC from the 11 unconventional entries in the pool
3. If capacity is provided, interpolate using log-linear regression within the facility type

**Accuracy:** 70% ±30% on N=10. Authoritative for `onshore_unconventional` — the ensemble gives it priority over Benchmark.

### 4.8 Composite

**Algorithm:** Multi-item scope builder with chip matching.

1. User defines scope items (e.g. "process_unit: Crude Unit", "osbl: Utilities")
2. Each item is matched against the 857-chip frankenstein library using text similarity
3. Matched chips provide cost breakdowns
4. Costs are summed across all scope items with IQR filtering to remove outlier chips

**Accuracy:** 26% ±30% overall; 50% ±30% for refinery_bf. Best for multi-unit projects where scope decomposition is known.

### 4.9 SURF_User

**Algorithm:** Subsea equipment bottom-up pricing.

- **Subsea trees:** heritage pricing × count
- **Flowlines:** length-based cost
- **Risers:** depth-adjusted cost
- **Manifolds:** unit cost
- **Umbilicals:** length-based cost
- **Calibration factor:** 1.34 (fitted against 4 Guyana deepwater projects)

**Note:** SURF is a **component model** — it estimates only the subsea portion, not total project TEC. It is NOT included in the ensemble P50 median. It appears as a separate line item.

**Inputs required:** surf_scope with subsea_trees, flowlines, risers (at least one)
**Accuracy:** 4/4 within ±30% on Guyana deepwater validation set.

### 4.10 OSBL_Estimate

**Algorithm:** 3-layer indirect cost overlay applied to ISBL.

- **Layer 1:** Heritage percentage (archetype-based OSBL/ISBL ratio)
- **Layer 2:** IC Library parametric (power, steam, storage, loading subcurves)
- **Layer 3:** Absolute cost chain (fixed infrastructure items)

Auto-fires whenever Calculator_Onshore produces an ISBL value. Not a TEC model — provides the OSBL breakout.

---

## 5. Ensemble Logic

The ensemble is computed by `_assess_confidence()` in engine.py. It mediates
between all TEC models that fired (excluding component models like SURF and OSBL).

### Step 1: Collect Estimates
Gather `estimate_musd` from all models where `can_fire=True` and `excluded_by_rule=False`.

### Step 2: Spread Gate
Iteratively check if the max/min ratio exceeds `SPREAD_GATE_RATIO` (3.0×).
If it does, remove the lowest-priority model that is furthest from the median.

**Priority hierarchy:**
| Priority | Models | Rationale |
|---|---|---|
| 5 | Unconventional (when archetype=onshore_unconventional) | Purpose-built for this archetype |
| 3 | Calculator_Onshore, Calculator_Offshore, Calculator_Pipeline, Calculator_LNG | Physics/capacity-driven |
| 2 | Unconventional (other archetypes) | Lookup-based |
| 1 | Benchmark, EquipmentVector, Composite | Statistical/analogue-based |

### Step 3: Unconventional Override
For `onshore_unconventional` archetype, if the Unconventional model survived the spread gate, use it directly as P50 (ignore other models).

### Step 4: Geometric Mean Blend
When exactly 2 models survive (Calculator_Onshore + Benchmark) and they disagree by >1.5×, use geometric mean instead of arithmetic median. This prevents the larger model from dominating the P50.

```
geometric_mean = sqrt(estimate_A × estimate_B)
```

### Step 5: Compute P50, Range, Confidence
- **P50** = median of surviving estimates
- **Range** = min of model lows to max of model highs (capped at 5× ratio)
- **Confidence tier** = based on model count and agreement (see Section 6)

---

## 6. Confidence Tiers

| Tier | Criteria | Meaning |
|---|---|---|
| **HIGH** | 3+ models, 3+ agree within ±30% | Strong consensus across multiple independent methods |
| **MEDIUM-HIGH** | 2+ models, 2+ agree within ±30% | Good agreement between two models |
| **MEDIUM** | 2+ models, spread >30% between them; or Unconventional override | Models disagree but both informative |
| **LOW** | 1 model survives after spread gate removed others | Single-source estimate, treat with caution |
| **CANNOT_ESTIMATE** | 0 models fired or no usable estimates | Insufficient inputs to produce any estimate |
| **COMPONENT_ONLY** | No TEC models, but component models (SURF) fired | Only subsea/component breakout available |

---

## 7. Key Constants & Thresholds

| Constant | Value | Location | Purpose |
|---|---|---|---|
| `SPREAD_GATE_RATIO` | 3.0 | engine.py | Max allowed ratio between highest and lowest surviving model estimates |
| `SCREENING_FLOOR_MUSD` | 20.0 | engine.py | Projects below $20M trigger a floor warning (not screening candidates) |
| `_POOL_BASE_YEAR` | 2024 | engine.py | All pool TEC values are normalized to 2024 USD |
| `_CP30_REF_LOCATION` | Texas-BTN (GOM) | engine.py | GOM is the base location for CP30 indices |
| TEC_MULT (greenfield) | 2.58 | engine.py | ISBL → TEC multiplier for greenfield projects |
| TEC_MULT (brownfield) | 1.30 | engine.py | Defined, but plain "brownfield" scope currently uses the expansion multiplier 2.61 on purpose; 1.30 applies to "modification" only. Open decision, see BACKLOG. |
| TEC_MULT (expansion) | 2.61 | engine.py | ISBL → TEC for expansion projects |
| Benchmark blend | 0.5 / 0.5 | engine.py | Cosine similarity weight vs. size similarity weight |
| Geometric mean threshold | 1.5× | engine.py | Triggers geometric mean when Calc_Onshore and Benchmark disagree |
| Range cap | 5.0× | engine.py | P80/P20 ratio capped at 5× (symmetric in log-space) |
| EMMA (offshore) | 1.0 | engine.py | EMMA intentionally disabled for offshore (was causing 1.88× inflation) |

---

## 8. User Interface

Three pages in a top navigation bar. Theme is `.streamlit/config.toml` (light,
navy primary, Inter); no CSS or HTML is injected. Every element is native
Streamlit: bordered containers as cards, `st.metric(border=True)` KPI cards,
inline badges, Material icons, sentence-case labels.

### Estimator page
- **Left column, input cards:** Project (archetype, location, basis year and
  scope type as button groups, project name, optional process domain),
  Equipment list (fragment; duplicate types merge), Facility and capacity
  (facility type is a dropdown the user can also type into; pipeline, offshore
  and LNG fields appear per archetype), Subsea scope (offshore only), Scope
  items (fragment), and the **Run screening estimate** button.
- **Right column:** **Model readiness** is computed on every rerun by
  `costbot.screening.model_readiness()` without running any model, so the user
  sees Ready / Needs … / Excluded per eligible model while typing. After Run:
  KPI row (P50, range, confidence), warnings (screening floor, model warnings,
  CP30 note), the **Model estimates** Altair chart (bars, range whiskers,
  ensemble P50 rule, colour by role), one tab per fired model with its detail
  table and analogues, **Comparable projects**, **Bid check**, **What-if** and
  **Download HTML report**. Changing an input after a Run shows a stale notice.

### Models page
Tabs: Model specs (one card per model with badges), Routing and inputs
(archetype routing and exclusions from the engine tables, dependency table,
ensemble rules), Reported accuracy (reference figures, marked unverified).

### Data page
Mock-package warning and data directory, loaded tables with live counts and
usage, table preview, analogue pool by archetype.

---

## 9. Bid Validation

Available after running an estimate. The user enters a contractor bid amount and type (TEC or EPC lump-sum). The system compares it against the ensemble range:

| Verdict | Condition | Action |
|---|---|---|
| **WITHIN_RANGE** | P20 ≤ bid ≤ P80 | Bid is consistent with screening estimate |
| **ABOVE_RANGE** | bid > P80 | Bid may be overpriced — investigate scope differences |
| **BELOW_RANGE** | bid < P20 | Bid is suspiciously low — risk of underbid or missing scope |

---

## 10. What-If Sensitivity

Available after running an estimate. The user selects a numeric parameter (capacity, pipeline length, diameter, topsides weight, water depth, LNG capacity), enters an alternate value, and re-runs all models with that change.

Output:
- Base vs. What-If P50 delta (dollars and percentage)
- Per-model comparison table with individual model deltas

---

## 11. CP30 Escalation

All pool-based estimates (Benchmark, EquipmentVector, Unconventional, Composite) are generated in `_POOL_BASE_YEAR` (2024) USD. If the user selects a different basis year, the engine applies a CP30 escalation factor:

```
escalation_factor = CP30_index(target_year, GOM) / CP30_index(2024, GOM)
```

This adjusts for cost inflation/deflation between years. The factor is displayed in the results as a basis-year note.
For a target year beyond the last year in the CP30 table, the factor is extrapolated with the last observed annual growth (e.g. 2026 from 2024→2025). Calculator models are not CP30-escalated; their rate tables carry their own basis.

---

## 12. Archetype Routing

Each archetype maps to a specific set of eligible models via `ARCHETYPE_MODELS`:

| Archetype | Eligible Models |
|---|---|
| offshore_fpso, offshore_platform | Calculator_Offshore, Benchmark, SURF_User |
| lng_onshore, lng_offshore, lng_terminal | Calculator_LNG, Benchmark |
| onshore_petchem, integrated_petchem | Calculator_Onshore, Benchmark |
| refinery_gf, refinery_bf | Calculator_Onshore, Benchmark |
| onshore_unconventional | Calculator_Onshore, Unconventional, Benchmark |
| pipeline_mainline, pipeline_gathering, pipeline_complex | Calculator_Pipeline, Benchmark |
| ccs, ccs_gas_processing | Calculator_Onshore, Benchmark |
| oil_sands, onshore_conventional | Calculator_Onshore, Benchmark |
| renewable_diesel, gas_processing, power_generation | Calculator_Onshore, Benchmark |

**Dynamic additions:** EquipmentVector is added if the user provides an equipment list, SURF_User is added if SURF scope is provided, Composite is added if scope items are provided.
OSBL_Estimate auto-fires when Calculator_Onshore produces an ISBL.

---

## 13. Archetype Exclusions

Some archetype + model combinations are pre-excluded based on testing:

| Archetype | Excluded Model | Reason |
|---|---|---|
| offshore_fpso | Benchmark | ratio 0.058, returns pool median for mega-projects |
| refinery_bf | Calculator_Onshore | 7.0× overshoot on brownfield refinery projects |
| onshore_unconventional | Benchmark | anchored on the wrong pool segment |
| lng_onshore | Benchmark | pool median meaningless for multi-billion LNG |

Verbatim from `cost_bot_api.py`. The first build had re-enabled three of these;
the real-data run of 2026-09-28 showed Benchmark alone under-estimating FPSO and
LNG projects by 60 to 98%, so the reference rules were restored (2026-09-29).

---

## 14. Testing & Validation

### 14.1 Accuracy against `project_truth.csv`

The first build reported 42/50 (84%) at ±30%, but no script that produces
that number survived, so it is treated as unverified. `scripts/evaluate_truth.py`
now runs every truth row through `screen_project()` in LOOCV mode (the
project's own pool entry is excluded by planview_id) and prints hit rate per
archetype for the ensemble P50 and for the best single model. Run it in the
production environment:

```bash
COSTBOT_DATA_DIR=/path/to/real/data python scripts/evaluate_truth.py --csv results.csv
```

Reference point from the Sep 16 brief: 40/52 (77%). On the mock package the
script's output is meaningless.

**Per-archetype breakdown claimed by the first build (unverified):**
- Chemicals: 4/4 (100%)
- CCS: 2/2 (100%)
- Deepwater: 3/3 (100%)
- Unconventional: 10/11 (91%)
- Refinery BF: ~76%
- Pipeline: 40% (structural gaps)
- LNG: 0% (calculator miscalibrated)

### 14.2 Golden Baseline Regression Tests

`tests/test_golden_baseline.py` — tests each calculator in isolation against expected values from `_golden_baseline.json`.

The JSON in this repo is a MOCK snapshot of the engine's own output (14 cases, 13 PASS + 1 SKIP by construction); it guards against regressions, not against the reference. Against the REAL golden file the first build reported:

| Status | Count | Details |
|---|---|---|
| PASS | 23 | Within ±10% of golden expected |
| XFAIL (expected failure) | 12 | Documented intentional divergences |
| FAIL | 0 | No unexpected failures |
| SKIP | 6 | ic_library (no engine model) + pipeline_complex (no golden key) |

**XFAIL categories:**
- 3 offshore: EMMA intentionally removed (golden includes EMMA ~1.88×)
- 3 pipeline: Golden values from older calculator version (reference v2 itself fails them)
- 2 LNG: Calculator regression equations differ from reference
- 4 onshore (Joliet/BRACE): EMMA location mapping + BF-unit-mod scope chain differences

### 14.3 Other test layers

| Script | What it checks |
|---|---|
| `tests/test_ensemble.py` (pytest) | Ensemble rules independent of data: spread gate, geometric blend, unconventional override, 5x cap, bid validation, CP30 escalation and extrapolation, equipment vector, location resolution, screening floor, COMPONENT_ONLY. |
| `scripts/smoke_test.py` | 6 end-to-end scenarios through `screen_project()`; asserts which models fire and that no model died on a swallowed exception. |
| `scripts/ui_test.py` | Headless Streamlit `AppTest`: fills scenario 1, adds/removes equipment and scope items, clicks Run, checks results and that no error element rendered. |

### 14.4 8 Remaining Accuracy Failures reported by the first build (unverified)

| # | Project | Best Error | Root Cause |
|---|---|---|---|
| 1 | Cowboy Gas CDP | +36% | Pool TEC itself 19% above truth |
| 2 | PIT BMT3 | -39% | Pipeline complex — needs more than mainline calc |
| 3 | PNG LNG | -50% | Too few $16B-scale peers in pool |
| 4 | BR Naphtha Debottleneck | +55% | Pool TEC 52% above truth |
| 5 | Cowboy Pad Pre-Investment | +55% | $6M project — noise floor |
| 6 | Singapore SLXP | +70% | Pool TEC 58% above truth |
| 7 | USGC Reconfig Baytown | -90% | Not in pool, no size signal, $1.26B truth |
| 8 | Golden Pass Terminal | +274% | Liquefaction calc on regasification terminal |

---

## 15. File Inventory

```
costbot/
├── README.md               # Repo readme: what it is, run, test, layout
├── CLAUDE.md               # Conventions for working in the repo
├── Makefile                # install / test / run / mock / screenshots / evaluate
├── app.py                  # Streamlit entry point (st.navigation, top)
├── .streamlit/config.toml  # Theme (light, navy accent). No CSS in code.
├── app_pages/              # estimator.py, models.py, data.py
├── ui/                     # common.py, cards.py (fragment cards), results.py (results panel)
├── costbot/                # Engine package
│   ├── constants.py        # routing, exclusions, correlations, location maps, UI option lists
│   ├── labels.py           # labels, model specs, ensemble rules, colours (UI + report)
│   ├── data.py             # DataStore (COSTBOT_DATA_DIR aware)
│   ├── escalation.py       # CP30 + EMMA
│   ├── models/             # one file per model runner
│   ├── ensemble.py         # _assess_confidence
│   ├── screening.py        # screen_project, model_readiness, model_rows, analogues, validate_bid
│   └── report.py           # HTML report
├── engine.py               # Facade re-exporting costbot.* (kept for compatibility)
├── app.yaml                # Databricks App config (streamlit on port 8000)
├── requirements.txt        # Runtime dependencies
├── requirements-dev.txt    # pytest, pyflakes, playwright
├── docs/
│   ├── spec/               # task_brief_2026-09-15.md (the spec), requirement_update_2026-09-16.md, wireframe_v1.md
│   ├── APP_DOCUMENTATION.md  # This file
│   ├── DEMO_SCRIPT.md        # Live demo walkthrough
│   ├── REVIEW_2026-09-26.md  # Spec vs implementation review, bugs fixed
│   └── BACKLOG.md            # Open decisions and next work
├── scripts/
│   ├── generate_mock_data.py # Writes the synthetic data/ package
│   ├── smoke_test.py         # Engine end-to-end scenarios
│   ├── ui_test.py            # Headless Streamlit test
│   ├── screenshot.py         # Playwright screenshots of the app
│   └── evaluate_truth.py     # Accuracy vs project_truth.csv
├── tests/
│   ├── test_ensemble.py      # Ensemble, CP30, bid, equipment vector
│   ├── test_readiness.py     # model_readiness vs screen_project
│   ├── test_report.py        # HTML report
│   └── test_golden_baseline.py  # Calculators vs golden JSON (script + pytest)
└── data/                   # MOCK package (see data/README.md), incl. extracted_files/_golden_baseline.json
```

---

## 16. Known Limitations

1. **LNG Calculator is miscalibrated.** Regression equations from reference code were ported without recalibration. Use Benchmark for LNG projects.
2. **Pipeline Complex is unsupported.** Only mainline pipeline estimation is implemented. Complex pipelines (multi-diameter, multi-segment, facilities-heavy) are not modeled.
3. **EMMA is disabled for offshore.** The EMMA location factor was causing systematic 1.88× inflation for deepwater projects. Set to 1.0 pending investigation.
4. **Composite model has low accuracy (26% ±30%).** Chip matching depends on having similar projects in the frankenstein library. Works best for refinery brownfield.
5. **Pool data quality drives Benchmark accuracy.** Three accuracy failures (BR Naphtha, SLXP, Cowboy CDP) are caused by the pool TEC being 19–58% above truth.
6. **No user authentication / role-based access.** POC-level — anyone with workspace access can use the app.
7. **No persistent storage.** Estimates are in-session only (Streamlit session state). Download the HTML report to preserve results.
8. **Screening floor at $20M.** Projects below $20M are flagged as not screening candidates — estimates at this scale carry disproportionate uncertainty.
9. **Reference parity is unverified.** `cost_bot_api.py` (the spec's source of truth) is not available here, so "identical outputs for identical inputs" has never been checked. Six modelling choices deviate from the README on purpose; see `docs/BACKLOG.md`.
10. **Pipeline calculator is unverified** (truth values disagree between sources); the UI shows a warning banner.

---

## 17. Glossary

| Term | Definition |
|---|---|
| **Archetype** | Project category defining which models are eligible (e.g. offshore_fpso, refinery_bf, pipeline_mainline) |
| **BPD** | Barrels per day |
| **Chip** | A cost breakdown element from a real project, stored in the frankenstein library |
| **CP30** | Cost Performance 30 — industry index for normalizing costs across locations and time |
| **EMMA** | Equipment, Materials, Methods, Approach — location cost adjustment factor relative to GOM |
| **Ensemble** | The combined result from all surviving models after spread gating |
| **GOM** | Gulf of Mexico — the reference location for cost normalization |
| **ISBL** | Inside Battery Limits — core process equipment cost before indirect multipliers |
| **KTA** | Kilotonnes per annum |
| **LOOCV** | Leave-One-Out Cross-Validation — accuracy testing by hiding each project and predicting from the rest |
| **MTPA** | Million tonnes per annum |
| **OSBL** | Outside Battery Limits — utilities, infrastructure, and offsite costs |
| **P20 / P50 / P80** | 20th / 50th / 80th percentile cost estimates, P50 is the median (best estimate). |
| **Pool** | 503-project analogue corpus used by Benchmark and EquipmentVector |
| **Scope Type** | Greenfield / Brownfield / Expansion / Modification — determines TEC multiplier |
| **Six-tenths Rule** | Engineering scaling law: cost ∝ (capacity ratio)^0.6 |
| **Spread Gate** | If models disagree by >3×, the lowest-priority outlier is removed |
| **SURF** | Subsea, Umbilicals, Risers, Flowlines — subsea infrastructure for offshore projects |
| **TEC** | Total Erected Cost — full installed cost including equipment, materials, labor, and indirects |
| **XFAIL** | Expected failure in tests — a documented intentional divergence from reference values |
