"""Shared UI helpers: cached data store, labels, page metadata."""
import os

import streamlit as st

from costbot.data import DataStore

APP_TITLE = "GP screening cost estimator"
APP_VERSION = "POC v1.1"
DISCLAIMER = "Class 5 screening estimate (±50% target). Deterministic models, no AI. Not a basis of estimate."


@st.cache_resource
def load_data() -> DataStore:
    """One DataStore per server process (CSV loads are lazy inside it)."""
    return DataStore()


def data_is_mock(data: DataStore) -> bool:
    """True when the loaded package is the synthetic one shipped in the repo."""
    readme = os.path.join(data.data_dir, 'README.md')
    try:
        with open(readme) as f:
            return 'MOCK' in f.read(200)
    except OSError:
        return False


ARCHETYPE_LABELS = {
    'refinery_bf': 'Refinery brownfield',
    'refinery_gf': 'Refinery greenfield',
    'onshore_petchem': 'Petrochemical (onshore)',
    'integrated_petchem': 'Integrated petrochemical',
    'offshore_fpso': 'Offshore FPSO',
    'offshore_platform': 'Offshore platform',
    'pipeline_mainline': 'Pipeline (mainline)',
    'pipeline_gathering': 'Pipeline (gathering)',
    'pipeline_complex': 'Pipeline (complex)',
    'lng_onshore': 'LNG (onshore)',
    'lng_terminal': 'LNG terminal',
    'oil_sands': 'Oil sands',
    'onshore_conventional': 'Onshore conventional',
    'onshore_unconventional': 'Onshore unconventional',
    'ccs': 'Carbon capture (CCS)',
    'ccs_gas_processing': 'CCS / gas processing',
    'renewable_diesel': 'Renewable diesel',
    'gas_processing': 'Gas processing',
    'power_generation': 'Power generation',
}
ARCHETYPE_OPTIONS = list(ARCHETYPE_LABELS)

MODEL_LABELS = {
    'Benchmark': 'Benchmark (analogues)',
    'EquipmentVector': 'Equipment vector',
    'Calculator_Onshore': 'Onshore calculator',
    'Calculator_Offshore': 'Offshore calculator',
    'Calculator_Pipeline': 'Pipeline calculator',
    'Calculator_LNG': 'LNG calculator',
    'Unconventional': 'Unconventional lookup',
    'Composite': 'Composite (scope chips)',
    'SURF_User': 'SURF subsea (component)',
    'OSBL_Estimate': 'OSBL overlay (indirect)',
}


def model_label(model_id: str) -> str:
    return MODEL_LABELS.get(model_id, model_id)


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
