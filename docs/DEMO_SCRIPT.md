# GP Screening Cost Estimator — Demo script

**Who this is for:** Guilherme presenting the POC to David and the team, live, from the
Databricks App. Read it once end to end, then keep it open on a second screen.

**How to use it.** Every case has four blocks: *Say* (what you say, in your own words),
*Do* (exactly what to click, with the labels as they appear on screen), *See* (what the
screen shows) and *Wireframe check* (what matches David's wireframe and brief, what does
not, and why). Numbers in *See* are the ones from the real package on 2026-09-30; they
will match what you see unless the data package changes.

**Time.** Full run: 25 minutes. Short run: cases 1, 2 and the accuracy conversation, 12 minutes.

---

## 0. Before the demo

- Open the Databricks App. The header reads **GP screening cost estimator** with a blue
  **POC v1.1** badge and the line *Class 5 screening estimate (±50% target). Deterministic
  models, no AI. Not a basis of estimate.*
- Three pages in the top navigation: **Estimator**, **Models**, **Data**.
- The header must **not** show a warning about synthetic data. If it does, the app is
  reading the mock package; stop and fix the deployment first (`docs/DEPLOY_DATABRICKS.md`).
- Press **Reset** (bottom of the input column) so the form is empty.

**Say (30 seconds).** "This is the screening estimator from the September 16 package. It
runs your nine deterministic models, ten with the composite from the wireframe, from flat
files, no LLM, no database. I will walk through one case per model family, then show the
accuracy we measured on the 52 truth projects, with the same conventions your harness uses."

---

## 1. The screen

**Say.** "Left side is the scope, right side is what the models make of it. Nothing runs
until I press the button, but the readiness list on the right updates as I type."

**See.**

| Left column, top to bottom | What it unlocks |
|---|---|
| **Project** card: Archetype, Location (CP30 region), Basis year (2024 / 2025 / 2026), Scope type (Greenfield / Brownfield / Expansion / Modification), Rough size, Project name, and an **Optional details** expander (Process domain, Analogue model) | Benchmark (analogues) |
| **Equipment list** card: Equipment type, Count, **Add** | Equipment vector |
| **Facility and capacity** card: Facility type, Primary capacity, Unit; extra fields appear for pipeline, offshore and LNG archetypes | Onshore / offshore / pipeline / LNG calculators, unconventional lookup |
| **Subsea scope (SURF)** card, offshore archetypes only | SURF subsea component |
| **Scope items** card: Scope item type, Facility name, **Add** | Composite (scope chips) |
| **Run screening estimate** and **Reset** | |

Right column: **Model readiness** (each eligible model with a badge: *Ready*, *Needs …*,
*Excluded for this archetype*, *automatic*), then, after a run, the results.

**Wireframe check.**

| Wireframe | App | Why |
|---|---|---|
| Five pages: Estimator, Data Package, Code Inventory, Dependencies, Model Specs | Three pages: Estimator, Models (specs + routing + dependencies + accuracy), Data | Code Inventory described files the Sep 16 package removed (parametric navigators, overlay stack); Dependencies and Model Specs merged into one page. |
| Four input sections: Core, Benchmark, Composite, Parametric / ADR | Five cards, one per model family | Same idea, re-cut by model family so each card says what it unlocks. |
| Model names A, A.1, B, B.1, Bottom-Up | The nine canonical names of the Sep 15 brief (Benchmark, EquipmentVector, Calculator_Onshore …) plus Composite | The brief renamed them; A.1 Calculator Plus (ADR) is not in the Sep 16 package, so it is not in the app. |
| "Model Readiness" table with the inputs each model needs | Same, live, with badges | Same. |

---

## Case 1 — Petrochemical plant, the two-model baseline

**Say.** "The simplest path. Archetype, location, a rough size and a capacity. Two
independent models fire, the analogue one and the onshore calculator, and the ensemble
sits between them."

**Do.**

