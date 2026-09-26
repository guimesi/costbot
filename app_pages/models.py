"""Models page: what each model does, how inputs route to models, reported accuracy."""
import pandas as pd
import streamlit as st

from costbot.constants import ARCHETYPE_EXCLUSIONS, ARCHETYPE_MODELS
from ui.common import ARCHETYPE_LABELS, model_label

SPECS = [
    ('Benchmark', 'Analogue matching', ':blue-badge[Broad]',
     "One-hot encoding of domain, scope type, region, on/offshore and facility class, cosine similarity "
     "against the 503-project pool, blended 50/50 with a size signal. P20/P50/P80 from the top analogues.",
     "Reported: regression under investigation in the Sep 15 brief.", "numpy, pandas, scikit-learn"),
    ('EquipmentVector', 'Equipment composition', ':green-badge[Best broad model]',
     "52-dimension vector of equipment counts, process equipment only (valves, instruments, electrical zeroed), "
     "L2-normalised cosine similarity against 593 project vectors, similarity-weighted top 5.",
     "66% within ±30% (N=29)", "numpy"),
    ('Calculator_Onshore', 'Six-tenths scaling', ':blue-badge[Calculator]',
     "ISBL = base × (capacity / reference)^0.6 for 18+ facility types, EMMA location factor, "
     "ISBL to TEC multiplier by scope type, 6% escalation, AACE class 5 range.",
     "79% within ±30% (N=14). Excluded for refinery brownfield (7x overshoot).", "pure Python"),
    ('Calculator_Offshore', 'Topsides weight curves', ':blue-badge[Calculator]',
     "Topsides weight (given or from production rate) × $/t by hull type, parametric hull, subsea and SURF "
     "allowances, transport, engineering, owner's cost, 20% contingency. EMMA disabled on purpose.",
     "50% within ±30% (N=2)", "pure Python"),
    ('Calculator_Pipeline', 'Section decomposition', ':orange-badge[Unverified]',
     "Linepipe material, mainline construction by diameter, HDD crossings, MLV and pump stations, metering, "
     "engineering and survey, 20% contingency, location and congestion factors.",
     "67% within ±30% (N=3), truth values disputed between sources.", "pure Python"),
    ('Calculator_LNG', 'CET subsystem regressions', ':red-badge[Miscalibrated]',
     "Per-train material regressions for treating, liquefaction, power, offsites and marine, times a 3.1 "
     "loading factor and a location factor.",
     "0% within ±30%. Directional only; not in November scope.", "pure Python"),
    ('Unconventional', 'Facility-type lookup', ':blue-badge[Archetype-specific]',
     "Median TEC of pool projects with the same facility type (CDP, cold separation train, cryo plant, pad, "
     "pipeline). Authoritative for the unconventional archetype in the ensemble.",
     "70% within ±30% (N=10)", "numpy, pandas"),
    ('Composite', 'Scope chip matching', ':gray-badge[Low accuracy]',
     "Each scope item is matched against the 857-chip library with a 5-tier keyword and synonym scorer, "
     "IQR outliers removed, medians summed across items.",
     "26% within ±30% overall, 50% for refinery brownfield", "pandas"),
    ('SURF_User', 'Subsea bottom-up', ':green-badge[Component]',
     "Trees, flowlines, risers, manifolds and umbilicals at heritage unit prices × 1.34 calibration. "
     "Reported as a separate component, never added to the total.",
     "4 of 4 within ±30% on the Guyana deepwater set", "pure Python"),
    ('OSBL_Estimate', 'Indirect cost overlay', ':green-badge[Automatic]',
     "Three layers on top of an ISBL: heritage percentage by scope type, IC Library parametric sub-curves "
     "(power, steam, storage, loading) and an absolute cost chain, blended.",
     "8% average error (N=4)", "pure Python"),
]

