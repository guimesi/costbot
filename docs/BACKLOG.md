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

- [x] Split `engine.py` into the `costbot/` package (one module per model,
      constants, data, escalation, ensemble, screening, report) with `engine.py`
      as a facade; split `app.py` into `app_pages/` + `ui/` with `st.navigation`.
      Done 2026-09-26, all four test layers unchanged.
- [x] Performance, measured 2026-09-26 on the mock package (same row counts as the
      real one), Apple Silicon: `screen_project` with all pool models firing = 28 ms;
      a full estimator-page rerun with results on screen = 26 ms server-side.
      EquipmentVector was 10 ms (JSON parse of 593 vectors per call) and is now
      0.5 ms via a parsed matrix cached on `DataStore.derived()`. Benchmark (5 ms)
      and Composite (7 ms) are not worth caching. The "page reload" feeling on
      Databricks is therefore not engine time: it was the double rerun (fixed with
      fragments) plus network round trip and Plotly re-rendering in the browser.
      Remaining lever is client-side: fewer/lighter charts, `st.form` on the input
      panel so widgets do not rerun the page on every change. Both belong to the UX pass.
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
