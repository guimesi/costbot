# Handoff: costbot Estimator redesign (Proposta A "Guiada" and Proposta B "Console")

Repo: `guimesi/costbot` (branch `main`). Streamlit 1.52+, theme in `.streamlit/config.toml`, pages in `app_pages/`, shared UI in `ui/`, engine untouched.

## Overview
Two alternative UIs for the same estimator. Both keep the engine (`costbot/screening.py: screen_project`, `model_readiness`, `validate_bid`) and the session-state contract from `app_pages/estimator.py` (`equipment_items`, `scope_items`, `last_scope`, `last_results`). Only presentation changes.

- **Proposta A – Guiada**: same two-column shape as today. Left column becomes a stepper (done / active / optional) with a compact readiness strip and the Run button pinned at the bottom. Right column: hero P50 + one shared $ axis (P20–P80 band, P50 marker, one dot per model), then a tabbed surface (Models · Comparable projects · Bid check · What-if). Models and Data pages become dense tables. **Implementable in pure Streamlit.**
- **Proposta B – Console**: whole scope form lives in a navy sidebar; the main area is one no-scroll results console: estimate strip (P50, confidence, range axis with bid marker + inline bid check), then two cards (model dot-plot, comparable projects). **Needs the Streamlit sidebar plus a small CSS block** (dark sidebar, card radii), or a non-Streamlit front end.

Suggested rollout: implement each as a separate `st.Page` behind a query param or env flag (`COSTBOT_UI=a|b`) so both can be demoed side by side against the current page.

## About the design files
The `.dc.html` files are **design references** (HTML mockups), not code to ship. Recreate them in Streamlit with its native widgets and Altair; use the HTML only to read exact sizes, colors, copy and layout. Numbers in the mocks are from the synthetic data package (MOCK-*).

## Fidelity
High-fidelity for layout, hierarchy, colors, typography and copy. Interactions (expand/collapse, tabs, bid marker) are described here, not fully wired in the mocks. Proposta A has a `screen` tweak (estimator / models / data) and a `stale` flag; Proposta B has a `bidMusd` tweak that moves the bid marker and recomputes the verdict.

## Files
- `Proposta A - Guiada.dc.html` – Estimator + Models + Data screens (switch via the top tabs).
- `Proposta B - Console.dc.html` – Estimator console.
- `Atual - Estimator.dc.html`, `Atual - Models.dc.html`, `Atual - Data.dc.html` – recreation of the current app for reference.
- `Análise UX.dc.html` – diagnosis (8 problems), principles, quick wins.

Open any file directly in a browser; they are self-contained.

## Design tokens
Keep `config.toml` colors. Change fonts.

- primary / ink: `#1F3A5F` (navy), text `#1F2933`, muted `#5F6B7A`, faint `#9AA5B1`
- border `#D9DFE7`, row divider `#EEF1F5`, page bg `#F4F6F9` (A) / `#EEF1F5` (B), card bg `#FFFFFF`, table header bg `#FAFBFC`
- status: green `#1B7F4C`, amber `#B86E00`, red `#B42318`, teal `#2A9D8F` (similarity bars), gold `#E9A23B` (indirect / OSBL)
- badge fills: color at 10% alpha, e.g. `rgba(27,127,76,.1)` with text in the full color
- font: **IBM Plex Sans** 400/500/600 for UI, **IBM Plex Mono** 400/500/600 for every number ($, counts, ids). Update `config.toml`:
  `font = "IBM Plex Sans:https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap"` and `codeFont = "IBM Plex Mono:…"`. Base size 14px.
- radii: cards 8–10px (A), 12px (B); inputs/buttons 6px; badges 4px; pills 999px
- spacing: page padding 24px; card padding 12–14px (inputs) / 20–24px (results); grid gaps 10px (stepper), 16–18px (result cards)
- section labels: 12px, 600, uppercase, letter-spacing .06em, color muted

## Proposta A – Guiada

