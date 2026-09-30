"""Proposta B ("Console"): the whole scope form lives in the navy sidebar
(theme.sidebar in .streamlit/config.toml, no CSS); the main area is one
results console. Selected with COSTBOT_UI=b.

Same engine calls, widget keys and session-state contract as estimator.py.
"""
import streamlit as st

from costbot.constants import FACILITY_TYPE_OPTIONS, LOCATION_OPTIONS
from costbot.screening import model_readiness, screen_project
from ui.cards import equipment_card, scope_items_card
from ui.common import APP_TITLE, APP_VERSION, ARCHETYPE_LABELS, ARCHETYPE_OPTIONS, load_data, reset_session
from ui.results import render_empty_state
from ui.results_b import render_results_b
from ui.scope import (CAPACITY_UNITS, HULL_TYPES, PROCESS_DOMAINS, SCOPE_TYPES, build_scope, scope_from_state,
                      short_label, visible_readiness)

data = load_data()
ss = st.session_state


def group_header(title: str, model_ids, status_by_model: dict) -> None:
    """12px group label at left, model chip(s) at right: mint dot when the
    model is ready, outlined when not, nothing when the archetype does not route to it."""
    chips = []
    for mid in model_ids:
        s = status_by_model.get(mid)
        if s == 'ready':
            chips.append(f":green[● {short_label(mid)}]")
        elif s in ('needs', 'auto'):
            chips.append(f":gray[○ {short_label(mid)}]")
        elif s == 'excluded':
            chips.append(f":red[● {short_label(mid)} excluded]")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.caption(title, width="stretch")
        if chips:
            st.caption(" ".join(chips))


# Readiness from the values already in session_state, so the group chips can sit above their inputs
_live = scope_from_state(ss)
status_by_model = {r['model_id']: r['status'] for r in model_readiness(_live, data)} if _live.get('archetype') else {}

