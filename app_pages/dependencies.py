"""Dependencies page: input -> model graph, unlock sequence, routing."""
import pandas as pd
import streamlit as st

from costbot.constants import ARCHETYPE_MODELS

st.markdown("### Input - Model Dependency Graph")
st.caption(
    "**Required** = model cannot fire without this input. "
    "**Optional** = improves accuracy."
)

deps = [
    {"Input": "Archetype", "Required For": "ALL MODELS", "Optional For": "-"},
    {"Input": "Location", "Required For": "ALL (CP30 normalization)", "Optional For": "-"},
    {"Input": "Basis Year", "Required For": "ALL (time normalization)", "Optional For": "-"},
    {"Input": "Scope Type (BF/GF)", "Required For": "-", "Optional For": "Benchmark, Composite, Calculator"},
    {"Input": "Facility Type", "Required For": "Calculator_Onshore", "Optional For": "Benchmark, Unconventional"},
    {"Input": "Primary Capacity", "Required For": "Calculator_Onshore, Calculator_LNG", "Optional For": "Benchmark"},
    {"Input": "Pipeline Length + OD", "Required For": "Calculator_Pipeline", "Optional For": "-"},
    {"Input": "Topsides Weight", "Required For": "Calculator_Offshore", "Optional For": "-"},
    {"Input": "Equipment List", "Required For": "EquipmentVector", "Optional For": "-"},
    {"Input": "Scope Items (multi)", "Required For": "Composite", "Optional For": "-"},
    {"Input": "SURF Scope", "Required For": "SURF_User", "Optional For": "-"},
]
st.dataframe(pd.DataFrame(deps), width='stretch', hide_index=True)

st.markdown("---")
st.markdown("### Progressive Unlock Sequence")
unlock = [
    {"Step": 1, "User Action": "+ Archetype + Location + Year", "Models Unlocked": "Benchmark", "Accuracy Class": "Class 5"},
    {"Step": 2, "User Action": "+ Facility type + capacity", "Models Unlocked": "Calculator (Onshore/Offshore/Pipeline/LNG)", "Accuracy Class": "Class 4-5"},
    {"Step": 3, "User Action": "+ Scope items (multi-select)", "Models Unlocked": "Composite (B.1)", "Accuracy Class": "Class 5"},
    {"Step": 4, "User Action": "+ Equipment specification", "Models Unlocked": "EquipmentVector", "Accuracy Class": "Class 4"},
    {"Step": 5, "User Action": "+ SURF subsea scope", "Models Unlocked": "SURF_User (component)", "Accuracy Class": "Class 3-4"},
]
st.dataframe(pd.DataFrame(unlock), width='stretch', hide_index=True)

# Visual dependency diagram
st.markdown("---")
st.markdown("### Model Routing by Archetype")
routing_data = []
for arch, model_list in sorted(ARCHETYPE_MODELS.items()):
    routing_data.append({
        "Archetype": arch,
        "Models": ", ".join(model_list),
        "Count": len(model_list),
    })
st.dataframe(pd.DataFrame(routing_data), width='stretch', hide_index=True)