| Field | Select / type |
|---|---|
| Archetype | **Petrochemical (onshore)** |
| Location (CP30 region) | **US Gulf Coast** |
| Basis year | **2024** (already selected) |
| Scope type | **Greenfield** |
| Rough size | **Substantial ($500M to $1,000M)** |
| Project name | `Demo polypropylene` |
| Facility type | **polypropylene** |
| Primary capacity | `450` |
| Unit | **KTA** |

Before pressing Run, point at **Model readiness**: Benchmark (analogues) *Ready*, Onshore
calculator *Ready*, OSBL overlay (indirect) *Ready automatic*, Equipment vector *Needs at
least one equipment item*, Composite (scope chips) *Needs at least one scope item*.

Press **Run screening estimate**.

**See.**

- Three KPI cards: **Best estimate (P50)**, **Range (P20 to P80)**, **Confidence**
  (MEDIUM-HIGH or HIGH), with the ensemble reasoning in a caption under them.
- A caption *Other analogue variant, Reference (analogue_estimator v3): $…* telling what
  David's own analogue model would have given for the same inputs.
- **Model estimates**: a bar per model with its own range as whiskers, the ensemble P50 as
  a dashed line, one tab per model. Open the **Onshore calculator** tab: the ISBL
  correlation used (polypropylene, 136 $M at 450 KTA), the EMMA index (414 for US Gulf
  Coast, factor 2.05), the TEC multiplier 2.58 for greenfield, 6% escalation, the
  calibration note (back-solved from one project, "circular"). Open **Benchmark
  (analogues)**: the variant, the size signal used (*size_bucket*, $700M), the ten
  analogues with their similarity.
- **Comparable projects**: the ten nearest pool projects with cost, match, country, capacity.
- **Bid check**, **What-if**, **Download HTML report** below.

**Say.** "Note the OSBL overlay: it ran automatically because the onshore calculator
produced an ISBL, and it is shown as an indirect line, not added to the median."

**Wireframe check.**

| Wireframe / brief | App | Why |
|---|---|---|
| Benchmark needs archetype + location + year; "size provided" improves it | Benchmark fires from archetype + location; **Rough size** is the size input | The reference analogue model takes a size bucket, not a cost. Year defaults to 2024, the pool's basis. |
| "No user-entered cost input" | Kept. Rough size is an order of magnitude, never a number | Same rule. |
| Brief, step 1: Benchmark "if size provided" | Benchmark fires without a size, better with one | The reference code fires without a size (cosine on categories). We measured why the size matters: see the accuracy section. |
| OSBL "runs automatically when any model fires" | Runs when there is an ISBL, i.e. when the onshore calculator fires | That is what `cost_bot_api` does; the brief's sentence is looser than the code. |
| One analogue model | Two selectable variants: David's port (Reference) and the first build's size-band variant (Engine), default Engine | Measured on the real data: equal without a size, the Engine variant ahead with one (63% vs 44%). The other variant's number is always shown. |

---

## Case 2 — Refinery brownfield, the exclusion and David's "scope is the equipment list"

**Say.** "Brownfield refinery work is where the onshore calculator overshoots, so the API
excludes it for this archetype. Your directive was that for brownfield the scope *is* the
equipment list, so let's give it one."

**Do.** Press **Reset**, then:

| Field | Select / type |
|---|---|
| Archetype | **Refinery brownfield** |
| Location (CP30 region) | **US Gulf Coast** |
| Scope type | **Modification** |
| Rough size | **Moderate ($75M to $200M)** |
| Facility type | **hydrotreater** |
| Primary capacity | `40000` |
| Unit | **BPD** |

Point at **Model readiness**: Onshore calculator shows the red badge **Excluded for this
archetype**. Press **Run screening estimate** once, show the result (Benchmark only).

Then, in **Equipment list**, add one at a time (type, count, **Add**; the card refreshes
alone, the page does not reload):

