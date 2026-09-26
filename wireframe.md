# GP Screening Cost Estimator — UX Wireframe v1.0

This file is a Markdown transcription of the rendered `wireframe.html` screens. Visual styling and browser-only layout have been converted into structured text.

## Navigation

- Estimator
- Data Package
- Code Inventory
- Dependencies
- Model Specs

---

## 1. Estimator

### 1. Core Inputs (Required for ANY estimate)

| Field | Input |
|---|---|
| Project Archetype | Select… |
| Location (CP30 Region) | Select… |
| Basis Year | Select… |

### Model Readiness

| Model | Readiness / requirement |
|---|---|
| B — Benchmark (Analogue) | Needs archetype + location + year |
| B.1 — Composite (Chips) | Needs at least 1 scope item |
| A — Parametric (CET) | Needs facility/details |
| A.1 — Calculator Plus (ADR) | Needs ADR project |
| Bottom-Up (Equipment) | Needs equipment spec |

### Estimate Results

Results are shown in the right-side panel after enough inputs are provided.

### 2. Benchmark Inputs

> **Design change:** no user-entered cost input. Model B should produce the first estimate from **Archetype + Location + Basis Year** alone. **BF/GF is optional** and refines matching.

**Brownfield / Greenfield (Optional):**
- Optional

### Supporting Data

Fill core inputs to see the first benchmark estimate. Add scope items to build a composite estimate.

### 3. Composite Inputs

> **Design change:** build a project scope from scope items. Example: add a process unit, then an OSBL package, then a pipeline segment. Composite estimate sums all matched chip costs.

Example scope items shown in the wireframe include:

| Scope item | Example | Match result |
|---|---|---|
| Process Unit | Crude Unit | Matched chips |
| OSBL Utilities | Utilities Package | Matched 4 chips |
| Pipeline Segment | Export Pipeline | Matched 2 chips |

Action:
- **+ Add Scope Item**

### 4. Parametric / ADR Inputs

A dedicated section follows the composite inputs for the parametric / ADR-based model inputs.

---

## 2. Data Package

### Data Package Manifest

Verified reference data for the Streamlit app. Package as CSV/Parquet. Counts below need refresh from live tables before contractor handoff.

| Table | Rows | Models | Description | Refresh |
|---|---:|---|---|---|
| CET Rate CSVs (36 files) | 9,938 | A | Heritage parametric rate tables | Static |
| `ref_are_analogue_pool_v3` | 74 | B | Clean analogue corpus, CP30-normalized | Ad-hoc |
| `frankenstein` | 857 | B.1 | Chip library, 68 projects | Ad-hoc |
| `project_truth` | 47 | B, B.1 | Verified actuals + archetype labels | Ad-hoc |
| `gate_facilities` | 431 | A, B | Facility scope from gate packages | Ad-hoc |
| `gate_execution` | 404 | B | Execution strategy features | Ad-hoc |
| `ref_cp30_combined_indices` | 324 | ALL | CP30 escalation, 27 loc × 12 yr | Semi-annual |
| `ref_country_to_cp30_location` | 67 | ALL | Country to CP30 mapping | Rare |
| EMMA 4Q2025 factors | ~200 | A, BU | Location factors (AILR, material, FX) | Semi-annual |
| `ref_capacity_unit_harmonization` | 23 | B.1 | Unit conversion mappings | Rare |
| Overlay chain config | ~20 | A, A.1 | ISBL-to-TEC ratios. **MUST EXTRACT.** | Rare |
| ADR equipment ref | ~10K | A.1, BU | Equipment reference costs from ADR | Ad-hoc |
| Chip taxonomy | ~100 | B.1 | Dropdown options. **TO BE BUILT.** | Ad-hoc |
| DB_TO_TEC factors | 4 | A.1 | Gearing factors by archetype | Rare |

### PRE-BUILD TASKS (before contractor starts)

1. **Extract overlay chain config** — consolidate ratios from multiple `.py` files into one JSON.
2. **Build chip taxonomy** — query `frankenstein` for distinct `(archetype × scope_type × facility_type)`.
3. **Subset ADR equipment** — extract equipment-type costs from ~16M ADR line items.
4. **Snapshot all IC tables to CSV** — export flat files for contractor data package.

---

