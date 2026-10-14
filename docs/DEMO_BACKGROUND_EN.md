# Costbot — presenter's background (English)

**For:** Guilherme, before presenting. It explains the tool without assuming anything: what
each model does, how the opinions become one number, the terms, where it came from, the
measured accuracy and how it compares with the reported one, and what matches the
wireframe or not. The spoken demo text is in `docs/DEMO_SCRIPT.md`; the Portuguese version
of this material is `docs/DEMO_BACKGROUND.md`.

---

# PART 1 — Understand the tool before presenting

## 1.1 What it does, in one sentence

You describe a capital project with a few fields (project type, location, rough size,
capacity) and the tool tells you what it should cost, with an uncertainty range, and shows
the similar past projects that support the number. It is a screening estimate (Class 5),
meant to decide whether a project is worth pursuing, not to budget it.

## 1.2 How it gets to the number: the table of experts

Picture a table with ten experts. Each has their own way of estimating. Each one only
speaks up when the data their method needs is present. In the end, the tool takes the
opinions that showed up, discards anyone far out of line, and keeps the median.

The ten, with the name shown on screen:

| On screen | What it does, in one sentence | What it needs | How it behaves |
|---|---|---|---|
| **Benchmark (analogues)** | Searches 503 past projects for the most similar ones and uses their cost. "What did it cost the last time we did something like this." | Project type and location. Much better with a rough size. | Without a size it is weak; with a size it is the model that helps most. |
| **Equipment vector** | Compares your equipment list with the lists of 593 projects. "Tell me what's inside and I'll find the project with the same recipe." | An equipment list with counts (at least two process items: pumps, exchangers, towers...). | Called the "best broad model" in the original brief. |
| **Onshore calculator** | Engineering formula: reference cost × (capacity / reference capacity)^0.6, adjusted by a location index, times a multiplier that takes it to total cost. | Facility type and capacity. | Good for new plants; overshoots badly on refinery modifications, so it is switched off there. |
| **Offshore calculator** | Estimates from the topsides weight (the top part of the platform). | Topsides weight or production in KBPD, water depth, hull type. | Calibrated on two projects only; handle with care. |
| **Pipeline calculator** | Diameter × length, section by section: pipe, construction, crossings, stations. | Length and diameter. | Marked "unverified" in the original brief; the app shows a warning. |
| **LNG calculator** | Equations per subsystem of an LNG plant. | Capacity in MTPA. | Known to be miscalibrated and out of the November scope. |
| **Unconventional lookup** | Table of unconventional projects by facility type (compressor station, delivery point...), interpolating by capacity. | Facility type. | The most accurate family on the real data. |
| **Composite (scope chips)** | Builds the project from pieces (a process unit, a utilities package, a pipeline segment) and adds up the cost of each piece, found in a library of 857 cost "chips". | At least one scope item. | Came from the wireframe; the September brief does not list it. |
| **SURF subsea (component)** | Cost of the subsea system: trees, flowlines, risers, manifolds, umbilicals. | Trees or flowlines, water depth. | A component: it stays out of the median, shown beside it. |
| **OSBL overlay (indirect)** | Utilities and offsites as a proportion of the process units' cost. | Runs by itself when the onshore calculator produces an ISBL. | Also stays out of the median. |

## 1.3 How the opinions become one number: the ensemble

The rules the app applies, copied from the reference `cost_bot_api`:

1. Only total-cost models enter. SURF and OSBL are shown beside the total, never in the
   median.
2. **Spread gate:** while the highest and the lowest surviving estimates differ by more
   than 3 times, the one furthest from the median is dropped. No model outranks another.
3. **Best estimate (P50)** = median of the survivors.
4. **Range (P20 to P80)** = from the lowest "low" to the highest "high" among the models'
   own ranges, each bound limited to 5 times the median.
5. **Confidence:** HIGH when 3 or more survivors sit within ±30% of the median; MEDIUM-HIGH
   when 2 do; MEDIUM when 2 or more survive but disagree; LOW with a single model;
   COMPONENT_ONLY when only SURF ran (there is a subsea cost, no total).
6. Projects below US$ 20 million get a note: they are below the screening floor.

When a model is dropped, the screen says "Gated out of the ensemble" and why.

## 1.4 The terms that will come up

| Term | In plain words |
|---|---|
| **TEC** | Total erected cost: the full installed cost of the project. The number the app estimates. |
| **ISBL / OSBL** | Inside / outside battery limits: the process units versus utilities and offsites. |
| **P50, P20, P80** | The median and the 20th / 80th percentiles of the range. "P80 = an 80% chance it costs less than this." |
| **Class 5** | Screening estimate, ±50% target. Not a basis for a budget. |
| **Archetype** | The project type (refinery brownfield, FPSO, pipeline...). It decides which models can run. |
| **CP30** | Cost index by location and year. Every cost is brought to 2024 dollars with it. |
| **EMMA** | Location cost index used by the calculators. Gulf Coast = 414; the GOM 2000 base = 202; the factor is 414 / 202 = 2.05. |
| **Analogues** | The similar projects the Benchmark used. Shown under "Comparable projects". |
| **Greenfield / brownfield** | A new plant on new ground / work on an existing plant. Expansion and modification are kinds of brownfield. |
| **Rough size** | Your order of magnitude for the project: "between 500 million and 1 billion". Not a cost; a band. |
| **LOOCV** | How accuracy was measured: for each project with a known cost, hide it from the data, estimate it, compare with the actual cost. |

