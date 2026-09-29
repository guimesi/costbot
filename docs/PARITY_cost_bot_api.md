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
| Calculator_Onshore | facility_type defaults to `process_plant_generic`; scope type is `BF-expansion` for any brownfield / expansion / modification / debottleneck, else `GF`; `FACILITY_TYPE_CORRELATION_MAP`; range +/-50% | **Aligned**, and the calculator itself is now a verbatim port of `onshore_calculator.py` (section below). |
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

## `onshore_calculator.py` (Calculator_Onshore), read 2026-09-29

`costbot/models/calculator_onshore.py` is a port of `estimate_onshore_tec()`
called the way `_run_calculator_onshore()` calls it. `tests/test_calculator_onshore.py`
checks 18 input combinations against the reference file to 1e-6 (skips when
`reference/onshore_calculator.py` is absent).

| Topic | Reference | Engine before | Now |
|---|---|---|---|
| TEC multipliers | `GF` 2.58, `BF-expansion` 2.61, `BF-unit-mod` 1.30; `TEC_MULTIPLIERS.get(scope_type, 2.58)` so any other string (the golden's plain `BF`) is 2.58 | keys greenfield / brownfield / expansion / modification, plain BF -> 2.61 | **Verbatim.** Explains the BRACE golden case. |
| Modification override | facility name containing modification / conversion / debottleneck forces `BF-unit-mod` | same idea, different key names | Verbatim. |
| Contingency | not added (`include_contingency=False`; multipliers calibrated on TEC truth that includes it) | not added | Aligned. `estimate_contingency_scsa` and the TCC / PI / EM / other-indirect CET sections exist in the reference for a user-facing breakdown; not called by the API path, not ported. |
| Escalation | 6% flat (4Q2025 indices to expenditure midpoint) | 6% | Aligned. |
| Facility resolution | exact IC Library key, exact tuple, alias, **substring** over aliases then over tuple keys (first hit), else `process_plant_generic` with a fallback reason; the calculator always fires | exact key or alias only, else no fire | **Verbatim**, including the quirks: `atmospheric_pipestill` hits alias `pe` (polyethylene), `polyethylene_expansion` hits `ethylene` (ethylene_complex). Readiness now needs a capacity only. The fallback reason is surfaced as the model warning. |
| IC Library CDU curve | `crude_distillation_unit` (aliases cdu, cdu_addition, crude_unit): ISBL = 0.0662 Q + 3.3812 $M, Q in kB/SD, valid 50 to 500; out of range via an alias raises in the reference (API: no fire) | absent (crude_unit -> refinery_bf) | Ported, out-of-range reports `ic_library_out_of_range`. |
| Tuples | 18 power-law tuples; `chemical_expansion = (474, 330)` | same 18 | Same. `CALIBRATION_STATUS` (N, circular, source project) now in the detail. |
| EMMA | 40 keys; exact, else first key that is a substring of the location or vice versa, else 202 | table with 13 engine additions (Joliet 519, New Mexico 412, Shanghai, United Kingdom, ...) | **Verbatim table and lookup.** Joliet, New Mexico, Shanghai, "Texas-BTN (GOM)" (hits `GOM` first) are factor 1.0 as in the reference; explains the three Joliet golden cases. Additions dropped; listed in the backlog for David. |
| Capacity unit | ignored for the tuples (raw number); BPD -> kB/SD only for the CDU curve | converted, no fire on a mismatch | **Deviation kept on purpose**: converted when a conversion is known (KBPD -> BPD, MTPA -> KTA, ...), raw number + warning otherwise. Same result as the reference whenever the unit matches the tuple's. |
| Empty facility type | `''` substring-matches the first alias (`ethylene`) | generic | Deviation: engine uses the API's documented default `process_plant_generic`. |
| Range | -30/+50 in the calculator, overridden to +/-50% by the API wrapper | +/-50% | Aligned (wrapper). |
| BCEP golden | expected 2650.3 = 474 x (1500/1500)^0.6 x 2.0446 x 2.58 x 1.06: the older `(474, 1500)` tuple | 6574.3 with `(474, 330)` | Stale golden case, not a chain difference. XFAIL note corrected. |

## `evaluation_harness.py` (how the 40/52 was measured), read 2026-09-29

`scripts/evaluate_harness.py` reproduces its conventions with the engine's
models; `scripts/evaluate_truth.py` stays the "what the user sees" view
(ensemble P50). The two answer different questions.

| Topic | Reference harness | What it means for the brief's number |
|---|---|---|
| Scoring unit | "any model passes": a project is a hit when ANY model, run on its own, lands within +/-30% of ANY of its truths; no ensemble, no archetype exclusions, no 5x clamp | 40/52 is not the accuracy of one number. Our ensemble P50 figure (54% on real data) and the harness figure are not comparable; the closest engine analogue was "best single model" 31/52. |
| Truths per project | one per (planview_id, eval_type): FINAL row -> Type B, highest `screening_validation` gate row -> Type A. A project can carry both and hit on either | more chances per project than one truth. |
| Denominator | unique planview_ids; CANARY and non_comparable included | 52 = 48 EVALUATION + 4 INTEGRITY_CANARY, matching the real truth table. |
| Truth normalisation | CP30 to 2024 at the location from `ref_gate_project_location_mapping.location_free_text` (substring map), fallback Louisiana then Texas-BTN (GOM) | that mapping table is not in the package; the script uses `scope_inputs.location` when present, else the pool's site / cp30 location. |
| Benchmark | enriched features from truth / pool / scope_inputs (domain, scope type, bf_gf, region from the CP30 location, fac_type, capacity); **no size signal** (`BENCHMARK_SIZE_BUCKET_ENABLED = False`), LOOCV | the reference Benchmark in the 40/52 is the cosine-only one (29% on its own in our matrix). |
| Composite | `estimate_production(..., apply_oh=True, truth_musd=<truth>)`; the file's own comment: "True for oracle ceiling", "truth leakage finding" | part of the 40/52 comes from a model that reads the answer. Not reproducible and not something a user could run. The script runs the engine's Composite on the project's own chip labels, without OH. |
| Calculator_Onshore | scope_inputs facility / capacity / free-text secondary_params; scope type from keywords (brownfield/revamp/expansion/existing -> BF-expansion; debottleneck/modification/mod_ -> BF-unit-mod; `_bf` archetype -> BF-expansion; grassroots override, negation-aware); location = free text into the EMMA lookup; unit conversion KBD/KBPD/KBD_NGL -> BPD and MTPA <-> MTPA_CO2 only, any other mismatch = no fire; fires for refinery_bf (exclusions are an API thing) | ported verbatim in the script. Note the harness DOES convert units and refuses mismatches, unlike the API path. |
| Calculator_Pipeline | OD, service, grade, pipe type, HDD %, congestion parsed from the free text with regexes; length from primary_capacity (miles default); location via `_PIPELINE_LOC_MAP` | parsing ported; `pipe_type` and `pct_hdd` are passed but the engine's pipeline model (pending `pipeline_calculator_v2.py`) does not use them. |
| Calculator_Offshore | topsides from a JSON `secondary_params`; scored against `truth_total_dev_musd` | ported (score against total dev when present). |
| Calculator_LNG | trains from a "N train" regex else round(MTPA/5); location free text (default 'png') | ported. |
| Unconventional | the project's own pool row, `exclude_self=True` | the engine's Unconventional had no self-exclusion until now: `exclude_planview_ids` added (also to EquipmentVector and Composite). Earlier evaluate_truth runs of Unconventional (9/11) may have benefited from the project's own pool row; the corp run will say. |
| EquipmentVector | the project's own 52-dim vector, LOOCV | ported: own `vector_raw` -> equipment list, self excluded. |
| SURF | four hard-coded projects scored against a SURF component truth | not reproduced. |
| Metrics | unweighted counts only (David directive 2026-09-16): N within +/-30%, N within the screening band 0.70..1.60, N zero-viable | same three numbers printed, per archetype too. |

## Still open after this file

1. `surf_estimator.py`: SURF inputs and pricing (UI card changes with it).
2. `osbl_estimator.py` + IC Library JSON.
3. `pipeline_calculator_v2.py`, `lng_calculator.py`, `offshore_calculator.py`: internals
   (and the `pct_hdd` / `pipe_type` inputs the harness already passes).
4. `composite_estimator.py` / `equipment_vector_estimator.py` / `unconventional_calculator.py`:
   the pool-side models; the harness shows how they are called, not what they do.
