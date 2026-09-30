# Validation on the real data package, 2026-09-30 (round 3)

Same corporate laptop and package as round 1 and 2 (`docs/VALIDATION_2026-09-28.md`).
Code: `main` 7f5aaa4, i.e. after the faithful ports of `cost_bot_api.py`,
`analogue_estimator.py` v3.0 and `onshore_calculator.py`, with the reference
harness convention added as `scripts/evaluate_harness.py`.

## Checks

| Check | Result |
|---|---|
| pytest | 74 passed, 18 skipped (the reference-file parity tests; the files are not in corp) |
| Engine smoke, headless UI | pass |
| Golden baseline | **25 PASS, 10 XFAIL, 0 FAIL**, 6 SKIP (was 22 / 12 / 1) |

Golden: the three Joliet cases and every other onshore case now match the
reference to the digit (0.0%), which confirms the onshore port. BRACE stays
XFAIL for a different reason than assumed: its golden value (162.2) is the
project's actual TEC quoted in the reference docstring, not a calculator
output (the reference itself gives 1,906 to 2,341 there). BCEP is the stale
tuple, as documented.

## Accuracy, two conventions

| Convention | Result | Reference point |
|---|---:|---|
| Ensemble P50 within +/-30% (what the app shows) | **15/52 (29%)** | round 2: 28/52 (54%) |
| Best single model within +/-30% | 16/52 (31%) | round 2: 31/52 (60%) |
| Reference harness: any model, any truth, +/-30% | **14/50 (28%)**, 13/46 on EVALUATION | brief: 40/52 (77%) |
| Reference harness: screening band 0.70..1.60 | 15/50 (30%) | brief: 44/52 |

Per model on the harness convention (fired / within 30%): Benchmark 49 / 6,
Calculator_Onshore 14 / 4, Unconventional 10 / 7, Pipeline 3 / 0 (1 in
band), Offshore 2 / 0, LNG 1 / 0. EquipmentVector and Composite did not run:
the script looked for the mock column names (`vector_raw`,
`semantic_label`); the real package has `equipment_vector_json` and
`category` / `cost_category_l1` with `is_leaf`. Fixed after this run.

## Why the ensemble fell from 54% to 29%

Round 2's 54% came from the first build's own Benchmark: a size band from
the capacity heuristic that filtered the pool by order of magnitude, then a
0.5 / 0.5 cosine-size blend. It carried refinery brownfield at 15/17.

The faithful port of `analogue_estimator.py` v3.0 is a different model:
cosine over categories, a soft size signal (bucket or explicit) blended
0.6 / 0.4 only when given, no capacity band. Run without a size signal (the
reference harness setting) it scores 6/50 on its own; refinery brownfield
drops to 3/17. The reference harness comments record the same finding on
their side ("size_bucket ... triggers the 0.6/0.4 blend that REGRESSES
accuracy", run 029 3/44 vs 12/48 without it).

The variants still show the lever: user-given size bucket 23/52 (44%), pool
TEC (leaky) 30/52 (58%), bucket + forecasts excluded 24/52 (46%).

Unconventional went 9/11 -> 8/11 after LOOCV self-exclusion, as predicted.

## What the brief's 40/52 contains that the engine cannot

- Composite corrected with the truth value (`apply_oh=True`, "oracle
  ceiling" in the harness's own words).
- SURF scored as a component against a SURF-only truth for four projects.
- Two truths per project and canary rows counted as ordinary projects.

Without those, on the same convention and the same models, the number is
14/50 (16/50 once EquipmentVector and Composite run on the real columns is
the next thing to measure).

## Decision needed (Guilherme, not David)

Two honest numbers exist for the demo: the reference's own analogue model
(28% any-model, 29% ensemble) or the first build's analogue variant (54%
ensemble on round 2). Recommendation: restore the first build's Benchmark as
a selectable variant (`benchmark_mode = reference | engine`), default to
the reference for parity, and show both in the app and in the report. The
first build's code is in git (commit 8f8b141, `costbot/models/benchmark.py`).

## Other observations

- 6 onshore calculator no-fires are the harness's own unit rule
  (UNIT_MISMATCH_UNCONVERTIBLE); 5 are missing capacity in scope_inputs;
  14 truth projects have no scope_inputs row (41 rows for 52 projects).
- scope_inputs has no location column; the script used the pool's site /
  cp30 location. The harness's own location table
  (`ref_gate_project_location_mapping`) is not in the package.
- Two unconventional truths are $3M and $7M, below the $20M screening
  floor; they cannot be hit by any pool model (ratios 15x to 150x).
- Smoke scenario 2 (offshore): the spread gate drops the offshore calculator
  (2,214) and keeps EquipmentVector (301) alone; P50 = 301 with LOW
  confidence. Worth a look once `offshore_calculator.py` arrives.
