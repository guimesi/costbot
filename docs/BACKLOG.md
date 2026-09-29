# Backlog

Working list. Order inside each section is rough priority. Move items to
the review docs when done.

## Decisions that only the manager can take (deviations from README)

Evidence from the first real-data run (docs/VALIDATION_2026-09-28.md): ensemble
54% vs 77% reported; Benchmark alone underestimates large projects by 56% to 98%;
the pool is 76% screening forecasts; the pool TEC of truth projects equals the
truth, so the LOOCV size hint leaks the answer. Discuss items 1 and 4 with that in hand.

See `REVIEW_2026-09-26.md` section 3. Short form:

Status after reading `cost_bot_api.py` (2026-09-29, see docs/PARITY_cost_bot_api.md):

1. ~~Benchmark exclusions~~ RESOLVED: the API excludes Benchmark for offshore_fpso,
   onshore_unconventional and lng_onshore; engine now matches.
2. ~~OSBL trigger~~ RESOLVED: the API triggers OSBL only from a Calculator_Onshore ISBL
   (or a user ISBL); engine already did that. The README sentence was loose.
3. ~~9 vs 10 models~~ RESOLVED: Composite is not in the API; kept as an extra, never routed.
4. ~~Benchmark firing on archetype alone~~ RESOLVED by `analogue_estimator.py`: it fires
   without a size (cosine on categories) and takes an optional size bucket / explicit size.
   The README's "if size provided" is that bucket; the UI now offers it as "Rough size".
5. ~~Brownfield multiplier~~ RESOLVED by `onshore_calculator.py`: GF 2.58, BF-expansion 2.61,
   BF-unit-mod 1.30, anything else 2.58. Ported verbatim (2026-09-29).
6. Calculator_LNG in the ensemble: the API includes it (no exclusion). Engine matches.
7. NEW: the API's 5x cap clamps each bound to median/5 .. median*5 (up to 25x span);
   the brief's text says high/low <= 5x. Engine follows the API; confirm the intent.

## Modelling (needs the manager's OK before changing model behaviour)

- [ ] Benchmark size prior without leakage: the reference offers a user size bucket
      (now in the UI). Candidates beyond that: calibrate capacity-to-size per domain from
      verified pool rows, or feed a calculator's estimate as `size_estimate_musd`.
      Measure with `scripts/evaluate_truth.py --size-hint {api,bucket,capacity,pool}`.
- [ ] Default `pool_exclude_forecast=True` (drops 381 planview_forecast rows; +2 hits, never hurts).
- [ ] Composite: the reference's production path sums the project's own scope chips with subtotal
      gap-filling and an OH correction that reads the truth (`apply_oh=True`). Decide with David what a
      user-facing Composite may use; the engine's version matches chip labels across projects, no OH.
- [ ] Pipeline calculator: accept `pipe_type` and `pct_hdd` (the harness passes them) once
      `pipeline_calculator_v2.py` is available.
- [x] `chemical_expansion` correlation: the golden BCEP value came from the older tuple
      (474 @ 1500 KTA); the reference now uses (474 @ 330 KTA) and so does the engine.
- [ ] EMMA gaps inherited from the reference: Joliet, New Mexico, Shanghai, "Texas-BTN (GOM)"
      resolve to factor 1.0 (the lookup finds no key, or hits "GOM" first). Illinois is 665
      in the same table. Ask David whether Joliet should map to Illinois.
- [ ] Reference alias quirks kept for parity: any name containing "pe" (e.g.
      atmospheric_pipestill) resolves to polyethylene, "...ethylene..." to ethylene_complex.
      Worth a curated alias list once David agrees.

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
