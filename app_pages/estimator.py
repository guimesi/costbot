"""Estimator page: inputs on the left, live readiness and results on the right."""
import streamlit as st

from costbot.constants import FACILITY_TYPE_OPTIONS, LOCATION_OPTIONS, resolve_country
from costbot.models.benchmark import SIZE_BUCKETS, SIZE_BUCKET_ORDER, BENCHMARK_MODES
from costbot.screening import model_readiness, screen_project
from ui.cards import equipment_card, scope_items_card
from ui.common import ARCHETYPE_LABELS, ARCHETYPE_OPTIONS, load_data, reset_session
from ui.results import render_readiness, render_results

data = load_data()

CAPACITY_UNITS = ['KTA', 'BPD', 'KBPD', 'KBOPD', 'MMSCFD', 'MTPA', 'MTPA_CO2', 'KBD', 'KBSD', 'KBD NGL', 'miles', 'km']
HULL_TYPES = ['FPSO_newbuild', 'FPSO_converted', 'semi_sub', 'jacket_shallow']

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
            bf_gf = st.segmented_control("Scope type", ['greenfield', 'brownfield', 'expansion', 'modification'],
                                         key="bf_gf", format_func=str.capitalize,
                                         help="Optional. Sets the ISBL to TEC multiplier and refines analogue matching.")
        size_bucket = st.selectbox(
            "Rough size", SIZE_BUCKET_ORDER, index=None, key="size_bucket",
            placeholder="Optional: order of magnitude",
            format_func=lambda b: f"{b.replace('_', ' ').capitalize()}  ("
                                  f"${SIZE_BUCKETS[b]['range_musd'][0]:,.0f}M to ${SIZE_BUCKETS[b]['range_musd'][1]:,.0f}M)",
            help="Your own order-of-magnitude judgement. It narrows the benchmark's analogue pool to "
                 "projects of similar size; without it the benchmark matches on category alone.")
        project_name = st.text_input("Project name", key="project_name", placeholder="Optional, used in the report")
        with st.expander("Optional details", icon=":material/more_horiz:"):
            process_domain = st.selectbox(
                "Process domain", ['chemicals', 'refining', 'offshore', 'pipeline', 'lng', 'oil_sands', 'ccs',
                                   'gas_processing', 'upstream_unconventional', 'upstream_conventional', 'power'],
                index=None, key="process_domain", placeholder="Inferred from the archetype if empty",
                format_func=lambda x: x.replace('_', ' ').capitalize())
            benchmark_mode = st.segmented_control(
                "Analogue model", list(BENCHMARK_MODES), default='reference', key="benchmark_mode",
                format_func=lambda m: BENCHMARK_MODES[m],
                help="Reference: the manager's analogue_estimator v3 (matches on category, size only if you "
                     "give a rough size). Engine variant: the first build's model, which also narrows the pool "
                     "to a size band from the capacity. The results show what the other variant would give.")

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
    surf_has_scope = (surf_trees + surf_flowlines + surf_risers) > 0

    scope_items_card(core_ready)

    with st.container(horizontal=True, vertical_alignment="center"):
        run_clicked = st.button("Run screening estimate", type="primary", icon=":material/play_arrow:",
                                disabled=not core_ready, width="stretch", key="run")
        st.button("Reset", icon=":material/restart_alt:", type="tertiary", key="reset_all",
                  on_click=reset_session, help="Clear every input and the last estimate.")

# ----------------------------------------------------------------------------
# Scope dict (built on every rerun so the readiness panel is live)
# ----------------------------------------------------------------------------
scope = {
    'project_name': project_name or (f'{archetype} screening' if archetype else 'screening'),
    'archetype': archetype,
    'process_domain': process_domain or None,
    'location': location or '',
    'country': resolve_country({'location': location or ''}),
    'basis_year': basis_year or 2024,
    'size_bucket': size_bucket,
    'benchmark_mode': benchmark_mode or 'reference',
    'benchmark_compare': True,
    'greenfield_brownfield': bf_gf or 'greenfield',
    'scope_type': bf_gf or 'greenfield',
    'facility_type': (facility_type or '').strip() or None,
    'primary_capacity': capacity if capacity > 0 else None,
    'capacity_unit': cap_unit or '',
    'length_km': pipeline_length if pipeline_length > 0 else None,
    'od_inches': pipeline_od,
    'diameter_inches': pipeline_od,
    'topsides_weight_te': topsides_wt if topsides_wt > 0 else None,
    'water_depth_m': water_depth if water_depth > 0 else None,
    'secondary_params': {
        'hull_type': hull_type,
        'topsides_weight_te': topsides_wt if topsides_wt > 0 else None,
        'water_depth_m': water_depth if water_depth > 0 else None,
    },
    'lng_capacity_mtpa': lng_mtpa if lng_mtpa > 0 else None,
    'equipment_list': [dict(e) for e in st.session_state.equipment_items] or None,
    'scope_items': [dict(i) for i in st.session_state.scope_items] or None,
    'surf_scope': {
        'subsea_trees': {'generic': surf_trees} if surf_trees > 0 else {},
        'flowlines': [{'id': f'FL{i+1}', 'count': 1} for i in range(surf_flowlines)],
        'risers': [{'id': f'R{i+1}', 'count': 1} for i in range(surf_risers)],
        'manifolds': {'generic': surf_manifolds} if surf_manifolds > 0 else {},
        'umbilicals': [{'id': f'U{i+1}'} for i in range(surf_umbilicals)],
        'water_depth_m': water_depth if water_depth > 0 else 1500,
    } if surf_has_scope else None,
}

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
        with st.container(border=True):
            st.markdown("**:material/rocket_launch: How it unlocks**")
            st.markdown("""
1. **Archetype + location** unlock the benchmark against the analogue pool. A **rough size** narrows it to projects of similar magnitude.
2. **Equipment list** unlocks the equipment vector model, the best broad model.
3. **Facility type + capacity** unlock the calculators (onshore, offshore, pipeline, LNG).
4. **Subsea scope** (offshore only) unlocks the SURF component estimate.
5. **Scope items** unlock the composite chip model.

The OSBL overlay runs automatically whenever the onshore calculator produces an ISBL.
Press **Run screening estimate** once the readiness list shows what you need.
""")
