# GP Screening Cost Estimator — Streamlit POC

Updated task brief (Sep 15, 2026). Supersedes Aug 30 version; significant data and architecture changes.

> **WARNING:** The August 30 task brief and zip package are OBSOLETE. Data sizes (74→503 pool, 47→53 truth), model names, code architecture, and UX flow have all changed. Do NOT build from the old zip.

## What Changed Since Aug 30

| Item | Aug 30 | Current (Sep 15) |
|---|---|---|
| Analogue pool | 74 rows | **503 rows** (100% fill on all key fields) |
| Truth projects | 47 rows | **53 rows** (52 distinct projects) |
| Models | 5 lettered (A, A1, B, B1, Bottom-Up) | **9 callable runners** with canonical names |
| Architecture | 5 separate Python files per model | **cost_bot_api.py** (112KB) wraps everything |
| Best broad model | Benchmark (Model B) | **EquipmentVector** (66% ±30%) |
| OSBL estimation | Not built | **CalcPlus OSBL v1.3** (40KB, 8% avg error) |
| SURF subsea | Not built | **SURF CalcPlus v2** (4/4 LOOCV) |
| Production arch. | TBD (3 options) | **Deterministic only. No AI / LLM in estimation** |

## The Task

Build a standalone Streamlit app that runs **9 deterministic cost estimation models**. User fills in project details via dropdowns, models progressively light up as inputs are provided, results show as cost ranges with reference projects visible. No LLM, no database connections, no Databricks dependency. Everything runs from flat files.

## The 9 Models

| Model | What it uses | Minimum inputs | Accuracy |
|---|---|---|---|
| Calculator_Onshore | Six-tenths scaling correlations for 18 facility types from heritage CET workbooks | Process domain + facility type + capacity + location | 79% ±30% (N=14) |
| Calculator_Offshore | Topsides weight curves + hull parametric + engineering % from offshore CET | KBPD + water depth + topsides weight | 50% ±30% (N=2) |
| Calculator_LNG | 42 CET equations for LNG plant subsystems | LNG capacity (MTPA) + location | 0% (miscalibrated). Not November scope. |
| Calculator_Pipeline | Pipeline parametric from CET | Diameter + length + terrain + location | 67% ±30% (N=3). **UNVERIFIED.** Pipeline c/s truth values differ from project_truth (see MEASUREMENTS_LOG). With Garonita truth: 1/3 ±30%. |
| Benchmark | Cosine similarity on project features against 503-entry pool | Archetype + location + year + size + BF/GF | 70% ±30% (regression under investigation) |
| EquipmentVector **BEST BROAD** | 52-dimension cosine similarity on equipment composition. Top 5 weighted, size-gated. | Equipment list (type + count) + archetype | **66% ±30% (N=29)** |
| Unconventional | Facility-type lookup for short-cycle unconventional projects | Facility type (CS train, CDP, pipeline, etc.) | 70% ±30% (N=10) |
| SURF_User **NEW** | Subsea equipment bottom-up: flowlines, risers, umbilicals, trees, installation | Well count + water depth + topsides weight | 4/4 LOOCV ±30% |
| OSBL_Estimate **NEW** | 3-layer indirect cost overlay: heritage flat + IC Library parametric + IC Absolute cost chain | Process domain + scope type + capacity + location | 8% avg error (N=4) |

## Reference Spec: `cost_bot_api.py`

The **single source of truth** for model behavior is `cost_bot_api.py` (112KB, 17 methods). The Streamlit app should produce identical outputs for identical inputs.

| Method | What it returns |
|---|---|
| `screen_project(params)` | Runs all eligible models, returns ensemble range with per-model detail |
| `get_analogues(params)` | Returns top-N similar projects from the 503-entry pool |
| `run_calculator_onshore(params)` | Single-model run: Onshore parametric |
| `run_equipment_vector(params)` | Single-model run: Equipment similarity |
| `run_surf_user(params)` | Single-model run: SURF subsea bottom-up |
| `run_osbl_estimate(params)` | Single-model run: OSBL indirect cost overlay |

> **Ensemble range logic:** `cost_bot_api` applies a 5x cap on the range (high/low ≤ 5x). When SURF fires but no TEC models fire, confidence tier = **COMPONENT_ONLY** (subsea cost available but no total project cost).

## Data Files (Updated)

| File | Rows | What it is |
|---|---:|---|
| `ref_are_analogue_pool_v3.csv` | **503** | Completed projects with normalized costs, full 2D taxonomy (process_domain × scope_type), capacity, equipment counts. All fields 100% filled. |
| `frankenstein.csv` | 857 | Sub-project cost chips. 57 projects. Used by Composite models. |
| `project_truth.csv` | **53** | Verified actual costs + 2D archetype. 52 distinct projects. |
| `ref_equipment_vectors.csv` | **593** | 52-dimension equipment composition vectors. Used by EquipmentVector. |
| `gate_costs.csv` | 1,687 | Gate package cost breakdowns (scope chip, cost type, indirect). 58 projects. |
| `ref_archetype_taxonomy.csv` | 17 | Canonical 2D taxonomy definition (process_domain × scope_type). |
| `ref_cp30_combined_indices.csv` | 324 | CP30 location + time escalation factors. |
| `ref_country_to_cp30_location.csv` | 67 | Maps country names to CP30 location codes. |
| `_golden_baseline.json` | — | Calculator family configuration (routing, subsystem definitions). |
| `ic_library_osbl_subcurves.json` **NEW** | — | IC Library OSBL sub-curve parameters for CalcPlus OSBL. |

## UX Pattern: Progressive Disclosure (Updated)

| Step | User fills | What lights up |
|---|---|---|
| 1 | Process domain + scope type + location + year | **Benchmark** (if size provided) |
| 2 | + Equipment list (type + count) | **EquipmentVector** (best broad model) |
| 3 | + Capacity / size estimate | **Calculator_Onshore** or **Calculator_Offshore** (by routing) |
| 4 | + Water depth + topsides weight | **SURF_User** (offshore only) |
| 5 | + Facility type (unconventional) | **Unconventional** lookup |
| Always | (runs automatically when any model fires) | **OSBL_Estimate** (indirect cost overlay) |

> **Key UX insight (David directive):** For brownfield refinery/modification work, the scope IS the equipment list. Cost Bot must always ask: “What major equipment is involved? Pumps, exchangers, towers, drums, compressors — even rough counts help.” This unlocks EquipmentVector, the best broad model.

## Key Behavioral Rules

- **Screening floor: $20M.** Projects below $20M are not screening candidates. Tell the user honestly.
- **Per-archetype exclusions:** `refinery_bf` excludes `Calculator_Onshore` (7.0x overshoot); `offshore_fpso` excludes `Benchmark` (0.58 ratio); `onshore_unconventional` excludes `Benchmark`.
- **Process only vector matching:** When matching equipment lists, zero out valve/instrument/panel/meter/switchgear/transformer dimensions before L2 normalization. Signal = process equipment only.
- **Ensemble range cap:** 5x maximum spread (high/low). Wider ranges get capped with a `range_capped` flag.
- **COMPONENT_ONLY confidence:** When SURF fires but no TEC models fire, the result is a subsea component cost, not a total project estimate.

## What's NOT in the Streamlit POC

- No LLM / AI calls; estimation is deterministic.
- No database connection (all data is CSV/JSON files).
- No Databricks dependency.
- No user-entered cost input (models estimate cost FROM scope parameters).
- No engagement logging (this is a POC app only).

---

Prepared from updated September 15 task brief. Source: `cost_bot_api.py` (112KB) + live POC files.