# ----------------------------------------------------------------------------
# Sidebar: scope console
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f":material/calculate: **{APP_TITLE}** :gray-badge[{APP_VERSION}]")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.caption("**SCOPE**", width="stretch")
        st.button("Reset", type="tertiary", key="reset_all", on_click=reset_session,
                  help="Clear every input and the last estimate.")

    archetype = st.selectbox("Archetype", ARCHETYPE_OPTIONS, index=None, key="archetype",
                             format_func=lambda x: ARCHETYPE_LABELS.get(x, x), placeholder="Select an archetype")
    location = st.selectbox("Location", LOCATION_OPTIONS, index=None, key="location", placeholder="Select a location")
    c1, c2 = st.columns([1, 1.2], vertical_alignment="bottom")
    with c1:
        basis_year = st.segmented_control("Basis year", [2024, 2025, 2026], default=2024, key="basis_year",
                                          format_func=lambda y: str(y)[2:], width="stretch")
    with c2:
        bf_gf = st.selectbox("Scope type", SCOPE_TYPES, index=None, key="bf_gf", format_func=str.capitalize,
                             placeholder="Greenfield")
    project_name = st.text_input("Project name", key="project_name", placeholder="Optional, shown in the console")
    with st.expander("More", icon=":material/more_horiz:"):
        process_domain = st.selectbox("Process domain", PROCESS_DOMAINS, index=None, key="process_domain",
                                      placeholder="Inferred from the archetype", format_func=lambda x: x.replace('_', ' ').capitalize())

    archetype = archetype or ''
    core_ready = bool(archetype and location)
    is_pipeline = 'pipeline' in archetype
    is_offshore = 'offshore' in archetype
    is_lng = 'lng' in archetype
    st.divider()

    # Facility · capacity
    calc_ids = ['Calculator_Onshore'] + (['Calculator_Offshore'] if is_offshore else []) \
        + (['Calculator_Pipeline'] if is_pipeline else []) + (['Calculator_LNG'] if is_lng else []) + ['Unconventional']
    group_header("Facility · capacity", calc_ids, status_by_model)
    facility_type = st.selectbox("Facility type", FACILITY_TYPE_OPTIONS, index=None, key="facility_type",
                                 accept_new_options=True, disabled=not core_ready, placeholder="Facility type",
                                 label_visibility="collapsed")
    with st.container(horizontal=True, vertical_alignment="center"):
        capacity = st.number_input("Primary capacity", min_value=0.0, value=0.0, key="capacity", disabled=not core_ready,
                                   label_visibility="collapsed", placeholder="Capacity")
        cap_unit = st.selectbox("Unit", CAPACITY_UNITS, index=None, key="cap_unit", disabled=not core_ready,
                                placeholder="Unit", label_visibility="collapsed", width=96)
    pipeline_length, pipeline_od = 0.0, 36.0
    topsides_wt, water_depth, hull_type = 0.0, 0.0, 'FPSO_newbuild'
    lng_mtpa = 0.0
    if is_pipeline:
        with st.container(horizontal=True):
            pipeline_length = st.number_input("Length (km)", min_value=0.0, value=0.0, key="pipe_len")
            pipeline_od = st.number_input("Diameter (in)", min_value=0.0, value=36.0, key="pipe_od")
    if is_offshore:
        with st.container(horizontal=True):
            topsides_wt = st.number_input("Topsides weight (t)", min_value=0.0, value=0.0, key="topsides_wt")
            water_depth = st.number_input("Water depth (m)", min_value=0.0, value=0.0, key="water_depth")
        hull_type = st.selectbox("Hull type", HULL_TYPES, key="hull_type", format_func=lambda x: x.replace('_', ' ').capitalize())
    if is_lng:
        lng_mtpa = st.number_input("LNG capacity (MTPA)", min_value=0.0, value=0.0, key="lng_mtpa")

    surf_trees = surf_flowlines = surf_risers = surf_manifolds = surf_umbilicals = 0
    if is_offshore:
        group_header("Subsea scope (SURF)", ['SURF_User'], status_by_model)
        with st.expander("Trees, flowlines, risers", icon=":material/waves:"):
            surf_trees = st.number_input("Subsea trees", min_value=0, value=0, key="surf_trees_input")
            surf_flowlines = st.number_input("Flowlines", min_value=0, value=0, key="surf_flowlines")
            surf_risers = st.number_input("Risers", min_value=0, value=0, key="surf_risers")
            surf_manifolds = st.number_input("Manifolds", min_value=0, value=0, key="surf_manifolds")
            surf_umbilicals = st.number_input("Umbilicals", min_value=0, value=0, key="surf_umbilicals")

    # Equipment
    n_items = sum(int(e.get('count', 0)) for e in ss.equipment_items)
    group_header(f"Equipment · {n_items} items" if n_items else "Equipment", ['EquipmentVector'], status_by_model)
    equipment_card(core_ready, border=False)

    # Scope items
    group_header("Scope items", ['Composite'], status_by_model)
    scope_items_card(core_ready, border=False)

    # Scope dict, built every rerun so the readiness line is live
    scope = build_scope(
        archetype=archetype, location=location, basis_year=basis_year, bf_gf=bf_gf, project_name=project_name,
        process_domain=process_domain, facility_type=facility_type, capacity=capacity, cap_unit=cap_unit,
        pipeline_length=pipeline_length, pipeline_od=pipeline_od, topsides_wt=topsides_wt, water_depth=water_depth,
        hull_type=hull_type, lng_mtpa=lng_mtpa, surf_trees=surf_trees, surf_flowlines=surf_flowlines,
        surf_risers=surf_risers, surf_manifolds=surf_manifolds, surf_umbilicals=surf_umbilicals,
        equipment_items=ss.equipment_items, scope_items=ss.scope_items,
    )

    st.divider()
    visible = visible_readiness(model_readiness(scope, data))
    n_ready = sum(1 for r in visible if r['status'] == 'ready')
    off = [short_label(r['model_id']) for r in visible if r['status'] != 'ready']
    with st.container(horizontal=True, vertical_alignment="center"):
        if core_ready:
            st.caption(f"{n_ready} of {len(visible)} models ready", width="stretch")
            if off:
                st.caption(f"`{', '.join(off[:2])}{'…' if len(off) > 2 else ''} off`")
        else:
            st.caption("Pick an archetype and a location to see which models can run.")
    stale = 'last_results' in ss and scope != ss.get('last_scope')
    run_clicked = st.button("Run estimate", type="primary", icon=":material/play_arrow:", disabled=not core_ready,
                            width="stretch", key="run", help="Inputs changed since the last run." if stale else None)
    with st.container(horizontal=True):
        st.page_link("app_pages/models.py", label="Models", icon=":material/science:")
        st.page_link("app_pages/data.py", label="Data", icon=":material/database:")

if run_clicked and core_ready:
    ss.last_scope = scope
    ss.last_results = screen_project(scope, data)
    stale = False

# ----------------------------------------------------------------------------
# Main: results console
# ----------------------------------------------------------------------------
if 'last_results' in ss:
    render_results_b(ss.last_results, data, stale=stale)
else:
    st.caption(":material/calculate: Screening estimate")
    st.markdown("## Fill the scope in the sidebar and press Run")
    render_empty_state()