## 1.5 Where it came from and what was done

- On September 16 the package arrived: data (503 projects, 593 equipment vectors, 857
  chips, 53 actual-cost rows), the reference code and the brief.
- The models were rebuilt in our own code, module by module, and checked against the
  reference files shared so far: `cost_bot_api.py`, `analogue_estimator.py`,
  `onshore_calculator.py`, `evaluation_harness.py`. The 25 onshore "golden" test cases
  from the package give the same number in our code, to the digit.
- The app runs on Databricks as an App, reading CSV files. No AI, no database.
- Five reference files are still missing to complete the parity: SURF, OSBL, pipeline,
  LNG and offshore. Until then those models follow the first version, with inputs in the
  `cost_bot_api` format.

## 1.6 Accuracy, so you can answer

**How it was measured.** Take the 52 projects whose actual cost is known. For each one,
hide it from the data, run the tool as a user would, and compare. "Hit" means the
estimate landed within ±30% of the actual cost.

**The figures (real data, September 30):**

| What was measured | Result |
|---|---:|
| The number the app shows (P50), with no size given | 29% of projects (15 of 52) |
| The number the app shows, with the rough size given | **63%** (33 of 52); refinery brownfield 14 of 17 |
| The reference harness's own convention, without the model that reads the answer | 48% (24 of 50) |
| The figure reported in the brief | 77% (40 of 52) |

**Why the brief says 77% and we get 48% on the same convention.** Three reasons, in plain
words:

1. That convention counts a project as a hit if **any** single model, on its own, landed
   close. It is not one final number; it is "one of the ten got it". The app gives one
   number.
2. One of those models, the Composite, corrects itself with the project's actual cost. The
   reference code itself calls that an "oracle ceiling". It does not exist for a new project
   someone types in.
3. SURF is scored against a subsea-only cost, for four projects.

**What moves the result most:** the rough size given by the user. It takes the app from
29% to 63%. It is a legitimate input: whoever does screening knows whether the project is
50 or 500 million.

**Where it is still zero:** oil sands, LNG and integrated petchem. They depend on the LNG
and offshore calculators, whose files have not arrived, and on an oil sands correlation.

## 1.7 What matches the wireframe and what does not

| In the wireframe (August) | In the app | Why |
|---|---|---|
| Five pages: Estimator, Data Package, Code Inventory, Dependencies, Model Specs | Three: Estimator, Models, Data | "Code Inventory" listed files the September package removed. "Dependencies" and "Model Specs" became tabs of the Models page. |
| Models named A, A.1, B, B.1, Bottom-Up | The nine names from the September 15 brief, plus the Composite | The brief renamed the models. A.1 "Calculator Plus (ADR)" left the package, so it does not exist in the app. |
| Benchmark needs type + location + year; "size, if provided" | Benchmark runs with type + location; the size is the "Rough size" field | The reference code takes a size band, not a cost. The year defaults to 2024. |
| "No cost input from the user" | Kept. "Rough size" is an order of magnitude, never a number | Same rule. |
| Composite builds the project from scope items | Same card, same item types | Kept from the wireframe. |
| OSBL "runs whenever any model runs" | Runs when there is an ISBL, that is, when the onshore calculator ran | That is what `cost_bot_api` does. The brief's sentence is looser than the code. |
| One analogue model | Two, selectable: the reference one and our variant with a size band, which is the default | On the real data they tie without a size; with a size the variant hits more (63% against 44%). The app always shows what the other would give. |
| Offshore calculator with the EMMA location factor | EMMA switched off offshore | The rate tables are already in 2024 dollars; applying EMMA again doubled the adjustment. Documented. |
| Not there | Bid check, What-if, HTML report | Added in the first build for gate-review use. |
| "Data Package" page with a 74-project manifest | Data page with the real tables of the September package (503 projects etc.) | The September package replaced the manifest. |

---

# PART 2 — Likely questions and answers

| Question | Answer |
|---|---|
| "Is this the original code running?" | No. It is a rewrite, module by module, checked against the reference files. The golden cases match to the digit. Five reference files are still to come: SURF, OSBL, pipeline, LNG and offshore. |
| "Why two analogue models?" | The reference one is always shown. The variant filters by size band; on the real data it hits more when a size is given. Which one stays as default is a team decision. |
| "Why 10 models and not 9?" | The composite from the wireframe was kept. It is never chosen by the archetype; it only runs when the user adds scope items. |
| "Why does brownfield use 2.61?" | Because `cost_bot_api` sends BF-expansion for any brownfield; 1.30 only when the facility name says modification or conversion. Copied as is, flagged. |
| "What about oil sands, LNG, integrated petchem?" | Still zero in every configuration. They depend on the LNG and offshore files and on an oil sands correlation. |
| "Why is EMMA off for offshore?" | The offshore rate tables are already in 2024 dollars; applying EMMA again doubled the adjustment. The Payara, Liza and Jacket golden cases show it. |
| "Does it run on Databricks?" | It is running now, as an App, from flat files. |
| "What is the confidence?" | How many models agree. HIGH: three or more within ±30% of the median. MEDIUM-HIGH: two. MEDIUM: two or more, disagreeing. LOW: a single one. |
| "What happens when the models disagree a lot?" | While the highest and lowest differ by more than 3x, the one furthest from the median is dropped, and the screen says which and why. |
| "Can I type the cost I think it is?" | No. The rule is no cost input. "Rough size" is an order of magnitude. |