## 3. Code Inventory

### Production Python Modules (Reference Implementation)

Contractor uses these as **specification + validation reference**, not direct copy.

#### `computational/analogue_estimator.py`
Cosine similarity analogue matching, CP30 normalization, P20/P50/P80.

**Model B**

#### `computational/frankenstein_orchestrator.py`
Chip matching. Archetype filter, size-gate, magnitude-gate, IQR outlier removal.

**Model B.1**

#### `computational/generative_estimator.py`
`DB_TOTAL_COST` sum × archetype factor. Deterministic.

**Model A.1**

#### `computational/parametric_navigator.py` (`+offshore`, `+onshore`)
CET CSV rate-table lookup. Physical input → rate.

**Model A (3 variants)**

#### `computational/overlay_stack.py`
ISBL-to-TEC expansion. Shared. Ratios **MUST be extracted to config**.

**Shared**

#### `computational/tests/` (`289 + 50 + batches`)
Full regression suite. Contractor **MUST** pass these. Same inputs = same outputs.

**QA Gate**

### EXCLUDED (chatbot-only, not needed)

The wireframe explicitly excludes chatbot/persona-oriented artifacts from the contractor implementation, including skill/persona files such as `cost-buddy`, `cost-skeptic`, `cost-driver`, etc.

---

## 4. Dependencies

### Input to Model Dependency Graph

- **Required** = model cannot fire.
- **Optional** = improves accuracy.

| Input | Models / effect |
|---|---|
| Archetype | **ALL MODELS** |
| Location | **ALL (MAG normalization)** |
| Basis Year | **ALL (MAG normalization)** |
| BF / GF | B, B.1 — optional |
| Scope Items (multi-select) | **B.1** |
| Facility Type | **A**, B.1 optional |
| ADR Project | **A.1** |
| Equipment Spec | **Bottom Up** |

### Progressive Unlock Sequence

| Step | User action | Model unlocked | Class |
|---:|---|---|---|
| 1 | Archetype + Location + Year | **B (Benchmark)** | Class 5 |
| 2 | + Scope Items (multi-select) | **B.1 Composite** | Class 5 |
| 3 | + Facility Type + capacity | **A (Parametric)** | Class 4–5 |
| 4 | + ADR project | **A.1 Calc Plus** | Class 3–4 |
| 5 | + Equipment Spec | **Bottom Up** | Class 2 |

---

## 5. Model Specs

### B — Benchmark (Analogue)

| Attribute | Specification |
|---|---|
| Algorithm | Cosine similarity, CP30-normalized archetype matching |
| Output | P20/P50/P80 ($M TEC), top-N analogues |
| Pool | 74 projects (`pool_v3`) |
| LOOCV | 71.9% ±30% (N=32 LOOCV) |
| Libraries | sklearn, pandas, numpy |
| LLM | NO |

### B.1 — Composite (Chip Match)

| Attribute | Specification |
|---|---|
| Algorithm | Multi-item scope builder: add process unit + OSBL + pipeline etc.; each item matches chips independently, then summed |
| Output | Central/Low/High ($M), matched chips by scope item, summed total |
| Library | 857 chips, 68 projects |
| LOOCV | 26% ±30%, 48% ±50% (refinery_bf: 50% ±30%) |
| LLM | NO (semantic → category dropdown) |

### A — Parametric (CET Navigator)

| Attribute | Specification |
|---|---|
| Algorithm | Physical input → CET CSV lookup → rate × qty → overlay chain |
| Rate tables | 36 CET CSVs |
| Validation | Pipeline 1.18×, Offshore 1.09×, Onshore 1.10× / 0.82× |
| LLM | NO |

### A.1 — Calculator Plus (ADR)

| Attribute | Specification |
|---|---|
| Algorithm | Sum `DB_TOTAL_COST` × archetype gearing factor |
| Factors | `us_canada`: 24.0 (N=3), `china`: 15.2 (N=1), `uk`: 33.8 (N=1) |
| Constraint | Only projects with ADR data (IC3+) |
| LLM | NO |

---

## Notes

This wireframe reflects an earlier UX/specification state than the later September 15 README. Some counts and model names shown here (for example the 74-project analogue pool and A/B/B.1 labels) were subsequently superseded in the updated application documentation.
