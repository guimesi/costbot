# Backlog

Working list. Order inside each section is rough priority. Move items to
the review docs when done.

## Decisions that only the manager can take (deviations from README)

See `docs/REVIEW_2026-09-26.md` section 3. Short form:

1. Benchmark exclusions for `offshore_fpso` and `onshore_unconventional`: README says exclude, engine includes.
2. OSBL trigger: README "whenever any model fires", engine only from Calculator_Onshore ISBL.
3. 9 vs 10 models (Composite).
4. Benchmark firing on archetype alone vs "if size provided".
5. Brownfield TEC multiplier 1.30x (docs) vs 2.61x (engine, deliberate).
6. Calculator_LNG in the ensemble with 0% accuracy.

## Engineering

- [ ] Split `engine.py` (2.9k lines) into a package: `costbot/data.py`,
      `costbot/models/<model>.py`, `costbot/ensemble.py`, `costbot/escalation.py`,
      `costbot/report.py`; keep `engine.py` as a thin facade so app and tests keep
      working. Split `app.py` into `app_pages/` (estimator, data, code, deps, specs)
      plus `ui/components.py`. Do this BEFORE the UX redesign so the UI is only
      rewritten once.
- [ ] Cache the Benchmark one-hot matrix and scaler per DataStore (recomputed every call).
- [ ] Pre-parse `ref_equipment_vectors.csv` JSON vectors into a numpy matrix once.
- [ ] Composite: vectorize chip scoring (DataFrame.apply with Python scorer per scope item).
- [ ] What-if: propagate all `secondary_params` keys, not only topsides/water depth.
- [ ] Add `pipeline_gathering` and `lng_offshore` to the UI archetype list or drop from routing.
- [ ] Process Domain input is collected but not used by Benchmark; wire in or remove.
- [ ] `_convert_capacity` cross-family conversions (KTA <-> BPD via fixed density): document or refuse.
- [ ] Data Package / Code Inventory tabs: remove or label rows for files not shipped.
- [ ] `APP_DOCUMENTATION.md` and `DEMO_SCRIPT.md`: rewrite after decisions above; drop unverified accuracy numbers.

## Validation in the production environment (real data)

- [ ] `COSTBOT_DATA_DIR=<real package> python scripts/evaluate_truth.py --csv results.csv`
      and compare with the email's 40/52 (77%).
- [ ] Check `evaluate_truth.py` column auto-detection against the real `project_truth.csv`.
- [ ] Run `test_golden_baseline.py` against the REAL `_golden_baseline.json` (expect the
      12 documented XFAILs, zero FAIL).
- [ ] Confirm CP30 table has `location`, `year`, `combined_idx` columns and the
      `Texas-BTN (GOM)` row; the 2026 extrapolation depends on it.

## Layout / UX / UI (not started, parked on purpose)

- [ ] Full pass on layout, visual hierarchy and flow. Candidates: `st.navigation`
      multipage instead of 5 tabs; results in a stable slot so the page does not jump;
      inputs in `st.form` per card; theme via `.streamlit/config.toml`; native
      elements instead of the custom CSS/HTML blocks; Material icons; Vega charts
      instead of Plotly for the comparison bar.
- [ ] Readiness panel as a live checklist that updates as inputs are filled (fragment),
      before the user presses Run.
