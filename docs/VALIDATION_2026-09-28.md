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

---

# Round 2 (same day): the accuracy matrix

Same environment and package. Golden: 22 PASS, 12 XFAIL, 1 FAIL
(`BCEP_chemical`, see below), 6 SKIP.

## Accuracy vs truth, ensemble P50 at +/-30%, 52 projects

| Benchmark size signal | pool as shipped | forecast rows excluded |
|---|---:|---:|
| none (cosine only) | 15 (29%) | |
| capacity heuristic (what the app does for a typed-in project) | **28 (54%)** | 30 (58%) |
| pool TEC of the project itself (reference harness LOOCV enrichment) | 38 (73%) | **40 (77%)** |

The bottom-right cell reproduces the Sep 16 brief to the digit: 40/52, and
40/48 on `quality_role = EVALUATION`. The 77% is therefore obtained by
giving Benchmark the project's own pool TEC as its size band, and the pool
TEC of a truth project equals the truth (ratio 1.00, IQR 1.00 to 1.00).
For a project a user types into the app, that signal does not exist; the
comparable figure is 54% (58% with forecast rows dropped from the pool).

What the size signal does per archetype (pool hint, forecasts excluded, vs
capacity heuristic): oil sands 3/3 vs 0/3, integrated petchem 2/3 vs 0/3,
CCS 2/2 vs 0/2, renewable diesel 1/1 vs 0/1, pipeline replacement 1/1 vs
0/1, onshore petchem 3/4 vs 2/4. Refinery brownfield (16/17) and
unconventional (9/11) are the same either way: their models do not depend
on the Benchmark size band.

Other reads from the matrix:
- Dropping the 381 `planview_forecast` rows from the analogue pool helps a
  little everywhere (+2 hits) and never hurts. Worth making the default.
- In 33 of 52 projects Benchmark was the only total-cost model; the
  calculators fired in 19. The calculators' own hit rate is stable across
  variants (11 to 12 of 19).
- `INTEGRITY_CANARY` rows: 0/4 in every variant, as intended for canaries.
- One unconventional miss is a $7M project, below the $20M screening floor.

## BCEP_chemical (golden FAIL)

Inputs: `chemical_expansion`, 1500 KTA, Baytown, GF. Engine: ISBL at GOM
1175.8 (474 x (1500/330)^0.6), EMMA 2.0446, ISBL at location 2403.9, TEC
multiplier 2.58, escalation 6%, TEC 6574.3. Expected 2650.3 = 2403.9 x
1.1025. So the reference applied essentially no ISBL-to-TEC multiplier to
this correlation (1.04 x 1.06 escalation = 1.1024), which suggests the
474/330 KTA "chemical_expansion" figure is already a TEC-level number in
the reference, not an ISBL. Marked XFAIL under investigation; decision for
the manager together with the brownfield multiplier item.

Resolved 2026-09-29 with `onshore_calculator.py` in hand: the golden value is
the OLD tuple. 474 x (1500/1500)^0.6 x 2.0446 x 2.58 x 1.06 = 2650.3 exactly.
The reference file now carries `chemical_expansion = (474, 330, 0.60)` with the
comment "was (474, 1500) but 1500 was wrong capacity", so the golden case is
stale, not a different multiplier chain. The engine's 6574.3 is what the
current reference computes. Same file also explains the Joliet cases (its EMMA
lookup has no Joliet, factor 1.0) and BRACE (plain "BF" is not a multiplier
key, falls back to 2.58); both are now ported and should pass.

## Implications

1. The accuracy the brief reports is not what a user will experience.
   Stated honestly: 54% overall today, 88% for refinery brownfield, 82% for
   unconventional, near zero for large greenfield projects where only the
   analogue model fires.
2. The size band is the lever. A legitimate size prior (not the truth)
   would recover much of the gap: calibrate the capacity-to-size factors
   per archetype from verified pool rows instead of the fixed table, and/or
   feed the calculators' estimate into Benchmark as its size band when a
   calculator fires. Both are measurable with this harness, leak-free.
3. Default the analogue pool to verified rows (exclude forecasts).


---

# Addendum 2026-09-29: what the 40/52 is (from `evaluation_harness.py`)

The manager's harness arrived. Its scorecard is "any model passes": a
project is a hit when any single model, run on its own with no ensemble, no
exclusions and no clamp, lands within +/-30% of any of the project's truths
(a project can carry a FINAL truth and a screening-gate truth). CANARY and
non_comparable projects count. Its Composite runner corrects with the truth
value (`apply_oh=True`; the file calls that the "oracle ceiling"). Its
Benchmark carries no size signal at all.

So the matrix above and the brief measure different things. The row-2 cell
that "reproduces 40/52" does so by another route (ensemble P50 with the pool
TEC as size band), a coincidence of totals, not the same computation. The
honest comparison for the brief's convention is `scripts/evaluate_harness.py`,
now part of `validate.py`: it prints the per-model matrix and the three
unweighted counts the harness prints (+/-30%, screening band, zero-viable),
minus the oracle Composite and the SURF component runner, which no user could
run. Expect it below 40/52 by roughly the Composite-only hits.

Also new in the engine from this file: LOOCV self-exclusion for
Unconventional, EquipmentVector and Composite (`exclude_planview_ids`). The
earlier unconventional 9/11 may have used the project's own pool row.
