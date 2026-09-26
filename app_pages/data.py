"""Data page: what is loaded, from where, and a preview of every table."""
import pandas as pd
import streamlit as st

from ui.common import data_is_mock, load_data

data = load_data()

TABLES = [
    ("ref_are_analogue_pool_v3", data.pool, "Benchmark, unconventional, analogues", "Completed projects with CP30-normalised TEC and the 2D taxonomy"),
    ("ref_equipment_vectors", data.equipment_vectors, "Equipment vector", "52-dimension equipment composition per project"),
    ("frankenstein", data.frankenstein, "Composite", "Scope chip library with direct costs"),
    ("ref_semantic_chip_classifications", data.semantic_chips, "Composite", "Chip to archetype classification"),
    ("project_truth", data.truth, "Evaluation only", "Verified actual costs for accuracy testing"),
    ("gate_costs", data.gate_costs, "Not used at runtime", "Gate package cost breakdowns"),
    ("ref_project_scope_inputs_v2", data.scope_inputs, "Not used at runtime", "Scope inputs for key projects"),
    ("ref_cp30_combined_indices", data.cp30, "All (escalation)", "CP30 location and time indices"),
    ("ref_country_to_cp30_location", data.country_to_cp30, "Reference", "Country to CP30 location"),
    ("ref_archetype_taxonomy", data.archetype_taxonomy, "Reference", "Canonical process domain × scope type taxonomy"),
]

if data_is_mock(data):
    st.warning("This is the synthetic data package shipped with the repo. Row counts and columns match the real "
               "package; values are random. Point `COSTBOT_DATA_DIR` at the real package to use it.",
               icon=":material/science:")
st.caption(f"Data directory: `{data.data_dir}`")

with st.container(border=True):
    st.markdown("**:material/inventory_2: Loaded tables**")
    manifest = pd.DataFrame([{'Table': n, 'Rows': len(df), 'Columns': df.shape[1], 'Used by': u, 'Description': d}
                             for n, df, u, d in TABLES])
    st.dataframe(manifest, hide_index=True, column_config={
        'Rows': st.column_config.NumberColumn(format='%d'), 'Columns': st.column_config.NumberColumn(format='%d')})

c1, c2 = st.columns([3, 2], gap="large")
with c1:
    with st.container(border=True):
        st.markdown("**:material/table_view: Preview**")
        name = st.selectbox("Table", [t[0] for t in TABLES], key="preview_table", label_visibility="collapsed")
        df = next(t[1] for t in TABLES if t[0] == name)
        if df.empty:
            st.caption("Table not found or empty.")
        else:
            st.dataframe(df.head(50), hide_index=True, height=420)
with c2:
    with st.container(border=True):
        st.markdown("**:material/donut_small: Analogue pool by archetype**")
        if not data.pool.empty and 'archetype' in data.pool.columns:
            counts = data.pool['archetype'].value_counts().rename('Projects')
            st.bar_chart(counts, horizontal=True, x_label="", y_label="")
        else:
            st.caption("Pool not loaded.")
