# Latest Requirement / Update Email

**Subject:** RE: Request for new streamlit  
**From:** McEvoy, T David  
**Date:** Wed 9/16/2026, 10:24 AM  
**To:** Pinto, Pedro /CS; Silva, Guilherme Oliveira /CS  
**Cc:** Perobelli, Giovanni /CS; Kumar, Lokesh; Chitturi, Prasanth; Cooke, Caroline  
**Attachment:** `streamlit_poc_package_2026-09-16.zip` (~6 MB)

---

Hey guys. Have a refresh on the data for this. Also cc'ing Prasanth who has joined my team from CSE, and keeping Caroline informed on our work.

Priority on this is going up, so let me know what we would have to move to do this sooner rather than later.

Attached is a refreshed data package for the Streamlit POC. Replaces the Aug 30 zip. Same structure (data + reference code + wireframe + task brief), but significant changes underneath.

## Data changes

- Analogue pool expanded from **100 to 503 entries** — all key fields now filled (process domain, scope type, capacity, archetype). This is the pool the screening models match against.
- Project truth table expanded from **42 to 53 test projects**.
- **6 new reference tables** added: `gate_costs` (1,687 cost breakdown rows across 58 projects), equipment vectors (593 entries), archetype taxonomy, semantic chip classifications, scope inputs, and **MAPI rate tables** (75K rows for location-adjusted pricing).

## Code changes

- The main entry point is now `cost_bot_api.py` (115KB) — a single callable wrapper with **9 model runners**. This is the interface the Streamlit app should call. It handles model routing, archetype detection, and result formatting.
- New model files added: `osbl_estimator.py` (offsites/utilities estimation), `unconventional_calculator.py`, `surf_calcplus_v2.py` (deepwater SURF), `analogue_estimator.py` (peer matching), `calculator_router.py`, `evaluation_harness.py`.
- Old deprecated code removed: parametric navigators (3 files), `frankenstein_orchestrator`, `overlay_stack`, `pad_configurator`, `generative_estimator`, and the full test suite (tested the old code, not applicable).
- `composite_estimator.py` substantially rewritten (**47KB → 99KB**) — now includes semantic hybrid matching.

## What hasn't changed

Wireframe, frankenstein chip library, CP30 normalization indices, equipment screening estimator, normalization service.

## Current accuracy

**Current accuracy (52 test projects): 40/52 within ±30% (77%).**

Strongest archetypes:

- refinery brownfield: **13/17**
- unconventional: **10/11**
- chemicals: **4/4**
- deepwater: **3/3**

Known gaps:

- pipeline: **2/5**
- oil sands: **1/3**
- LNG: **0/2**

The `README.html` in the zip is the updated task brief. Let me know if you have questions about the new API surface.
