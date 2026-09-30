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

## Correction on round 2's 54%

Re-reading the first build's Benchmark (commit dbe068d) while restoring it:
when no explicit size and no usable capacity existed (every modification,
because the heuristic is off for mods), it fell back to the project's own
pool TEC without saying so. Refinery brownfield is mostly modifications, so
its 15/17 in round 2 leaned on that fallback. The restored variant keeps the
capacity band and the 0.5/0.5 blend and drops the fallback (pool TEC only
with `benchmark_size_mode='pool'`, evaluation only). Its honest number is
what the next corp run prints under "Engine Benchmark variant".

## Decision taken (Guilherme, 2026-09-30)

Restore the first build's Benchmark as a selectable variant
(`benchmark_mode = reference | engine`), default to the reference for
parity, show both in the app and in the report. Done in the commit that
carries this note; `validate.py` now runs the engine variant four ways
(ensemble, + size bucket, + forecasts excluded, harness convention).

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


---

# Round 4 (same day, 16:36): the engine Benchmark variant, leak-free

Code: `main` 2c2637a. Golden 25 / 10 / 0 again. Same package.

## Ensemble P50 within +/-30%, 52 projects

| Benchmark variant | no size signal | user gives a size bucket | forecasts excluded |
|---|---:|---:|---:|
| Reference (analogue_estimator v3) | 15 (29%) | 23 (44%) | 15 (29%) |
| Engine (size band, leak-free) | 15 (29%) | **33 (63%)** | 14 (27%) |

Any-model (best single model) for the same cells: reference 16 / 29 / 17,
engine 19 / 36 / 16.

## Reference harness convention (any model, any truth), 50 projects

| Benchmark variant | +/-30% | screening band | EVALUATION only |
|---|---:|---:|---:|
| Reference | 19/50 (38%) | 21/50 (42%) | 18/46 (39%) |
| Engine | **24/50 (48%)** | 27/50 (54%) | 23/46 (50%) |

Benchmark alone on that convention: reference 6/50, engine 13/50. EquipmentVector
and Composite now run on the real columns: 25 and 18 fires, 5 and 1 hits.

## Reading

1. Without any size information the two analogue models are equal at 29%.
   The engine variant's capacity heuristic on its own adds nothing.
2. The lever is the user's rough size. With it the engine variant reaches
   63%, refinery brownfield 14/17 (82%), and the reference 44%. That is a
   legitimate input: an estimator always knows whether a job is $50M or $500M.
3. Excluding forecast rows now hurts the engine variant (the size band needs
   the rows); round 2's "+2 hits, never hurts" was about the old Benchmark.
4. Still at zero in every configuration: oil sands (3), LNG (3), integrated
   petchem (3), offshore FPSO on the ensemble (3). Those are the calculators
   whose reference files have not arrived (`lng_calculator.py`,
   `offshore_calculator.py`) or the generic onshore correlation for oil sands.
5. On the reference's own convention, engine variant, the honest number is
   24/50 (48%) versus the brief's 40/52 (77%), the gap being the oracle
   Composite, the SURF component scoring and the models above.

## Honest numbers for David (leak-free, 2026-09-30)

- No size given: 29% of 52 projects within +/-30% (either analogue model).
- Rough size given by the user: 63% with the engine variant, 44% with the reference.
- His own "any model passes" convention, without the oracle Composite: 48%.
