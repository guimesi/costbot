"""Shared UI helpers: cached data store, CSS, page list."""
import streamlit as st

from costbot.data import DataStore

APP_TITLE = "GP Screening Cost Estimator"
APP_VERSION = "POC v1.0"


@st.cache_resource
def load_data() -> DataStore:
    """One DataStore per server process (CSV loads are lazy inside it)."""
    return DataStore()


_CSS = """
<style>
    .main .block-container { padding-top: 1rem; max-width: 1400px; }
    div[data-testid="stMetric"] {
        background: #f8f9fa; border: 1px solid #dee2e6;
        border-radius: 8px; padding: 12px 16px;
    }
    .model-ready { background: #d1e7dd; border-radius: 6px; padding: 8px 12px;
                   margin-bottom: 6px; font-size: 0.85em; color: #0f5132; }
    .model-not-ready { background: #f5f5f5; border-radius: 6px; padding: 8px 12px;
                       margin-bottom: 6px; font-size: 0.85em; color: #6c757d; }
    .conf-high { background: #d1e7dd; color: #0f5132; padding: 2px 10px;
                 border-radius: 4px; font-weight: 600; font-size: 0.8em; }
    .conf-med { background: #fff3cd; color: #664d03; padding: 2px 10px;
                border-radius: 4px; font-weight: 600; font-size: 0.8em; }
    .conf-low { background: #f8d7da; color: #842029; padding: 2px 10px;
                border-radius: 4px; font-weight: 600; font-size: 0.8em; }
    .disclaimer { background: #fff3cd; padding: 12px 16px; border-radius: 8px;
                  border-left: 4px solid #ffc107; font-size: 0.85em; margin-top: 12px; }
    .stTabs [data-baseweb="tab-list"] { gap: 0px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 24px; font-weight: 500; }
</style>
"""


def inject_css() -> None:
    """Custom CSS from the first build. To be replaced by config.toml theming in the UX pass."""
    st.markdown(_CSS, unsafe_allow_html=True)
