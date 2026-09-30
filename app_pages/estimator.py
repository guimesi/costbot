"""Estimator page: inputs on the left, live readiness and results on the right."""
import streamlit as st

from costbot.constants import FACILITY_TYPE_OPTIONS, LOCATION_OPTIONS
from costbot.screening import model_readiness, screen_project
from ui.cards import equipment_card, scope_items_card
from ui.common import ARCHETYPE_LABELS, ARCHETYPE_OPTIONS, load_data, reset_session
from ui.results import render_empty_state, render_readiness, render_results
from ui.scope import CAPACITY_UNITS, HULL_TYPES, PROCESS_DOMAINS, SCOPE_TYPES, build_scope

data = load_data()

left, right = st.columns([5, 7], gap="large")

# ----------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------
with left:
    with st.container(border=True):
        st.markdown("**:material/folder_open: Project**")
        archetype = st.selectbox("Archetype", ARCHETYPE_OPTIONS, index=None, key="archetype",
                                 format_func=lambda x: ARCHETYPE_LABELS.get(x, x),
                                 placeholder="Select an archetype",
                                 help="Decides which models are eligible and which analogues are compared.")
        location = st.selectbox("Location (CP30 region)", LOCATION_OPTIONS, index=None, key="location",
                                placeholder="Select a location",
                                help="Drives the EMMA location factor and the analogue region.")
        with st.container(horizontal=True, vertical_alignment="top"):
            basis_year = st.segmented_control("Basis year", [2024, 2025, 2026], default=2024, key="basis_year",
                                              help="Pool data is 2024 USD; other years are CP30-escalated.")
            bf_gf = st.segmented_control("Scope type", SCOPE_TYPES,
                                         key="bf_gf", format_func=str.capitalize,
                                         help="Optional. Sets the ISBL to TEC multiplier and refines analogue matching.")
        project_name = st.text_input("Project name", key="project_name", placeholder="Optional, used in the report")
        with st.expander("Optional details", icon=":material/more_horiz:"):
            process_domain = st.selectbox(
                "Process domain", PROCESS_DOMAINS,
                index=None, key="process_domain", placeholder="Inferred from the archetype if empty",
                format_func=lambda x: x.replace('_', ' ').capitalize())

    archetype = archetype or ''
    core_ready = bool(archetype and location)
    is_pipeline = 'pipeline' in archetype
    is_offshore = 'offshore' in archetype
    is_lng = 'lng' in archetype

    equipment_card(core_ready)

    with st.container(border=True):
        st.markdown("**:material/factory: Facility and capacity**")
        st.caption("Unlocks the calculators (onshore, offshore, pipeline, LNG) and the unconventional lookup.")
        facility_type = st.selectbox("Facility type", FACILITY_TYPE_OPTIONS, index=None, key="facility_type",
                                     accept_new_options=True, disabled=not core_ready,
                                     placeholder="Select or type a facility type",
                                     help="The list is every facility type the calculators understand. "
                                          "You can type another name; the benchmark and composite models still run.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            capacity = st.number_input("Primary capacity", min_value=0.0, value=0.0, key="capacity", disabled=not core_ready)
            cap_unit = st.selectbox("Unit", CAPACITY_UNITS, index=None, key="cap_unit", disabled=not core_ready,
                                    placeholder="Unit", width=140)

        pipeline_length, pipeline_od = 0.0, 36.0
        topsides_wt, water_depth, hull_type = 0.0, 0.0, 'FPSO_newbuild'
        lng_mtpa = 0.0
        if is_pipeline:
            st.markdown("Pipeline")
            with st.container(horizontal=True):
                pipeline_length = st.number_input("Length (km)", min_value=0.0, value=0.0, key="pipe_len")
                pipeline_od = st.number_input("Diameter (in)", min_value=0.0, value=36.0, key="pipe_od")
        if is_offshore:
            st.markdown("Offshore")
            with st.container(horizontal=True):
                topsides_wt = st.number_input("Topsides weight (t)", min_value=0.0, value=0.0, key="topsides_wt")
                water_depth = st.number_input("Water depth (m)", min_value=0.0, value=0.0, key="water_depth",
                                              help="Also used by the SURF subsea estimate.")
            hull_type = st.selectbox("Hull type", HULL_TYPES, key="hull_type",
                                     format_func=lambda x: x.replace('_', ' ').capitalize())
        if is_lng:
            lng_mtpa = st.number_input("LNG capacity (MTPA)", min_value=0.0, value=0.0, key="lng_mtpa")

    surf_trees = surf_flowlines = surf_risers = surf_manifolds = surf_umbilicals = 0
    if is_offshore:
        with st.container(border=True):
            st.markdown("**:material/waves: Subsea scope (SURF)**")
            st.caption("Bottom-up subsea component estimate (4 of 4 within ±30% on the calibration set). "
                       "Reported separately, not part of the total.")
            c1, c2 = st.columns(2)
            with c1:
                surf_trees = st.number_input("Subsea trees", min_value=0, value=0, key="surf_trees_input")
                surf_flowlines = st.number_input("Flowlines", min_value=0, value=0, key="surf_flowlines")
                surf_risers = st.number_input("Risers", min_value=0, value=0, key="surf_risers")
            with c2:
                surf_manifolds = st.number_input("Manifolds", min_value=0, value=0, key="surf_manifolds")
                surf_umbilicals = st.number_input("Umbilicals", min_value=0, value=0, key="surf_umbilicals")
                st.caption(f"Water depth from above: {water_depth:,.0f} m")

    scope_items_card(core_ready)

    with st.container(horizontal=True, vertical_alignment="center"):
        run_clicked = st.button("Run screening estimate", type="primary", icon=":material/play_arrow:",
                                disabled=not core_ready, width="stretch", key="run")
        st.button("Reset", icon=":material/restart_alt:", type="tertiary", key="reset_all",
                  on_click=reset_session, help="Clear every input and the last estimate.")

# ----------------------------------------------------------------------------
# Scope dict (built on every rerun so the readiness panel is live)
# ----------------------------------------------------------------------------
scope = build_scope(
    archetype=archetype, location=location, basis_year=basis_year, bf_gf=bf_gf, project_name=project_name,
    process_domain=process_domain, facility_type=facility_type, capacity=capacity, cap_unit=cap_unit,
    pipeline_length=pipeline_length, pipeline_od=pipeline_od, topsides_wt=topsides_wt, water_depth=water_depth,
    hull_type=hull_type, lng_mtpa=lng_mtpa, surf_trees=surf_trees, surf_flowlines=surf_flowlines,
    surf_risers=surf_risers, surf_manifolds=surf_manifolds, surf_umbilicals=surf_umbilicals,
    equipment_items=st.session_state.equipment_items, scope_items=st.session_state.scope_items,
)

if run_clicked and core_ready:
    st.session_state.last_scope = scope
    st.session_state.last_results = screen_project(scope, data)

# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------
with right:
    render_readiness(model_readiness(scope, data), core_ready)
    if 'last_results' in st.session_state:
        render_results(st.session_state.last_results, data,
                       stale=(scope != st.session_state.get('last_scope')))
    else:
        render_empty_state()
