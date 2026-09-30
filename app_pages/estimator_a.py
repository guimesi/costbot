"""Proposta A ("Guiada"): the scope as a stepper on the left (done / active /
optional steps), a compact readiness strip and the Run button; hero estimate
and evidence tabs on the right. Selected with COSTBOT_UI=a.

Same engine calls, widget keys and session-state contract as estimator.py.
"""
import streamlit as st

from costbot.constants import FACILITY_TYPE_OPTIONS, LOCATION_OPTIONS
from costbot.screening import model_readiness, screen_project
from ui.cards import equipment_card, scope_items_card
from ui.common import ARCHETYPE_LABELS, ARCHETYPE_OPTIONS, load_data, reset_session
from ui.results import render_empty_state
from ui.results_a import render_results_a
from ui.scope import (CAPACITY_UNITS, HULL_TYPES, PROCESS_DOMAINS, SCOPE_TYPES, build_scope, equipment_summary,
                      facility_hint, facility_summary, project_summary, readiness_chip, scope_items_summary,
                      visible_readiness)

data = load_data()
ss = st.session_state

# Step state from the previous run's widget values (session_state already holds
# the new value when a widget changed). Labels need it before the widgets exist.
_archetype = ss.get('archetype') or ''
_location = ss.get('location')
_facility = (ss.get('facility_type') or '').strip()
_capacity = float(ss.get('capacity') or 0)
step_done = {
    1: bool(_archetype and _location),
    2: bool(ss.equipment_items),
    3: bool(_facility and _capacity > 0),
    4: bool(ss.scope_items),
}
active_step = next((s for s in (1, 2, 3) if not step_done[s]), None)


# A step has been "started" once it holds any input; done steps collapse only
# when the user moved on to a later step (or after a run), never mid-entry:
# collapsing step 3 the moment a capacity is typed would hide the unit selector.
step_started = {2: bool(ss.equipment_items), 3: bool(_facility or _capacity > 0), 4: bool(ss.scope_items)}
has_run = 'last_results' in ss


def step_open(n: int) -> bool:
    if not step_done[n]:
        return True
    if has_run:
        return False
    return not any(started for m, started in step_started.items() if m > n)


def step_label(n: int, title: str, summary: str, optional: bool = False, chip: str = '') -> str:
    # Badges, not coloured icons: expander labels keep icons monochrome
    if step_done[n]:
        mark = ":green-badge[:material/check:]"
    elif n == active_step:
        mark = f":blue-badge[{n}]"
    else:
        mark = f":gray-badge[{n}]"
    label = f"{mark} **{title}**"
    if optional and not step_done[n]:
        label += " :gray[optional]"
    if summary:
        label += f" :gray[· {summary}]"
    if chip:
        label += f" {chip}"
    return label


left, right = st.columns([5, 9], gap="large")

