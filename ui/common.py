"""Shared UI helpers: cached data store, labels, page metadata."""
import os

import streamlit as st

from costbot.data import DataStore
from costbot.labels import ARCHETYPE_LABELS, MODEL_LABELS, model_label  # noqa: F401 (re-exported)

APP_TITLE = "GP screening cost estimator"
APP_VERSION = "POC v1.1"
DISCLAIMER = "Class 5 screening estimate (±50% target). Deterministic models, no AI. Not a basis of estimate."


@st.cache_resource
def load_data() -> DataStore:
    """One DataStore per server process (CSV loads are lazy inside it)."""
    return DataStore()


def reset_session() -> None:
    """on_click callback: forget every widget value and result, so the next
    rerun starts from an empty estimator. Runs before widgets are created,
    which is the only moment Streamlit lets us drop widget keys."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state['equipment_items'] = []
    st.session_state['scope_items'] = []


def data_is_mock(data: DataStore) -> bool:
    """True when the loaded package is the synthetic one shipped in the repo."""
    readme = os.path.join(data.data_dir, 'README.md')
    try:
        with open(readme) as f:
            return 'MOCK' in f.read(200)
    except OSError:
        return False


ARCHETYPE_OPTIONS = list(ARCHETYPE_LABELS)


def musd(value, fallback='n/a') -> str:
    """$1,234M formatting for widget values (st.metric etc.), with a fallback for None/NaN."""
    try:
        if value is None or value != value:
            return fallback
        return f"${float(value):,.0f}M"
    except (TypeError, ValueError):
        return fallback


def musd_md(value, fallback='n/a') -> str:
    """Same, for markdown/caption text: the dollar sign is escaped, otherwise
    Streamlit treats `$...$` as LaTeX."""
    return musd(value, fallback).replace('$', '\\$')
