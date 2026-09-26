"""Data Package page: manifest, preview and pool distribution."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.common import load_data

data = load_data()

st.markdown("### Data Package Manifest")
st.caption("Reference data loaded from CSV. Counts reflect loaded files. "
           "CET rate tables (36 CSVs) are not part of this package; calculator rates are embedded in engine.py.")

manifest = [
    {"Table": "ref_are_analogue_pool_v3", "Rows": len(data.pool), "Models": "Benchmark, EquipmentVector", "Description": "Clean analogue corpus, CP30-normalized (503 projects)", "Refresh": "Ad-hoc"},
    {"Table": "project_truth", "Rows": len(data.truth), "Models": "Evaluation", "Description": "Verdict: excludes + archetype labels (53 projects)", "Refresh": "Ad-hoc"},
    {"Table": "frankenstein", "Rows": len(data.frankenstein), "Models": "Composite (B.1)", "Description": "Chip library - cost breakdown elements from 68 projects", "Refresh": "Ad-hoc"},
    {"Table": "gate_costs", "Rows": len(data.gate_costs), "Models": "Evaluation", "Description": "Validated gate-level cost data", "Refresh": "Ad-hoc"},
    {"Table": "ref_equipment_vectors", "Rows": len(data.equipment_vectors), "Models": "EquipmentVector", "Description": "52-dimension equipment fingerprint vectors", "Refresh": "Ad-hoc"},
    {"Table": "ref_archetype_taxonomy", "Rows": len(data.archetype_taxonomy), "Models": "ALL", "Description": "Master archetype definitions (18 archetypes)", "Refresh": "Static"},
    {"Table": "ref_project_scope_inputs_v2", "Rows": len(data.scope_inputs), "Models": "Calculator", "Description": "Rich scope/capacity for key projects", "Refresh": "Ad-hoc"},
    {"Table": "ref_semantic_chip_classifications", "Rows": len(data.semantic_chips), "Models": "Composite", "Description": "AI-classified cost line items", "Refresh": "Ad-hoc"},
    {"Table": "ref_cp30_combined_indices", "Rows": len(data.cp30), "Models": "ALL", "Description": "CP30 escalation indices (27 locations x years)", "Refresh": "Semi-annual"},
]

st.dataframe(pd.DataFrame(manifest), width='stretch', hide_index=True)

# Quick data preview
st.markdown("---")
st.markdown("#### Data Preview")
preview_table = st.selectbox("Select table to preview", [
    "ref_are_analogue_pool_v3", "project_truth", "frankenstein",
    "gate_costs", "ref_equipment_vectors", "ref_archetype_taxonomy",
    "ref_project_scope_inputs_v2", "ref_semantic_chip_classifications",
])
preview_map = {
    "ref_are_analogue_pool_v3": data.pool,
    "project_truth": data.truth,
    "frankenstein": data.frankenstein,
    "gate_costs": data.gate_costs,
    "ref_equipment_vectors": data.equipment_vectors,
    "ref_archetype_taxonomy": data.archetype_taxonomy,
    "ref_project_scope_inputs_v2": data.scope_inputs,
    "ref_semantic_chip_classifications": data.semantic_chips,
}
preview_df = preview_map.get(preview_table, pd.DataFrame())
if not preview_df.empty:
    st.dataframe(preview_df.head(50), width='stretch')
else:
    st.warning(f"Table '{preview_table}' is empty or not found.")

# Archetype distribution chart
if not data.pool.empty and 'archetype' in data.pool.columns:
    st.markdown("#### Analogue Pool by Archetype")
    arch_counts = data.pool['archetype'].value_counts()
    fig = go.Figure(go.Bar(
        x=arch_counts.values,
        y=arch_counts.index,
        orientation='h',
        marker_color='#0d6efd',
    ))
    fig.update_layout(
        height=400,
        margin=dict(l=200, r=20),
        xaxis_title="Number of Projects",
    )
    st.plotly_chart(fig, width='stretch')
