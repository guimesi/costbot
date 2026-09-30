"""
GP screening cost estimator - Streamlit entry point
====================================================
Local-running POC. No Spark, no Snowflake, no LLM.
Loads reference data from CSV, runs 10 deterministic models.

Run: streamlit run app.py

Pages live in app_pages/, shared UI helpers in ui/, the engine in costbot/.
Theme is .streamlit/config.toml; no CSS is injected.

COSTBOT_UI picks the estimator layout (design handoff, Sep 2026):
  current  the two-column page in app_pages/estimator.py (default)
  a        Proposta A "Guiada": stepper + hero estimate (app_pages/estimator_a.py)
  b        Proposta B "Console": navy sidebar + results console (app_pages/estimator_b.py)
"""
import os
import sys

import streamlit as st

# Make costbot/, ui/ and app_pages/ importable regardless of the working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.common import APP_TITLE, APP_VERSION, DISCLAIMER, load_data  # noqa: E402

ESTIMATOR_PAGES = {
    'current': 'app_pages/estimator.py',
    'a': 'app_pages/estimator_a.py',
    'b': 'app_pages/estimator_b.py',
}
UI = os.environ.get('COSTBOT_UI', 'current').strip().lower()
if UI not in ESTIMATOR_PAGES:
    UI = 'current'

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=":material/calculate:",
    layout="wide",
    initial_sidebar_state="expanded" if UI == 'b' else "collapsed",
)

# Session state: one place, before any page runs
st.session_state.setdefault('equipment_items', [])
st.session_state.setdefault('scope_items', [])

load_data()  # warm the cache once per process

if UI == 'current':
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(f"## {APP_TITLE}")
        st.badge(APP_VERSION, icon=":material/science:", color="blue")
    st.caption(DISCLAIMER)
elif UI == 'a':
    # App bar: compact title + version pill; the disclaimer moves next to the report button
    st.markdown(f":material/calculate: **{APP_TITLE}** :gray-badge[{APP_VERSION}]")
# 'b': the title lives in the sidebar console

pages = [
    st.Page(ESTIMATOR_PAGES[UI], title="Estimator", icon=":material/calculate:", default=True),
    st.Page("app_pages/models.py", title="Models", icon=":material/science:"),
    st.Page("app_pages/data.py", title="Data", icon=":material/database:"),
]
st.navigation(pages, position="top").run()
