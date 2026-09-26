"""Models page: what each model does, how inputs route to models, reported accuracy."""
import pandas as pd
import streamlit as st

from costbot.constants import ARCHETYPE_EXCLUSIONS, ARCHETYPE_MODELS
from costbot.labels import ARCHETYPE_LABELS, ENSEMBLE_RULES, MODEL_SPECS, model_label

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
    # Row by row so the two cards of a row share the same height (height="stretch")
    for row_start in range(0, len(MODEL_SPECS), 2):
        cols = st.columns(2, gap="medium")
        for col, (mid, method, badge, colour, algo, acc, libs) in zip(cols, MODEL_SPECS[row_start:row_start + 2]):
            with col.container(border=True, height="stretch"):
                st.markdown(f"**{model_label(mid)}** :{colour}-badge[{badge}]")
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
    st.markdown('\n'.join(f"- {r}" for r in ENSEMBLE_RULES).replace('$', '\\$'))

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