| Equipment type | Count |
|---|---:|
| exchanger | 6 |
| pump | 8 |
| tower | 1 |
| drum | 3 |
| compressor | 1 |

Readiness now shows Equipment vector *Ready*. Press **Run screening estimate** again.

Optional: in **Scope items** add Scope item type **process_unit**, Facility name
`Hydrotreater revamp`, **Add**; run again to light up Composite (scope chips).

**See.**

- First run: Benchmark alone, confidence LOW, the exclusion listed in the model
  status.
- Second run: Equipment vector appears with the five closest equipment profiles in its tab;
  the ensemble now combines two models; confidence goes up a tier.
- Third run (optional): Composite appears with the chips it matched per scope item.

**Wireframe check.**

| Wireframe / brief | App | Why |
|---|---|---|
| Brief: `refinery_bf` excludes Calculator_Onshore (7x overshoot) | Same, visible before the run as a red badge | Rule copied from `cost_bot_api`. |
| Brief: EquipmentVector is the best broad model, needs equipment list + archetype | Same card, same gate (at least two process items; valves and instruments are zeroed) | Same rule. |
| Wireframe: Composite builds the project from scope items (Process Unit, OSBL, Pipeline Segment) | Same card and item types | Kept from the wireframe. The reference Composite in the harness sums the project's own cost rows; the app matches scope items against the chip library, which is what a new project allows. |
| Wireframe: Bottom-Up "Class 2", A.1 Calculator Plus (ADR) | Not present | ADR data and `generative_estimator.py` were removed from the Sep 16 package. |

---

## Case 3 — Offshore FPSO, the calculator plus the subsea component

**Say.** "Offshore: the benchmark is excluded for FPSOs, the offshore calculator works from
topsides weight, and the SURF model prices the subsea scope as a separate component."

**Do.** Press **Reset**, then:

| Field | Select / type |
|---|---|
| Archetype | **Offshore FPSO** |
| Location (CP30 region) | **Guyana** |
| Scope type | **Greenfield** |
| Rough size | **Very large ($2,500M to $5,000M)** |
| Topsides weight (t) | `25000` |
| Water depth (m) | `1800` |
| Hull type | **Fpso newbuild** |

In **Subsea scope (SURF)**: Subsea trees `12`, Flowlines `6`, Risers `4`, Manifolds `2`,
Umbilicals `3`. Press **Run screening estimate**.

**See.**

- Readiness: Benchmark **Excluded for this archetype**, Offshore calculator *Ready*, SURF
  subsea (component) *Ready*.
- Results: Offshore calculator as the TEC estimate; SURF in the *Component* colour with its
  own tab (flowlines, risers, umbilicals, trees, installation); the SURF value is **not** in
  the P50.
- If you clear the topsides weight and run again, the confidence becomes
  **COMPONENT_ONLY**: a subsea cost exists, a total does not. Say that out loud; it is the
  rule from the brief.

**Wireframe check.**

| Wireframe / brief | App | Why |
|---|---|---|
| Brief: SURF_User needs well count + water depth + topsides weight | App asks for trees, flowlines, risers, manifolds, umbilicals and reads water depth from the facility card | The SURF reference file (`surf_estimator.py`) has not been shared yet; the card follows the Sep 15 brief's description. Will be aligned when the file arrives. |
| Brief: COMPONENT_ONLY when SURF fires alone | Same | Same rule. |
| Brief: `offshore_fpso` excludes Benchmark | Same | Same rule. The ensemble leans on the calculator and, with an equipment list, on the equipment vector. |
| Offshore calculator with EMMA location factor | EMMA disabled for offshore | The rate tables are already in 2024 USD; applying EMMA again double-counted (golden cases Payara, Liza, Jacket). Documented divergence. |

---

## Case 4 — Pipeline, the unverified calculator

**Say.** "Pipelines are the weak spot in the brief itself: the calculator is marked
unverified because the truth values disagree between sources. The app says so on screen."

