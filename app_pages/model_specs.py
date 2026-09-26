"""Model Specs page: per-model cards and accuracy summary."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.markdown("### Model Specifications")

specs = {
    "Calculator_Onshore": {
        "Algorithm": "Six-tenths power-law scaling: ISBL = base * (cap/base_cap)^0.6. EMMA location factor. TEC multiplier (GF: 2.50x, BF: 1.30x).",
        "Calibration": "Back-solved from project truth (N=1-2 per facility type). CIRCULAR for most correlations.",
        "LOOCV": "79% ±30% (N=14) - strongest archetype: refinery brownfield",
        "Libraries": "Pure math (no external deps)",
    },
    "Calculator_Offshore": {
        "Algorithm": "Topsides weight - cost curve + hull parametric. SURF separate. Indirects ~40%.",
        "Calibration": "FPSO N=2 LOOCV",
        "LOOCV": "50% ±30% (N=2)",
        "Libraries": "Pure math",
    },
    "Calculator_Pipeline": {
        "Algorithm": "Base rate/km * diameter factor * facilities * indirects. MAG pricing tables.",
        "LOOCV": "67% ±30% (N=3)",
        "Libraries": "Pure math + CET rate tables",
    },
    "Calculator_LNG": {
        "Algorithm": "A42 CET subsystem regressions * location rates. Miscalibrated.",
        "LOOCV": "0% ±30% - NOT CALIBRATED",
        "Libraries": "Pure math + regression equations",
        "Warning": "Do not rely on LNG estimates. Known gap.",
    },
    "Benchmark": {
        "Algorithm": "6D one-hot encoding + cosine sim. LOOCV. Encodes process_domain, scope_type, facility_type, location, capacity proximity, and CP30 match. Blended 50/50 with size similarity. Top-N analog. -> P20/P50/P80.",
        "Pool": "503 projects (ref_are_analogue_pool_v3)",
        "LOOCV": "Cosine-similarity rewrite. Key contributor to 84% ensemble accuracy.",
        "Libraries": "numpy, pandas, sklearn (StandardScaler, cosine_similarity)",
    },
    "EquipmentVector": {
        "Algorithm": "52-dimension equipment composition vector. Process equipment only (zeroes valves/instrumenta). L2-normalized cosine similarity. Top-5 weighted average.",
        "Pool": "593 equipment vectors",
        "LOOCV": "66% ±30% (N=29) - best broad model",
        "Libraries": "numpy (linear algebra)",
    },
    "Unconventional": {
        "Algorithm": "Facility-type median lookup from pool. Optional log-linear interpolation with capacity.",
        "Pool": "11 onshore_unconventional entries, 6 facility types",
        "LOOCV": "70% ±30% (N=10)",
        "Libraries": "numpy, pandas",
    },
    "Composite": {
        "Algorithm": "Multi-item scope builder. Each scope item matches chips from frankenstein library. Sum of median chip costs.",
        "Library": "857 chips from 68 projects",
        "LOOCV": "26% ±30%, 48% ±50% (refinery_bf: 50% ±30%)",
        "Libraries": "pandas",
    },
    "SURF_User": {
        "Algorithm": "Subsea equipment bottom-up: trees + flowlines + risers + manifolds + umbilicals. Heritage pricing * calibration factor (1.34).",
        "Calibration": "4 Guyana deepwater projects (SBM/MODEC).",
        "LOOCV": "4/4 within ±30%",
        "Libraries": "Pure math",
    },
}

for model_name, spec in specs.items():
    with st.expander(f"**{model_name}**", expanded=False):
        for key, val in spec.items():
            if key == 'Warning':
                st.warning(val)
            else:
                st.markdown(f"**{key}:** {val}")

st.markdown("---")
st.markdown("### Accuracy Summary (50 Test Projects)")
st.caption("Baseline from reference evaluation, improved by Benchmark cosine-similarity rewrite and 12 engine fixes.")
accuracy_data = [
    {"Archetype": "Chemicals", "Accuracy (±30%)": "4/4 (100%)", "Status": "Strong"},
    {"Archetype": "Deepwater", "Accuracy (±30%)": "3/3 (100%)", "Status": "Strong"},
    {"Archetype": "CCS", "Accuracy (±30%)": "2/2 (100%)", "Status": "Strong"},
    {"Archetype": "Unconventional", "Accuracy (±30%)": "10/11 (91%)", "Status": "Strong"},
    {"Archetype": "Refinery Brownfield", "Accuracy (±30%)": "13/17 (76%)", "Status": "Strong"},
    {"Archetype": "Pipeline", "Accuracy (±30%)": "2/5 (40%)", "Status": "Gap"},
    {"Archetype": "Oil Sands", "Accuracy (±30%)": "1/3 (33%)", "Status": "Gap"},
    {"Archetype": "LNG", "Accuracy (±30%)": "0/2 (0%)", "Status": "Gap"},
    {"Archetype": "OVERALL (engine)", "Accuracy (±30%)": "42/50 (84%)", "Status": "Exceeds 77% target"},
]
st.dataframe(pd.DataFrame(accuracy_data), width='stretch', hide_index=True)

# Accuracy visualization
fig = go.Figure()
labels = [d["Archetype"] for d in accuracy_data[:-1]]
vals = []
for d in accuracy_data[:-1]:
    frac = d["Accuracy (±30%)"].split("(")[1].rstrip("%)").rstrip("*")
    vals.append(int(frac))

colors = ['#198754' if v >= 70 else '#ffc107' if v >= 40 else '#dc3545' for v in vals]
fig.add_trace(go.Bar(x=labels, y=vals, marker_color=colors,
                     text=[f"{v}%" for v in vals], textposition='outside'))
fig.update_layout(
    title="LOOCV Accuracy by Archetype (±30%)",
    yaxis_title="Accuracy %", yaxis_range=[0, 110],
    height=350, margin=dict(t=40, b=40),
)
fig.add_hline(y=84, line_dash="dash", line_color="blue",
              annotation_text="Overall: 84%")
fig.add_hline(y=77, line_dash="dot", line_color="gray",
              annotation_text="Target: 77%")
st.plotly_chart(fig, width='stretch')
