"""
GP Screening Cost Estimator - Streamlit entry point
====================================================
Local-running POC. No Spark, no Snowflake, no LLM.
Loads reference data from CSV, runs 10 deterministic models.

Run: streamlit run app.py

Pages live in app_pages/, shared UI helpers in ui/, the engine in costbot/.
"""
import os
import sys

import streamlit as st

# Make costbot/, ui/ and app_pages/ importable regardless of the working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.common import APP_TITLE, APP_VERSION, inject_css, load_data  # noqa: E402

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":material/calculate:",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_css()

# Session state: one place, before any page runs
st.session_state.setdefault('equipment_items', [])
st.session_state.setdefault('scope_items', [])

load_data()  # warm the cache once per process

# Header shared by every page
header_cols = st.columns([6, 1])
with header_cols[0]:
    st.markdown(f"## {APP_TITLE}")
with header_cols[1]:
    st.markdown(
        f'<span style="background:#0d6efd;color:white;padding:4px 12px;border-radius:12px;'
        f'font-size:11px;font-weight:600;text-transform:uppercase;">{APP_VERSION}</span>',
        unsafe_allow_html=True,
    )

pages = [
    st.Page("app_pages/estimator.py", title="Estimator", icon=":material/calculate:", default=True),
    st.Page("app_pages/data_package.py", title="Data Package", icon=":material/database:"),
    st.Page("app_pages/code_inventory.py", title="Code Inventory", icon=":material/code:"),
    st.Page("app_pages/dependencies.py", title="Dependencies", icon=":material/account_tree:"),
    st.Page("app_pages/model_specs.py", title="Model Specs", icon=":material/science:"),
]
st.navigation(pages, position="top").run()

st.markdown("---")
st.caption(
    f"{APP_TITLE} - Streamlit {APP_VERSION} - "
    "Class 5 accuracy target (±50%) - Not a basis of estimate"
)