**Do.** Press **Reset**, then:

| Field | Select / type |
|---|---|
| Archetype | **Pipeline (mainline)** |
| Location (CP30 region) | **US Gulf Coast** |
| Scope type | **Greenfield** |
| Rough size | **Medium ($200M to $500M)** |
| Length (km) | `200` |
| Diameter (in) | `24` |

Press **Run screening estimate**.

**See.**

- Readiness: Pipeline calculator *Ready*, Benchmark *Ready*.
- A yellow warning from the pipeline calculator that it is unverified.
- Pipeline calculator tab: linepipe material, mainline construction, crossings, stations,
  engineering, contingency.

**Wireframe check.**

| Brief | App | Why |
|---|---|---|
| Pipeline: 67% ±30% (N=3), UNVERIFIED | Same warning, shown as a flag | Carried over as is. `pipeline_calculator_v2.py` not yet shared, so the internals are the first build's; the input mapping follows the API. |

---

## Case 5 — Onshore unconventional, the lookup model

**Say.** "For short-cycle unconventional work there is a dedicated lookup by facility type,
and it was the most accurate family on the real data."

**Do.** Press **Reset**, then:

| Field | Select / type |
|---|---|
| Archetype | **Onshore unconventional** |
| Location (CP30 region) | **New Mexico** |
| Scope type | **Expansion** |
| Facility type | **compressor_station** |
| Primary capacity | `70` |
| Unit | **MMSCFD** |

Press **Run screening estimate**.

**See.**

- Readiness: Benchmark **Excluded**, Onshore calculator *Ready*, Unconventional lookup
  *Ready*, OSBL overlay *Ready*.
- Unconventional lookup tab: the peers used and the capacity interpolation between them.
- Onshore calculator tab: the correlation `compressor_station` (back-solved from one
  project; the calibration note says so).

**Wireframe check.**

| Brief | App | Why |
|---|---|---|
| Unconventional: facility-type lookup, 70% ±30% (N=10); `onshore_unconventional` excludes Benchmark | Same routing and exclusion; capacity-aware interpolation as in `cost_bot_api` | Same. Measured on the real data: 7 of 11 within ±30%, 8 of 11 with the ensemble. |

---

## Case 6 — Basis year, bid check, what-if, report (any case)

**Do.** On the last result, change **Basis year** to **2026** and run again.

**See.** A caption *Pool-based estimates escalated from 2024 to 2026 USD (CP30 factor
1.2019; +20.2%)*. Say: "Pool numbers are 2024 dollars; other years use the CP30 index at
the Gulf Coast. 2025 is the last index in the table, 2026 is extrapolated."

**Do.** In **Bid check** enter a bid amount (for case 1, `700`), keep **TEC**, press
**Check bid**. Then in **What-if** pick **Primary capacity**, type a new value (for case 1,
`600`), press **Run what-if**.

**See.** Bid check: *Within range*, *Above range* or *Below range* with the distance to the
bound. What-if: three cards (base P50, what-if P50 with the delta, the parameter) and a
per-model table of base vs what-if.

**Do.** Press **Download HTML report**; open the file.

**See.** One page: the scope, the three KPIs, flags (including which analogue variant was
used and what the other gives), the model chart, status table, analogues, disclaimer.

**Wireframe check.**

| Wireframe / brief | App | Why |
|---|---|---|
| Not in the wireframe | Bid check, What-if, HTML report | Added in the first build for gate-review use. Bid check applies the API's EPC lump-sum adjustment. |
| Basis year as a core input | Buttons 2024 / 2025 / 2026, default 2024 | Same input; CP30 to 2026 is an extrapolation, flagged on screen. |

---

## 7. Models and Data pages (2 minutes)

**Do.** Open **Models**. Three tabs: **Model specs** (one card per model: method, badge,
algorithm, measured accuracy, libraries), **Routing and inputs** (which models each
archetype can use, the exclusions, the input to model table, the ensemble rules in plain
words), **Reported accuracy** (the brief's per-archetype table next to the figures measured
on this engine).

