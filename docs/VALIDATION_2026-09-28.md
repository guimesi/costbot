# Validation on the real data package, 2026-09-28 (round 1)

Environment: corporate Windows laptop, Python 3.12.1, Streamlit 1.64, local
run (not Databricks). Real package: pool 503, truth 53 rows / 52 projects,
equipment vectors 593, chips 857, CP30 324 rows (2014 to 2025), golden file
at `data/extracted_rates/_golden_baseline.json` (35 runnable cases).

## Results

| Check | Result |
|---|---|
| pytest (47 unit tests) | all pass on real data |
| Engine smoke (6 scenarios) | all expected models fire |
| Headless UI | pass |
| Golden baseline | 22 PASS, 10 XFAIL, 3 FAIL, 6 SKIP |
| Accuracy vs truth, ensemble P50 at +/-30% | **28/52 (54%)** |
| Accuracy vs truth, best single model | 31/52 (60%) |

Reference points: Sep 16 brief 40/52 (77%); first build's docs 42/50 (84%),
never reproduced.

### Golden baseline

Two of the three FAILs were typos in the XFAIL list (`Liza_Eh2` for
`Liza_Ph2`, `JUWO` for `JUDO`); their deviations match the documented
reasons exactly (offshore EMMA removed: +29%; Joliet without EMMA: +157%).
Fixed. The third, `BCEP_chemical` (+148%, onshore), is a genuine new
divergence; the next run prints its inputs and the engine chain.

### Accuracy by archetype (ensemble, +/-30%)

| Archetype | n | hits | note |
|---|---:|---:|---|
| refinery_bf | 17 | 15 (88%) | better than reported (13/17) |
| onshore_unconventional | 11 | 9 (82%) | median error 1% |
| onshore_petchem | 4 | 2 | |
| pipeline_mainline | 2 | 1 | calculator within 21% on the miss |
| lng_terminal | 1 | 1 | |
| everything else (ccs, ccs_gas_processing, integrated_petchem x3, lng_onshore x2, offshore_fpso x3, oil_sands x3, pipeline_complex x2, pipeline_replacement, renewable_diesel) | 17 | 0 | Benchmark-only, underestimates by 56% to 98% |

### The pattern behind the misses

In 18 of the 20 largest misses the only total-cost model that fired was
Benchmark, and it underestimated big projects by an order of magnitude
(an FPSO of $5.5B estimated at $106M, oil sands of $13B at $733M).

Two facts from the package explain a lot:

1. **381 of the 503 pool rows are `screening_forecast` / `planview_forecast`**:
   forecasts, not completed projects. Without a strong size signal the
   cosine match lands on them.
2. **Truth / pool TEC ratio for the same project: median 1.00, IQR 1.00 to
   1.00.** The pool's TEC for a truth project *is* the truth value. The
   engine (ported from the reference harness) uses the pool TEC as a size
   hint when a project is in the pool and no capacity is available. Whenever
   that hint is active, the model is told the magnitude of the answer.

Hypothesis to test in round 2: the reported 77% depends on that size hint.
Round 2 runs the accuracy four ways (capacity heuristic as now; pool TEC as
size hint always; no size hint; forecast rows excluded) and reports which
size signal each project got.

### Other observations

- Truth rows carry `cost_type` (50 TEC, 3 TBI), `test_type`
  (29 screening_validation, 19 predictive, 2 non_comparable, 3 missing) and
  `quality_role` (48 EVALUATION, 4 INTEGRITY_CANARY). The reference
  evaluation probably excluded non-comparable and canary rows; round 2
  reports hit rate per group so the denominators can be matched.
- 4 truth projects are not in the pool; 3 truth amounts could not be
  normalised to 2024 (no CP30 index for their basis year / location).
- CP30 GOM combined index: 2023 1.815, 2024 1.866, 2025 2.046. The 2025 jump
  (+9.6%) is what the 2026 extrapolation compounds to +20%. Worth asking
  whether 2025 is a real index or a forecast; the table also has an
  `esc_to_2025` column, suggesting 2025 may be the intended basis.
- `frankenstein` has `baseyear_usd_kusd` and `tec_multiplier`; the Composite
  model uses `direct_cost_kusd`. Check which the reference used.
- `ref_country_to_cp30_location.csv` is empty in the real package (0 rows);
  the engine does not depend on it.
- `semantic_chips` has 377 rows (mock had 857); Composite's archetype filter
  still fires.
