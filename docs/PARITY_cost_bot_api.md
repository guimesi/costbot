# Parity check: engine vs `cost_bot_api.py` (reference, v1.0.0 2026-09-10)

Compared on 2026-09-29 by reading the reference file line by line against
`costbot/`. "Aligned" means the engine now does what the API does; "engine
superset" means the engine does more but the API behaviour is preserved;
"pending" needs another reference file to settle.

## Routing, exclusions, ensemble (the open decisions)

| Topic | API | Engine before | Now |
|---|---|---|---|
| Archetype exclusions | `offshore_fpso` Benchmark, `refinery_bf` Calculator_Onshore, `onshore_unconventional` Benchmark, `lng_onshore` Benchmark | only refinery_bf | **Aligned** (verbatim). Real-data run backed it: Benchmark alone under-estimated FPSO/LNG by 60 to 98%. |
| Model set | 8 runners + OSBL overlay = 9 | 10 (Composite added from the wireframe) | Composite kept, labelled "not in the API"; never routed by archetype, only when scope items are given. |
| OSBL trigger | ISBL from Calculator_Onshore or `scope['isbl_musd']` | same | **Already aligned**. The README's "runs whenever any model fires" is not what the API does. |
| Ensemble spread gate | remove the model furthest from the median until spread <= 3x, no priorities | priority-aware (calculators outrank analogue models) | **Aligned** (`mode='api'` default). First-build rules kept as `ensemble_mode='engine'` for evaluation. |
| Unconventional override, geometric blend | none | both | Off by default (engine mode only). |
| 5x range cap | clamp each bound to [median/5, median*5] | high/low <= 5 symmetric around the median | **Aligned**. Note: the API's rule allows a 25x span; the brief's text ("high/low <= 5x") describes the engine's old rule. Worth one line with David. |
| Confidence tiers | HIGH / MEDIUM-HIGH / MEDIUM / LOW / CANNOT_ESTIMATE / COMPONENT_ONLY | same | Aligned. |
| Screening floor | note only when the user gives `project_scale_musd` < $20M | also post-hoc on the ensemble P50 | Engine superset (the post-hoc note stays; it is informational). |
| Archetypes routed | 14 (no lng_terminal, pipeline_complex, ccs_gas_processing, onshore_conventional, renewable_diesel, gas_processing: those fall to the default Calculator_Onshore + Benchmark) | 20 | Engine superset; the six extra route the same as the API default except `lng_terminal` (LNG calculator) and `pipeline_complex` (pipeline calculator). |

## Model runners

| Model | API behaviour | Now |
|---|---|---|
| Calculator_Onshore | facility_type defaults to `process_plant_generic`; scope type is `BF-expansion` for any brownfield / expansion / modification / debottleneck, else `GF`; `FACILITY_TYPE_CORRELATION_MAP`; range +/-50% | **Aligned**: default facility, API scope-type rule (calculator callers can still pass `calculator_scope_type` verbatim, the golden tests do), map entries added, range +/-50%. The 1.30x "modification" chain is therefore reached only by a direct calculator call, never through the API path. Multiplier values themselves: pending `onshore_calculator.py`. |
| Calculator_Pipeline | OD and options from `secondary_params`; length from `primary_capacity` in miles (default) or km; defaults service NGL, grade X65, congestion rural, HDD 500 m; range -30%/+50% | **Aligned** on inputs, defaults and range. Rates and the congestion table: pending `pipeline_calculator_v2.py`. |
| Calculator_LNG | capacity from `primary_capacity`, trains = round(MTPA/5); range -30%/+50% | **Aligned** on range (was +100%). Equations: pending `lng_calculator.py`. |
| Calculator_Offshore | topsides from `secondary_params` or derived from KBPD with hull by archetype (platform = semi_sub); range -30%/+50% | **Aligned**. Steps: pending `offshore_calculator.py`. |
| Benchmark | features: archetype, process_domain, scope_type, bf_gf, onshore/offshore, fac_type, capacity + unit, region (Guyana counts as North America); `exclude_planview_ids=[]` for new projects | Feature set similar; region vocabulary and everything inside `AnalogueEstimator` (size band, thresholds, pool filters): **pending `analogue_estimator.py`**. This is where the accuracy gap lives. |
| Unconventional | facility peers (alias map, then LIKE on the first token); capacity-aware 2-point interpolation within same-unit-family peers, nearest peer outside the range, unscaled median otherwise | **Aligned** (rewritten, incl. ranges 0.8/1.2, 0.7/1.5, min/max). |
| EquipmentVector | needs >= 2 process items; pool rows with TEC >= $20M and >= 3 items; archetype subset when >= 5 rows; similarity >= 0.30; top-5 weighted; range = P20/P80 of the top 15 | **Aligned** (was: no gates, threshold 0.1, range 0.5x/1.5x). Explains the $140M FPSO match on real data. |
| SURF_User | inputs: production/injection/total wells, drill centers, tieback km, water depth, region, sour, pressure, riser type; expands to `estimate_surf()` with Guyana-pattern defaults; range +/-25% | **Not aligned**: engine takes tree/flowline/riser counts with unit prices x 1.34. Needs `surf_estimator.py`; the UI card must then ask for wells / drill centers / tieback instead. |
| OSBL_Estimate | `OSBLEstimator(spark).estimate(archetype, scope_type, isbl, toggles)` | Engine has a 3-layer port with hard-coded curves; pending `osbl_estimator.py` + `ic_library_osbl_subcurves.json`. |
| Composite | not in the API | kept as an extra. |