**Do.** Open **Data**: the loaded tables with live row counts and which model reads each
one, a preview, and the pool by archetype.

**Say.** "Everything is traceable: the table, the row, the correlation, the rule."

**Wireframe check.**

| Wireframe | App | Why |
|---|---|---|
| Data Package page with the manifest (CET rate CSVs, 74-row pool, gate tables) | Data page with the tables actually in the Sep 16 package (503-row pool, 593 equipment vectors, 857 chips, 377 semantic chips, 41 scope inputs) | The Sep 16 package replaced the manifest. |
| Model Specs with LOOCV figures per model | Same, with the figures measured on this engine added | See the next section. |

---

## 8. The accuracy conversation

This is the question that will come. Have the numbers ready; they are measured on the real
package, 52 truth projects, leave-one-out, and published in `docs/VALIDATION_2026-09-30.md`.

**Say.** "Your package reports 40 of 52 within ±30%. We reproduced your harness's
convention on this engine and measured the app's own number. They are different questions."

| What is measured | Result |
|---|---:|
| The app's single estimate (ensemble P50), no size given | 29% of 52 projects within ±30% |
| The app's single estimate, user gives a rough size | **63%** (refinery brownfield 14 of 17) |
| Your harness's convention (any single model within ±30% of any truth), without the oracle Composite | 48% of 50 projects |
| Your package's figure | 77% (40 of 52) |

**Why the gap, in three sentences.** Your harness counts a project as a hit when any one
model lands near the truth, with no ensemble. One of those models, the Composite with
`apply_oh=True`, corrects itself with the truth value; your own file calls that the oracle
ceiling. And the harness scores SURF against a subsea-only truth for four projects. None of
that exists for a project a user types in.

**What moves the number.** The user's rough size. It is a legitimate input and it takes
the app from 29% to 63%. Your own analogue model goes from 29% to 44% with it; the size
band variant we kept from the first build does better, which is why it is the default and
the other one is one click away.

**Where it is still zero.** Oil sands, LNG and integrated petchem: those depend on the
LNG and offshore calculator files and an oil-sands correlation that are not in the package
yet.

---

## 9. Questions you may get

| Question | Answer |
|---|---|
| "Is this calling my code?" | No. The app is a port, module by module, checked against your files: `cost_bot_api.py`, `analogue_estimator.py`, `onshore_calculator.py`, `evaluation_harness.py`. The golden cases match to the digit. Four files are still to come: SURF, OSBL, pipeline, LNG, offshore. |
| "Why two analogue models?" | Yours is the reference and is always shown. The variant adds a size band; measured on the real data it is ahead when a size is given. Your choice which stays. |
| "Why does brownfield show 2.61 and not 1.30?" | Because `cost_bot_api` sends BF-expansion for every brownfield scope; 1.30 is reached only when the facility name says modification or conversion. We ported it as is and flagged it. |
| "Why 10 models, not 9?" | The composite from the wireframe was kept; it is never routed by archetype, only when the user adds scope items. |
| "Can it run on Databricks?" | It is running on Databricks now, as an App, from flat files. |

---

## Glossary

| Term | Plain English |
|---|---|
| TEC | Total erected cost, the full installed cost |
| ISBL / OSBL | Inside / outside battery limits: process units versus utilities and offsites |
| EMMA | Location cost index (GOM 2000 = 202); factor = index / 202 |
| CP30 | Cost index by location and year used to bring every cost to 2024 USD |
| P50, P20, P80 | Median and the 20th / 80th percentile of the range |
| Spread gate | If the surviving models disagree by more than 3x, the furthest one is dropped |
| COMPONENT_ONLY | A subsea component cost exists but no total project cost |
| Class 5 | Screening estimate, ±50% target; not a basis of estimate |