### App bar (52px, white, 1px bottom border `#D9DFE7`)
Left: 26px navy square with `calculate` icon, "GP screening estimator" 600, `POC v1.1` mono 11px in a 1px bordered pill. Then nav tabs Estimator / Models / Data (32px tall, 13.5px; active = bg `#F4F6F9`, navy, 600). Right: 12px muted disclaimer with `info` icon. **Remove** the per-page `## title` + badge + caption block from `app.py`.

Streamlit: `st.navigation(position="top")` already gives the tabs; drop the `st.markdown("## …")`/`st.badge`/`st.caption` lines and move the disclaimer next to the download button.

### Layout
`st.columns([420px-ish, rest])` → use `st.columns([5, 9], gap="large")`. Left column sticky in the mock; in Streamlit just keep it short.

### Left column – stepper
Header row: "SCOPE" section label + "Reset" tertiary link.

Each step is a white card, 1px `#D9DFE7`, radius 8, padding 12/14, a 22px circle at left:
- **Done** (steps 1 Project, 2 Equipment list): green circle with `check` icon; title 600; one-line grey (13px, `#5F6B7A`) summary of the values ("Petrochemical (onshore) · US Gulf Coast · 2025 USD · Greenfield" / "63 process items · pump 24, exchanger 18, …"); "Edit" link 12px navy at right. Below step 2 a green chip 11.5px `bolt` "Unlocks Equipment vector".
- **Active** (step 3 Facility and capacity): border `#1F3A5F`, numbered navy circle "3", subtitle "One number is enough. Unlocks the onshore calculator and the OSBL overlay.", fields Facility type (select), Primary capacity (number, mono) + Unit (select, 120px), and an `info` hint "Reference for polyethylene: 625 KTA. Scaling exponent 0.6." (from `ISBL_CORRELATIONS`).
- **Optional** (step 4 Scope items): outlined grey circle "4", "optional" in grey after the title, chevron, one-line hint "Add process units and OSBL packages to unlock Composite (low accuracy, 26%)."
- Offshore-only SURF card follows the same pattern, inserted after step 3 when `is_offshore`.

Streamlit: `st.expander(label=f"✓ Project · {summary}", expanded=False)` for done steps, `expanded=True` for the active one. Determine "active" as the first step whose inputs are empty. Keep `ui/cards.py` fragments inside the expanders.

**Models ready** card: label + mono "4 / 5"; a 5-segment progress bar (4px tall, green segments, grey for missing); then wrapped 12px chips, each a 7px dot (green filled = ready, grey outlined = needs) + model label; "auto" suffix for OSBL, "· needs scope items" for missing ones. Data: `model_readiness(scope, data)` minus `not_routed`.

Run button: full width, 40px, navy, white 600 text, `play_arrow` icon (`st.button(type="primary", width="stretch")`).

### Right column – results
1. Optional stale banner: bg `rgba(31,58,95,.08)`, border `rgba(31,58,95,.2)`, navy text, `history` icon, "Run now" link right.
2. **Hero card** (white, radius 10, padding 22/24): three columns
   - "BEST ESTIMATE · P50" label; value mono 44px 600 `$1,412` + `M` 22px grey; sub "TEC, 2025 USD · {project_name}".
   - "RANGE · P20 TO P80" label; mono 22px `$1,020M – $1,890M`; sub "−28% / +34% around P50" (compute from range vs P50).
   - "CONFIDENCE" label; pill 600 with 8px dot (green for HIGH/MEDIUM-HIGH, amber MEDIUM, red LOW, teal COMPONENT_ONLY — `CONFIDENCE_COLORS`); sub "3 models agree within 1.1×" (from `ens.reasoning`/spread).
   - Right: "HTML report" secondary button (`st.download_button`).
   - **Range axis** (74px tall): domain $0 → ~1.7×P80 rounded; P20–P80 band 22px tall `rgba(31,58,95,.12)`; P50 vertical 2px navy line with "P50" label above; mono 11px "P20 $1,020" / "P80 $1,890" below band ends; one 12px dot per model (navy filled = in ensemble, gold outlined = indirect, grey = gated out) with a 2px `#9AA5B1` whisker from low to high; axis ticks mono 10.5px `#9AA5B1`. Legend row below (12.5px): In ensemble (n), Indirect overlay not in total, Gated out (n); right-aligned `trending_up` CP30 note.
   - Streamlit: Altair layered chart — `mark_rect` for the band, `mark_rule` for P50 and whiskers, `mark_point(filled, size=120)` for models colored by role via `ROLE_COLORS`; `height=90`, no y axis. Replace the current `_model_chart`.