DEPENDENCIES = [
    ("Archetype", "All models", "-"),
    ("Location", "All (EMMA, analogue region)", "-"),
    ("Basis year", "All (CP30 escalation of pool estimates)", "-"),
    ("Scope type", "-", "Onshore calculator multiplier, benchmark, OSBL"),
    ("Equipment list", "Equipment vector", "-"),
    ("Facility type", "Onshore calculator, unconventional", "Benchmark"),
    ("Primary capacity", "Onshore and LNG calculators", "Benchmark size signal, OSBL"),
    ("Pipeline length + diameter", "Pipeline calculator", "-"),
    ("Topsides weight or production", "Offshore calculator", "-"),
    ("Subsea trees / flowlines", "SURF component", "-"),
    ("Scope items", "Composite", "-"),
]

ACCURACY = [
    ("Chemicals", 4, 4), ("Deepwater", 3, 3), ("CCS", 2, 2), ("Unconventional", 10, 11),
    ("Refinery brownfield", 13, 17), ("Pipeline", 2, 5), ("Oil sands", 1, 3), ("LNG", 0, 2),
]

tab_specs, tab_routing, tab_accuracy = st.tabs(["Model specs", "Routing and inputs", "Reported accuracy"])

with tab_specs:
    st.caption("Ten deterministic models. Each fires only when its inputs are present; the ensemble "
               "mediates between the total-cost models with a 3x spread gate and priority rules.")
    cols = st.columns(2, gap="medium")
    for i, (mid, method, badge, algo, acc, libs) in enumerate(SPECS):
        with cols[i % 2].container(border=True):
            st.markdown(f"**{model_label(mid)}** {badge}")
            st.caption(f"{method} · `{mid}`")
            st.markdown(algo)
            st.markdown(f":material/target: {acc}")
            st.caption(f"Libraries: {libs}")

with tab_routing:
    st.markdown("**Which models each archetype can use**")
    st.caption("Equipment vector, composite and SURF are added whenever their inputs exist. "
               "The OSBL overlay follows the onshore calculator.")
    routing = pd.DataFrame([{
        'Archetype': ARCHETYPE_LABELS.get(a, a),
        'Models': ', '.join(model_label(m) for m in ms),
        'Excluded': ', '.join(model_label(m) for m in ARCHETYPE_EXCLUSIONS.get(a, [])) or '',
    } for a, ms in ARCHETYPE_MODELS.items()])
    st.dataframe(routing, hide_index=True)

    st.markdown("**Input to model dependencies**")
    st.dataframe(pd.DataFrame(DEPENDENCIES, columns=['Input', 'Required by', 'Improves']), hide_index=True)

    st.markdown("**Ensemble rules**")
    st.markdown("""
- Component (SURF) and indirect (OSBL) estimates never enter the median.
- If the surviving models disagree by more than 3x, the lowest-priority model furthest from the median is removed. Calculators outrank analogue models; the unconventional lookup outranks everything for its archetype.
- Two survivors that are the onshore calculator and the benchmark, more than 1.5x apart, are blended with a geometric mean.
- The final range is the widest span of the survivors' ranges, capped at 5x around the median.
- Projects below $20M are flagged as outside the screening floor.
""")

with tab_accuracy:
    st.warning("These figures come from the reference evaluation in the Sep 16 brief and the first build. "
               "They have not been reproduced on this engine yet; run `scripts/evaluate_truth.py` on the real "
               "data package to refresh them.", icon=":material/science:")
    df = pd.DataFrame([{'Archetype': a, 'Within ±30%': f"{h}/{n}", 'Hit rate': h / n} for a, h, n in ACCURACY])
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        st.dataframe(df, hide_index=True, column_config={
            'Hit rate': st.column_config.ProgressColumn('Hit rate', min_value=0, max_value=1, format='%.0f%%')})
        total_h, total_n = sum(h for _, h, _ in ACCURACY), sum(n for _, _, n in ACCURACY)
        st.metric("Reference overall", f"{total_h}/{total_n} ({total_h / total_n * 100:.0f}%)", border=True,
                  help="Sep 16 brief: 40/52 (77%) at ±30%.")
    with c2:
        chart_df = df.set_index('Archetype')[['Hit rate']] * 100
        st.bar_chart(chart_df, horizontal=True, x_label="", y_label="")
