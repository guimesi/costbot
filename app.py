"""
GP screening cost estimator - Streamlit entry point
====================================================
Local-running POC. No Spark, no Snowflake, no LLM.
Loads reference data from CSV, runs 10 deterministic models.

Run: streamlit run app.py

Pages live in app_pages/, shared UI helpers in ui/, the engine in costbot/.
Theme is .streamlit/config.toml; no CSS is injected.
"""
import os
import sys

import streamlit as st

# Make costbot/, ui/ and app_pages/ importable regardless of the working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.common import APP_TITLE, APP_VERSION, DISCLAIMER, load_data  # noqa: E402

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":material/calculate:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Session state: one place, before any page runs
st.session_state.setdefault('equipment_items', [])
st.session_state.setdefault('scope_items', [])

load_data()  # warm the cache once per process

with st.container(horizontal=True, vertical_alignment="center"):
    st.markdown(f"## {APP_TITLE}")
    st.badge(APP_VERSION, icon=":material/science:", color="blue")
st.caption(DISCLAIMER)

pages = [
    st.Page("app_pages/estimator.py", title="Estimator", icon=":material/calculate:", default=True),
    st.Page("app_pages/models.py", title="Models", icon=":material/science:"),
    st.Page("app_pages/data.py", title="Data", icon=":material/database:"),
]
st.navigation(pages, position="top").run()