3. **Evidence card** with a tab strip (bg `#FAFBFC`, active tab navy with 2px underline): Models · Comparable projects (count pill) · Bid check · What-if.
   - Models tab: table rows (grid `1.4fr 110px 170px 1fr 28px`): dot + name 500; estimate mono 500; range mono 13px grey; "Role · basis" 12.5px grey (e.g. "In ensemble · ISBL 6/10 scaling, EMMA 2.05, TEC ×2.58 greenfield"); chevron. Row click expands the existing `_render_model_detail`. Footer line with `rule` icon: ensemble explanation (`ens.reasoning`).
   - Bid check / What-if tabs: move the existing widgets here unchanged.
4. **Closest comparable projects** card: header + "All 12 →"; grid `1.5fr 110px 120px 1fr .7fr 1fr`: Project 500, TEC mono, Match = 6px teal bar + mono score, Country grey, Capacity mono grey, Scope grey. Show top 4; the tab shows all.

### Models page (A)
One white table, header row bg `#FAFBFC`: Model (600 + mono id 11px grey) · Method · Needs · Role badge (color per `MODEL_SPECS` badge colour) · Within ±30% (56px bar green ≥60 / amber ≥40 / red below + mono value). Routing and ensemble rules go into an expander per row. Data: `MODEL_SPECS`, `ARCHETYPE_MODELS`.

### Data page (A)
Amber banner (bg `rgba(184,110,0,.08)`, border `rgba(184,110,0,.25)`, text `#7A4A00`) with "Synthetic package." + `data_dir` mono at right. Manifest table: Table (mono 12.5) · Rows mono · Cols mono grey · Used-by badge (blue = model input, green = escalation, grey = reference/unused) · Description · "Preview" link that opens `st.dataframe(df.head(50))` below the row (or in a `st.dialog`).

## Proposta B – Console

### Sidebar (300px, bg `#1F3A5F`, white text)
Header: `calculate` icon, "GP screening estimator" 600, `POC v1.1` mono pill 10.5px at right; 1px `rgba(255,255,255,.12)` divider.
Body (padding 16/20, gap 14): "SCOPE" label + Reset. Inputs are 34px tall, bg `rgba(255,255,255,.08)`, border `rgba(255,255,255,.18)`, radius 6, 13.5px: Archetype, Location, Basis year (3-segment 24/25/26; selected = white bg navy text), Scope type. Divider. Then three groups, each with a 12px label at left and an 10.5px model chip at right (mint `#7FD3B5` dot = ready, outlined = not):
- Facility · capacity → "Onshore calc": Facility select + capacity mono (80px) + unit (64px) in one row.
- Equipment · 63 items → "Equipment vector": equipment as chips `pump 24`, `exchanger 18`… (bg `rgba(255,255,255,.1)`, radius 4, 12px, count mono) + dashed "Add" chip.
- Scope items → "Composite": dashed 34px drop-zone "Add a process unit or OSBL package".
Bottom: "4 of 5 models ready" / mono "Composite off"; Run button 40px **white** with navy text. Footer links Models · Data (12.5px).