## Analogues, bid, what-if, report

| Topic | API | Now |
|---|---|---|
| `get_analogues` | feature match (0.33/0.33/0.34) + capacity proximity within unit family; weights 0.60/0.40, adaptive to 0.45/0.55 and 0.35/0.65 when the exact domain x scope slice has > 10 / > 50 rows; tie-break by TEC | **Aligned** (unit families ported from the API). |
| `validate_bid` | EPC lump sum / 1.175; verdict vs range | Already aligned. |
| `screen_whatif` | rerun with overrides, per-model deltas | Already aligned (UI what-if). |
| HTML report | 9 tabs: Basis, How This Works, Code of Accounts, Comparable Projects, Cross-Check, Portfolio Experience, Uncertainties, Assumptions, Validation | Engine report is a single page with most of the same content; missing as named sections: Assumptions (derived list), Portfolio Experience narrative, Cross-Check ratio table. Backlog. |
| `save_engagement` | JSON + HTML per engagement | Not in the POC (brief: no engagement logging). |

## Effect on the truth evaluation (mock package)

Aligning the ensemble to the API changes the mock-package hit rate from 42%
(engine rules) to 44% (API rules); the real package result comes from the
next validation run, which now also reports the engine-mode variant.

## `analogue_estimator.py` (v3.0) vs `costbot/models/benchmark.py` (2026-09-29)

Rewritten as a faithful port. What changed against the first build's Benchmark:

| Topic | Reference | First build | Now |
|---|---|---|---|
| Size signal | explicit `size_estimate_musd`, or a size bucket / hint (tiny 15M ... mega 7B); nothing else | capacity x fixed factor per domain, else the project's own pool TEC (LOOCV) | **Reference behaviour**. The UI gained a "Rough size" bucket (README: "Benchmark if size provided"). Capacity heuristic and pool hint survive as evaluation switches only. |
| Score with a size | 0.6 cosine + 0.4 size proximity | 0.5 / 0.5 | 0.6 / 0.4 |
| Refinery modification with capacity | capacity-family peers: adaptive 0.6/0.4, 0.5/0.5, 0.45/0.55 (gated); very large targets drop scope_type | not implemented | implemented |
| Pool region | from cp30_location: Texas/Louisiana/Canada = North America, UK = Europe, India = Asia Pacific, else North America | country -> 8 regions | reference rule |
| Target region | API keyword map (Guyana, Brazil = North America) | country -> region map | reference rule |
| bf/gf in the pool | from the archetype name: `_bf` / replacement = brownfield, grassroots / `_gf` = greenfield, else unknown | from scope_type | reference rule |
| Facility class | pool: substring map on facility_type (ref, chem, pipeline ...); target: the raw facility string | archetype -> class on both sides | reference rule (a raw target string rarely matches; noted as a reference quirk) |
| Analogue cost basis | nominal TEC x CP30(GOM, 2024) / CP30(source location, basis year); back-extrapolation by 2014-2019 CAGR; flat beyond 2025 | pool's `tec_musd_normalized_2024` | reference formula using the pool's cp30_location (the country -> location table is empty in the package) |
| Model range | min / max of the qualifying analogues (`cost_range_low/high`) | P20 / P80 | min / max; P20/P80 still reported |
| Gate enrichment features | has_pipeline, has_epc, n_facilities ... from gate tables | absent | constant zeros (gate tables not in the package; neutralised by the scaler) |
| Everything else | threshold 0.3, max 20, +/-0.5 log decade band, relax to 1.0, scope_type fallback, canaries, overrides, confidence | same | same |

Consequence for the numbers: with no size input the reference Benchmark is
category-only cosine, which on the real package scored 29%. The 54% of the
first build came from its capacity heuristic; the 77% of the brief from the
pool-TEC hint. The honest production figure now depends on whether the user
gives a rough size: the validation matrix reports both.

Open question for `evaluation_harness.py`: cost basis of the comparison
(the Benchmark returns GOM-2024 dollars; the calculators return at-location).

## Still open after this file

1. `analogue_estimator.py`: Benchmark internals, the size band and the 77%.
2. `onshore_calculator.py`: multipliers per scope type, `chemical_expansion` (golden BCEP), EMMA table.
3. `evaluation_harness.py`: exactly which rows and hints produced 40/52.
4. `surf_estimator.py`: SURF inputs and pricing (UI card changes with it).
5. `osbl_estimator.py` + IC Library JSON.