# ----------------------------------------------------------------------------
# Left: stepper
# ----------------------------------------------------------------------------
with left:
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(":material/tune: **Scope**", width="stretch")
        st.button("Reset", icon=":material/restart_alt:", type="tertiary", key="reset_all",
                  on_click=reset_session, help="Clear every input and the last estimate.")

    # Step 1: project
    with st.expander(step_label(1, "Project", project_summary(_archetype, _location, ss.get('basis_year'), ss.get('bf_gf'))
                                if step_done[1] else "archetype and location"),
                     expanded=step_open(1)):
        archetype = st.selectbox("Archetype", ARCHETYPE_OPTIONS, index=None, key="archetype",
                                 format_func=lambda x: ARCHETYPE_LABELS.get(x, x), placeholder="Select an archetype",
                                 help="Decides which models are eligible and which analogues are compared.")
        location = st.selectbox("Location (CP30 region)", LOCATION_OPTIONS, index=None, key="location",
                                placeholder="Select a location", help="Drives the EMMA location factor and the analogue region.")
        with st.container(horizontal=True, vertical_alignment="top"):
            basis_year = st.segmented_control("Basis year", [2024, 2025, 2026], default=2024, key="basis_year",
                                              help="Pool data is 2024 USD; other years are CP30-escalated.")
            bf_gf = st.segmented_control("Scope type", SCOPE_TYPES, key="bf_gf", format_func=str.capitalize,
                                         help="Optional. Sets the ISBL to TEC multiplier and refines analogue matching.")
        project_name = st.text_input("Project name", key="project_name", placeholder="Optional, used in the report")
        process_domain = st.selectbox("Process domain", PROCESS_DOMAINS, index=None, key="process_domain",
                                      placeholder="Optional, inferred from the archetype if empty",
                                      format_func=lambda x: x.replace('_', ' ').capitalize())

    archetype = archetype or ''
    core_ready = bool(archetype and location)
    is_pipeline = 'pipeline' in archetype
    is_offshore = 'offshore' in archetype
    is_lng = 'lng' in archetype

    # Step 2: equipment list
    with st.expander(step_label(2, "Equipment list", equipment_summary(ss.equipment_items) if step_done[2] else "",
                                chip=":green-badge[:material/bolt: Unlocks Equipment vector]" if step_done[2] else ""),
                     expanded=step_open(2)):
        st.caption("Unlocks the equipment vector model, the best broad model (66% within ±30%). "
                   "Pumps, exchangers, towers, drums, compressors: even rough counts help.")
        equipment_card(core_ready, border=False)

    # Step 3: facility and capacity
    with st.expander(step_label(3, "Facility and capacity", facility_summary(_facility, _capacity, ss.get('cap_unit'))
                                if step_done[3] else ""),
                     expanded=step_open(3)):
        st.caption("One number is enough. Unlocks the onshore calculator and the OSBL overlay"
                   + (", the offshore calculator" if is_offshore else "")
                   + (", the pipeline calculator" if is_pipeline else "")
                   + (", the LNG calculator" if is_lng else "") + ".")
        facility_type = st.selectbox("Facility type", FACILITY_TYPE_OPTIONS, index=None, key="facility_type",
                                     accept_new_options=True, disabled=not core_ready,
                                     placeholder="Select or type a facility type",
                                     help="The list is every facility type the calculators understand. "
                                          "You can type another name; the benchmark and composite models still run.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            capacity = st.number_input("Primary capacity", min_value=0.0, value=0.0, key="capacity", disabled=not core_ready)
            cap_unit = st.selectbox("Unit", CAPACITY_UNITS, index=None, key="cap_unit", disabled=not core_ready,
                                    placeholder="Unit", width=120)
        hint = facility_hint(facility_type)
        if hint:
            st.caption(f":material/info: {hint}")

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
                water_depth = st.number_input("Water depth (m)", min_value=0.0, value=0.0, key="water_depth",
                                              help="Also used by the SURF subsea estimate.")
            hull_type = st.selectbox("Hull type", HULL_TYPES, key="hull_type",
                                     format_func=lambda x: x.replace('_', ' ').capitalize())
        if is_lng:
            lng_mtpa = st.number_input("LNG capacity (MTPA)", min_value=0.0, value=0.0, key="lng_mtpa")

    # Offshore only: SURF
    surf_trees = surf_flowlines = surf_risers = surf_manifolds = surf_umbilicals = 0
    if is_offshore:
        surf_done = any(int(ss.get(k) or 0) > 0 for k in ('surf_trees_input', 'surf_flowlines', 'surf_risers'))
        mark = ":green[:material/check_circle:]" if surf_done else ":gray[:material/waves:]"
        with st.expander(f"{mark} **Subsea scope (SURF)** :gray[optional · component, reported separately]", expanded=False):
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

    # Step 4: scope items (optional)
    with st.expander(step_label(4, "Scope items", scope_items_summary(ss.scope_items) if step_done[4] else "", optional=True),
                     expanded=False):
        st.caption("Add process units and OSBL packages to unlock Composite (low accuracy, 26%). "
                   "Each piece is matched against the chip library and summed.")
        scope_items_card(core_ready, border=False)

    # Scope dict, built every rerun so the readiness strip is live
    scope = build_scope(
        archetype=archetype, location=location, basis_year=basis_year, bf_gf=bf_gf, project_name=project_name,
        process_domain=process_domain, facility_type=facility_type, capacity=capacity, cap_unit=cap_unit,
        pipeline_length=pipeline_length, pipeline_od=pipeline_od, topsides_wt=topsides_wt, water_depth=water_depth,
        hull_type=hull_type, lng_mtpa=lng_mtpa, surf_trees=surf_trees, surf_flowlines=surf_flowlines,
        surf_risers=surf_risers, surf_manifolds=surf_manifolds, surf_umbilicals=surf_umbilicals,
        equipment_items=ss.equipment_items, scope_items=ss.scope_items,
    )

    # Models ready strip
    visible = visible_readiness(model_readiness(scope, data))
    n_ready = sum(1 for r in visible if r['status'] == 'ready')
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(":material/checklist: **Models ready**", width="stretch")
            st.markdown(f"`{n_ready} / {len(visible)}`" if core_ready else "`0 / 0`")
        if core_ready:
            st.progress(n_ready / len(visible) if visible else 0.0)
            st.markdown("  ".join(readiness_chip(r) for r in visible))
        else:
            st.caption("Pick an archetype and a location to see which models can run.")

    run_clicked = st.button("Run screening estimate", type="primary", icon=":material/play_arrow:",
                            disabled=not core_ready, width="stretch", key="run")

if run_clicked and core_ready:
    ss.last_scope = scope
    ss.last_results = screen_project(scope, data)

# ----------------------------------------------------------------------------
# Right: results
# ----------------------------------------------------------------------------
with right:
    if 'last_results' in ss:
        render_results_a(ss.last_results, data, stale=(scope != ss.get('last_scope')))
    else:
        render_empty_state()