Streamlit: put all inputs in `st.sidebar`; style with a CSS block (`[data-testid="stSidebar"] {background:#1F3A5F}` + input/text colors) or set `secondaryBackgroundColor` to navy in a B-only theme. Equipment chips = `st.pills` with `selection_mode="multi"` for removal, or the existing fragment.

### Main (padding 24/28, bg `#EEF1F5`)
Header row: 12px "Screening estimate · {date}", h1 22px 600 project name; scenario pills "Base" (navy filled) and "+ What-if scenario" (outlined) — what-if runs become extra pills; "Report" button at right.

**Estimate strip** (white, radius 12, padding 22/26, grid `auto 1fr`):
- Left (right border `#EEF1F5`): "P50 · TEC 2025" label; mono 52px 600 `$1.41` + `B` 26px grey; confidence line 13px 600 with dot.
- Right: line "P20 – P80 range: **$1,020M – $1,890M**" and "3 models in ensemble · spread 1.10×"; 64px axis identical to A's (band 24px, P50 line + mono label above, model dots) plus a **bid marker**: 2px dashed red vertical with mono "Bid $1,650M" label under the axis. Tick labels `$0 · $600M · $1.2B · $1.8B · $2.4B`.
- Bid check row inline under the axis: "Bid check" 600, 120px mono number input, TEC / EPC lump sum segmented control (selected navy filled), verdict text 12.5px 600: green "Within range · +17% vs P50", amber "Above range · +x%", red "Below range · −x%", grey placeholder when empty. Wire to `validate_bid`.

**Two cards** (grid `1.1fr 1fr`, gap 18, radius 12):
- "How the models land": rows `150px 1fr 90px`: name 13px 500 + role 11.5px grey; an 18px mini axis per row (band ghost `rgba(31,58,95,.06)`, grey whisker, 10px dot navy / gold-outlined); estimate mono right. Footer with `rule` icon explanation. Row click → model detail (`st.expander` or `st.dialog`).
- "Comparable projects": rows `1fr 90px 64px`: name 500 (ellipsis) + meta "Country · capacity · scope" 11.5px grey; TEC mono; 28px teal match bar + mono score. "All 12 →" link.
Footer: 12px disclaimer with `info` icon.

## Interactions & state (both)
- `scope` dict is rebuilt every rerun as today; stale = `scope != last_scope` → banner (A) / "Run" button turns primary + pill "outdated" (B).
- Step state (A): done = required inputs of the step present; active = first not-done step; the rest collapsed.
- Axis domain: `0 → ceil(max(P80, max model high, bid) × 1.15 / 300) × 300` so ticks are round.
- Model dot colors from `ROLE_COLORS`; confidence colors from `CONFIDENCE_COLORS`.
- Hover on a dot: tooltip "Model · $est (low–high)".
- Bid marker updates on every keystroke (`st.number_input` rerun), verdict from `validate_bid`.

## Screenshots
`screenshots/` — `proposta-a-estimator.png`, `01-proposta-a.png` (Models), `02-proposta-a.png` (Data), `proposta-b-console.png`, `atual-estimator.png` (current app for comparison). All at 1440px.

## Assets
Icons: Material Symbols Rounded (already used via `:material/...:`). Fonts: Google Fonts (IBM Plex Sans / Mono). No images.

## Claude Code prompt (copy/paste)
> Read `design_handoff_costbot_redesign/README.md` and open `Proposta A - Guiada.dc.html` and `Proposta B - Console.dc.html` in the same folder. Implement both as new Streamlit pages `app_pages/estimator_a.py` and `app_pages/estimator_b.py` (plus `ui/results_a.py`, `ui/results_b.py`), reusing `costbot.screening`, `ui.cards` and session-state keys from `app_pages/estimator.py`. Register them in `app.py` behind `COSTBOT_UI` (`current|a|b`). Update `.streamlit/config.toml` fonts to IBM Plex. Replace `_model_chart` with the shared-axis Altair chart described in the README. Do not change the engine. Run `make test` and the headless UI test after each page.
