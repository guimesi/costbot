"""Code Inventory page: reference modules (not shipped) and exclusions."""
import pandas as pd
import streamlit as st

st.markdown("### Production Python Modules")
st.caption("Reference implementation. Contractor uses as specification + validation reference.")

modules = [
    {"Module": "cost_bot_api.py", "Lines": "2,484", "Model": "API Wrapper",
     "Description": "Main entry point - routes scope -> 9 model runners -> structured results"},
    {"Module": "analogue_estimator.py", "Lines": "1,526", "Model": "Benchmark (B)",
     "Description": "Cosine similarity analogue matching. CP30 normalization. P20/P50/P80."},
    {"Module": "composite_estimator.py", "Lines": "2,229", "Model": "Composite (B.1)",
     "Description": "Semantic hybrid chip matching. Gate cost breakdowns."},
    {"Module": "onshore_calculator.py", "Lines": "1,433", "Model": "Calculator (Onshore)",
     "Description": "Six-tenths scaling correlations. ISBL -> EMMA -> TEC chain."},
    {"Module": "offshore_calculator.py", "Lines": "1,009", "Model": "Calculator (Offshore)",
     "Description": "Topsides weight curves + hull parametric. Depth modules."},
    {"Module": "pipeline_calculator_v2.py", "Lines": "687", "Model": "Calculator (Pipeline)",
     "Description": "MAG pricing + labor + equipment + facilities + indirects."},
    {"Module": "lng_calculator.py", "Lines": "565", "Model": "Calculator (LNG)",
     "Description": "A42 CET subsystem regressions + location rates."},
    {"Module": "unconventional_calculator.py", "Lines": "102", "Model": "Unconventional",
     "Description": "Facility-type median lookup for short-cycle projects."},
    {"Module": "surf_estimator.py", "Lines": "1,227", "Model": "SURF",
     "Description": "Subsea equipment bottom-up: flowlines, risers, umbilicals, trees."},
    {"Module": "surf_calcplus_v2.py", "Lines": "90", "Model": "SURF CalcPlus",
     "Description": "Calibration wrapper over surf_estimator (4/4 LOOCV ±30%)."},
    {"Module": "osbl_estimator.py", "Lines": "1,002", "Model": "OSBL CalcPlus",
     "Description": "3-layer indirect cost overlay: heritage + IC library + absolute."},
    {"Module": "equipment_screening_estimator.py", "Lines": "563", "Model": "Equipment",
     "Description": "Equipment list -> chip matching -> EMMA -> TEC."},
    {"Module": "normalization_service.py", "Lines": "558", "Model": "Shared",
     "Description": "Location/time normalization via CP-30 indices."},
    {"Module": "calculator_router.py", "Lines": "792", "Model": "Router",
     "Description": "Facility type -> calculator lane classification + calibration."},
    {"Module": "model_router.py", "Lines": "1,291", "Model": "Router",
     "Description": "Archetype -> model eligibility routing."},
    {"Module": "evaluation_harness.py", "Lines": "2,330", "Model": "Evaluation",
     "Description": "Canonical LOOCV evaluation framework for all models."},
]

st.dataframe(
    pd.DataFrame(modules),
    width='stretch',
    hide_index=True,
    column_config={
        "Module": st.column_config.TextColumn(width="medium"),
        "Lines": st.column_config.TextColumn(width="small"),
        "Model": st.column_config.TextColumn(width="medium"),
        "Description": st.column_config.TextColumn(width="large"),
    },
)

st.markdown("---")
st.markdown("### Excluded (Not Needed for POC)")
st.markdown("""
- **LLM persona files** (`SKILL.md`, cost-buddy, cost-skeptic, etc.) - no chatbot in POC
- **Screening v3 notebooks** - stale, references contaminated tables
- **Deprecated orchestrators** - frankenstein_orchestrator, parametric navigators, overlay_stack
""")
