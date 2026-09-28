# Backlog

Working list. Order inside each section is rough priority. Move items to
the review docs when done.

## Decisions that only the manager can take (deviations from README)

Evidence from the first real-data run (docs/VALIDATION_2026-09-28.md): ensemble
54% vs 77% reported; Benchmark alone underestimates large projects by 56% to 98%;
the pool is 76% screening forecasts; the pool TEC of truth projects equals the
truth, so the LOOCV size hint leaks the answer. Discuss items 1 and 4 with that in hand.

See `REVIEW_2026-09-26.md` section 3. Short form:

1. Benchmark exclusions for `offshore_fpso` and `onshore_unconventional`: README says exclude, engine includes.
2. OSBL trigger: README "whenever any model fires", engine only from Calculator_Onshore ISBL.
3. 9 vs 10 models (Composite).
4. Benchmark firing on archetype alone vs "if size provided".
5. Brownfield TEC multiplier 1.30x (docs) vs 2.61x (engine, deliberate).
6. Calculator_LNG in the ensemble with 0% accuracy.

## Modelling (needs the manager's OK before changing model behaviour)

- [ ] Benchmark size prior without leakage: calibrate capacity-to-size factors per
      archetype from verified pool rows (log TEC vs log capacity), and/or use the
      calculators' estimate as Benchmark's size band when one fires. Measure with
      `scripts/evaluate_truth.py`; today 54% (capacity heuristic), 77% only with the
      truth-derived hint. See docs/VALIDATION_2026-09-28.md round 2.
- [ ] Default `pool_exclude_forecast=True` (drops 381 planview_forecast rows; +2 hits, never hurts).
- [ ] `chemical_expansion` correlation: reference applies ~1.0 TEC multiplier (golden
      BCEP_chemical). Decide whether that correlation is TEC-level.

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
- [ ] `docs/APP_DOCUMENTATION.md` and `docs/DEMO_SCRIPT.md`: rewrite after decisions above; drop unverified accuracy numbers.
- [ ] Top-level "Comparable projects" list uses `_get_analogues` (feature + capacity score) and shows 0.00 when only archetype is known; consider reusing the Benchmark analogues instead.

## Validation in the production environment (real data)

- [ ] `COSTBOT_DATA_DIR=<real package> python scripts/evaluate_truth.py --csv results.csv`
      and compare with the email's 40/52 (77%).
- [ ] Check `evaluate_truth.py` column auto-detection against the real `project_truth.csv`.
- [ ] Run `tests/test_golden_baseline.py` against the REAL `_golden_baseline.json` (expect the
      12 documented XFAILs, zero FAIL).
- [ ] Confirm CP30 table has `location`, `year`, `combined_idx` columns and the
      `Texas-BTN (GOM)` row; the 2026 extrapolation depends on it.

## Layout / UX / UI

- [x] UX pass 2026-09-26: 3 pages (Estimator, Models, Data) with top navigation;
      theme in `.streamlit/config.toml`, all injected CSS removed; cards as bordered
      containers; live **Model readiness** checklist from `model_readiness()`;
      KPI metrics; Altair chart with range whiskers and P50 rule; per-model tabs;
      column-configured tables; bid check and what-if as cards; stale-results notice;
      facility type dropdown that accepts typed values; equipment duplicates merge.
      Screenshots verified with Playwright + Chrome.
- [ ] Input panel as `st.form` if per-widget reruns ever feel slow on Databricks
      (would remove the live readiness; measure first).
- [ ] Offshore/pipeline/LNG specific fields could move into their own cards with icons.
- [ ] Empty-state illustration or example presets ("Load demo scenario" pills) for demos.
- [ ] Print-friendly view of the results (or rely on the HTML report).
- [ ] Mobile/narrow layout check (columns collapse; horizontal containers wrap).
