"""Estimator page: input panel (left) and results (right)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from costbot.constants import FACILITY_TYPE_OPTIONS, LOCATION_OPTIONS, resolve_country
from costbot.report import generate_html_report
from costbot.screening import screen_project, validate_bid
from ui.cards import _OTHER_FACILITY, equipment_card, scope_items_card
from ui.common import load_data

data = load_data()

col_input, col_result = st.columns([1, 2])

# --- Input Panel ---
with col_input:
    # Card 1: Core Inputs (Required for ANY estimate)
    st.markdown("#### 1. Core Inputs")
    archetype_options = [
        '', 'refinery_bf', 'refinery_gf', 'onshore_petchem', 'integrated_petchem',
        'offshore_fpso', 'offshore_platform', 'pipeline_mainline', 'pipeline_complex',
        'lng_onshore', 'lng_terminal', 'oil_sands', 'onshore_conventional',
        'onshore_unconventional', 'ccs', 'ccs_gas_processing', 'renewable_diesel',
        'gas_processing', 'power_generation',
    ]
    archetype_labels = {
        '': '-- Select Archetype --',
        'refinery_bf': 'Refinery Brownfield',
        'refinery_gf': 'Refinery Greenfield',
        'onshore_petchem': 'Petrochemical (Onshore)',
        'integrated_petchem': 'Integrated Petrochemical',
        'offshore_fpso': 'Offshore FPSO',
        'offshore_platform': 'Offshore Platform',
        'pipeline_mainline': 'Pipeline (Mainline)',
        'pipeline_complex': 'Pipeline (Complex)',
        'lng_onshore': 'LNG (Onshore)',
        'lng_terminal': 'LNG Terminal',
        'oil_sands': 'Oil Sands',
        'onshore_conventional': 'Onshore Conventional',
        'onshore_unconventional': 'Onshore Unconventional',
        'ccs': 'Carbon Capture (CCS)',
        'ccs_gas_processing': 'CCS / Gas Processing',
        'renewable_diesel': 'Renewable Diesel',
        'gas_processing': 'Gas Processing',
        'power_generation': 'Power Generation',
    }

    archetype = st.selectbox(
        "Project Archetype",
        archetype_options,
        format_func=lambda x: archetype_labels.get(x, x),
        key="archetype",
    )

    process_domain = st.selectbox(
        "Process Domain",
        ['', 'chemicals', 'refining', 'offshore', 'pipeline', 'lng',
         'oil_sands', 'ccs', 'gas_processing', 'upstream_unconventional',
         'upstream_conventional', 'power'],
        format_func=lambda x: x.replace('_', ' ').title() if x else '-- Optional --',
        key="process_domain",
    )

    location = st.selectbox("Location (CP30 Region)", [''] + LOCATION_OPTIONS, key="location")
    basis_year = st.selectbox("Basis Year", [2024, 2025, 2026], key="basis_year")

    bf_gf = st.selectbox(
        "Scope Type",
        ['', 'greenfield', 'brownfield', 'expansion', 'modification'],
        format_func=lambda x: x.title() if x else '-- Optional --',
        key="bf_gf",
    )
    project_name = st.text_input("Project Name (optional)", key="project_name")

    core_ready = bool(archetype and location)

    st.divider()

    # Card 2: Equipment List (fragment, see top of file)
    equipment_card(core_ready)

    st.divider()

    # Card 3: Facility & Capacity (step 3)
    st.markdown("#### 3. Facility & Capacity")
    facility_choice = st.selectbox(
        "Facility Type",
        [''] + FACILITY_TYPE_OPTIONS + [_OTHER_FACILITY],
        format_func=lambda x: ('-- Select --' if x == '' else
                               'Other (type below)' if x == _OTHER_FACILITY else x),
        key="facility_type_choice",
        disabled=not core_ready,
        help="These are the facility types the calculators understand. "
             "'Other' lets you type a free name (Benchmark and Composite still run).",
    )
    if facility_choice == _OTHER_FACILITY:
        facility_type = st.text_input("Custom facility type", key="facility_type_custom",
                                      disabled=not core_ready)
    else:
        facility_type = facility_choice

    cap_col1, cap_col2 = st.columns(2)
    with cap_col1:
        capacity = st.number_input(
            "Primary Capacity", min_value=0.0, value=0.0,
            key="capacity", disabled=not core_ready,
        )
    with cap_col2:
        cap_unit = st.selectbox(
            "Unit",
            ['', 'KTA', 'BPD', 'KBPD', 'KBOPD', 'MMSCFD', 'MTPA', 'MTPA_CO2',
             'KBD', 'KBSD', 'KBD NGL', 'miles', 'km'],
            key="cap_unit", disabled=not core_ready,
        )

    # Pipeline-specific
    if archetype and 'pipeline' in archetype:
        st.markdown("**Pipeline Parameters:**")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            pipeline_length = st.number_input("Length (km)", min_value=0.0, value=0.0, key="pipe_len")
        with p_col2:
            pipeline_od = st.number_input("Diameter (inches)", min_value=0.0, value=36.0, key="pipe_od")
    else:
        pipeline_length = 0.0
        pipeline_od = 36.0

    # Offshore-specific
    if archetype and 'offshore' in archetype:
        st.markdown("**Offshore Parameters:**")
        topsides_wt = st.number_input(
            "Topsides Weight (tonnes)", min_value=0.0, value=0.0, key="topsides_wt"
        )
        water_depth = st.number_input(
            "Water Depth (m)", min_value=0.0, value=0.0, key="water_depth",
            help="Required for SURF estimation and depth-adjusted offshore costs.",
        )
        hull_type = st.selectbox(
            "Hull Type",
            ['FPSO_newbuild', 'FPSO_converted', 'semi_sub', 'jacket_shallow'],
            key="hull_type",
        )
    else:
        topsides_wt = 0.0
        water_depth = 0.0
        hull_type = 'FPSO_newbuild'

    # LNG-specific
    if archetype and 'lng' in archetype:
        lng_mtpa = st.number_input(
            "LNG Capacity (MTPA)", min_value=0.0, value=0.0, key="lng_mtpa",
        )
    else:
        lng_mtpa = 0.0

    st.divider()

    # Card 4: SURF Subsea Scope (step 4 - offshore only)
    is_offshore = bool(archetype and 'offshore' in archetype)
    if is_offshore:
        st.markdown("#### 4. SURF Subsea Scope")
        st.caption("Subsea equipment bottom-up (4/4 LOOCV ±30%). Offshore projects only.")
        if 'surf_trees' not in st.session_state:
            st.session_state.surf_trees = 0

        with st.expander("Define subsea scope for SURF estimate", expanded=False):
            surf_c1, surf_c2 = st.columns(2)
            with surf_c1:
                surf_trees = st.number_input(
                    "Subsea Trees", min_value=0, value=0, key="surf_trees_input",
                    help="Number of subsea trees (wells).",
                )
                surf_flowlines = st.number_input(
                    "Flowlines", min_value=0, value=0, key="surf_flowlines",
                    help="Number of flowline segments.",
                )
                surf_risers = st.number_input(
                    "Risers", min_value=0, value=0, key="surf_risers",
                    help="Steel catenary risers, top-tensioned risers, etc.",
                )
            with surf_c2:
                surf_manifolds = st.number_input(
                    "Manifolds", min_value=0, value=0, key="surf_manifolds",
                    help="Subsea manifolds.",
                )
                surf_umbilicals = st.number_input(
                    "Umbilicals", min_value=0, value=0, key="surf_umbilicals",
                    help="Control/power umbilicals.",
                )
                surf_water_depth = water_depth  # inherit from Card 3 offshore params
                st.metric("Water Depth (from Card 3)", f"{water_depth:,.0f} m")

            surf_has_scope = (surf_trees + surf_flowlines + surf_risers) > 0
    else:
        surf_trees = surf_flowlines = surf_risers = surf_manifolds = surf_umbilicals = 0
        surf_has_scope = False

    st.divider()

    # Card 5: Scope Items (fragment, see top of file)
    scope_items_card(core_ready)

    st.divider()

    # Run Button
    run_disabled = not core_ready
    run_clicked = st.button(
        "Run Screening Estimate",
        type="primary",
        disabled=run_disabled,
        width='stretch',
    )

# --- Results Panel ---
with col_result:
    if run_clicked and core_ready:
        scope = {
            'project_name': project_name or f'{archetype} screening',
            'archetype': archetype,
            'process_domain': process_domain or None,
            'location': location,
            'country': resolve_country({'location': location}),
            'basis_year': basis_year,
            'greenfield_brownfield': bf_gf or 'greenfield',
            'scope_type': bf_gf or 'greenfield',
            'facility_type': facility_type if facility_type else None,
            'primary_capacity': capacity if capacity > 0 else None,
            'capacity_unit': cap_unit,
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
            'equipment_list': st.session_state.equipment_items if st.session_state.equipment_items else None,
            'scope_items': st.session_state.scope_items if st.session_state.scope_items else None,
            'surf_scope': {
                'subsea_trees': {'generic': surf_trees} if surf_trees > 0 else {},
                'flowlines': [{'id': f'FL{i+1}', 'count': 1} for i in range(surf_flowlines)],
                'risers': [{'id': f'R{i+1}', 'count': 1} for i in range(surf_risers)],
                'manifolds': {'generic': surf_manifolds} if surf_manifolds > 0 else {},
                'umbilicals': [{'id': f'U{i+1}'} for i in range(surf_umbilicals)],
                'water_depth_m': water_depth if water_depth > 0 else 1500,
            } if surf_has_scope else None,
        }
        st.session_state.last_scope = scope
        st.session_state.last_results = screen_project(scope, data)

    if 'last_results' in st.session_state:
        results = st.session_state.last_results
        ens = results['ensemble']
        models = results['models']

        # --- 9-Model Readiness Panel (wireframe-style) ---
        st.markdown("#### Model Readiness")
        _MODEL_NEEDS = {
            'Benchmark': 'archetype + location + year',
            'EquipmentVector': 'equipment list (type + count)',
            'Calculator_Onshore': 'facility type + capacity',
            'Calculator_Offshore': 'topsides weight or KBPD',
            'Calculator_Pipeline': 'pipeline length + diameter',
            'Calculator_LNG': 'LNG capacity (MTPA)',
            'Unconventional': 'facility type (unconventional)',
            'Composite': 'at least 1 scope item',
            'SURF_User': 'SURF subsea scope',
            'OSBL_Estimate': 'ISBL from Calculator (auto)',
        }
        _ALL_MODELS = [  # fixed display order (a set reorders between runs)
            'Benchmark', 'EquipmentVector', 'Calculator_Onshore',
            'Calculator_Offshore', 'Calculator_Pipeline', 'Calculator_LNG',
            'Unconventional', 'Composite', 'SURF_User', 'OSBL_Estimate',
        ]
        for mid in _ALL_MODELS:
            mr = models.get(mid, {})
            fired = mr.get('can_fire', False)
            excluded = mr.get('excluded_by_rule', False)
            if fired and not excluded:
                est = mr.get('estimate_musd', 0)
                label = f"${est:,.0f}M" if est else "READY"
                st.markdown(
                    f'<div class="model-ready">&#9679; <b>{mid}</b> - {label}</div>',
                    unsafe_allow_html=True,
                )
            elif excluded:
                st.markdown(
                    f'<div class="model-not-ready">&#9675; <b>{mid}</b> - excluded (known failure for {archetype})</div>',
                    unsafe_allow_html=True,
                )
            else:
                needs = _MODEL_NEEDS.get(mid, 'missing inputs')
                st.markdown(
                    f'<div class="model-not-ready">&#9675; <b>{mid}</b> - <i>Needs: {needs}</i></div>',
                    unsafe_allow_html=True,
                )

        st.divider()

        # --- 3-Up Hero Result Cards (wireframe-style) ---
        st.markdown("### Estimate Results")
        hero1, hero2, hero3 = st.columns(3)
        with hero1:
            best = ens.get('best_estimate_musd')
            st.metric(
                "Best Estimate (P50)",
                f"${best:,.0f}M" if best else "N/A",
            )
        with hero2:
            lo = ens.get('range_low_musd')
            hi = ens.get('range_high_musd')
            st.metric(
                "Range (P20 - P80)",
                f"${lo:,.0f}M - ${hi:,.0f}M" if lo and hi else "N/A",
            )
        with hero3:
            conf = ens.get('confidence', 'N/A')
            conf_cls = 'conf-high' if 'HIGH' in conf else ('conf-med' if 'MED' in conf else 'conf-low')
            st.markdown(
                f"**Confidence**<br><span class='{conf_cls}'>{conf}</span>",
                unsafe_allow_html=True,
            )
            st.caption(ens.get('reasoning', ''))

        # Screening floor warning
        if results.get('screening_floor_note'):
            st.warning(results['screening_floor_note'])

        # Basis-year escalation note
        if results.get('basis_year_note'):
            st.info(results['basis_year_note'])

        # Model-level warnings (e.g. unverified pipeline calculator)
        for mid, mr in models.items():
            if mr.get('can_fire') and not mr.get('excluded_by_rule') and mr.get('warning'):
                st.warning(f"**{mid}:** {mr['warning']}")

        st.divider()

        # --- Per-Model Results ---
        st.markdown("#### Individual Model Estimates")
        fired_models = {k: v for k, v in models.items()
                        if v.get('can_fire') and not v.get('excluded_by_rule')}

        if fired_models:
            # Build comparison chart
            model_names = []
            estimates = []
            lows = []
            highs = []
            colors = []
            color_map = {
                'Calculator_Onshore': '#1f77b4', 'Calculator_Pipeline': '#2ca02c',
                'Calculator_LNG': '#ff7f0e', 'Calculator_Offshore': '#9467bd',
                'Benchmark': '#d62728', 'EquipmentVector': '#8c564b',
                'Unconventional': '#e377c2', 'Composite': '#7f7f7f',
                'SURF_User': '#17becf', 'OSBL_Estimate': '#bcbd22',
            }

            for mid, mr in fired_models.items():
                est = mr.get('estimate_musd', 0)
                lo = mr.get('estimate_low_musd', est * 0.5)
                hi = mr.get('estimate_high_musd', est * 1.5)
                model_names.append(mid)
                estimates.append(est)
                lows.append(est - lo)
                highs.append(hi - est)
                colors.append(color_map.get(mid, '#333'))

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=model_names, y=estimates,
                error_y=dict(
                    type='data',
                    symmetric=False,
                    array=highs,
                    arrayminus=lows,
                ),
                marker_color=colors,
                text=[f"${e:,.0f}M" for e in estimates],
                textposition='outside',
            ))
            fig.update_layout(
                title="Model Estimates Comparison",
                yaxis_title="TEC ($M USD)",
                height=350,
                margin=dict(t=40, b=40),
                showlegend=False,
            )
            # Add ensemble best estimate line
            if ens.get('best_estimate_musd'):
                fig.add_hline(
                    y=ens['best_estimate_musd'],
                    line_dash="dash", line_color="red",
                    annotation_text=f"Ensemble P50: ${ens['best_estimate_musd']:,.0f}M",
                )
            st.plotly_chart(fig, width='stretch')

            # Detail expanders per model
            for mid, mr in fired_models.items():
                with st.expander(f"{mid}: ${mr.get('estimate_musd', 0):,.0f}M"):
                    detail = mr.get('detail', {})
                    if detail:
                        st.json(detail)
                    if mr.get('analogues'):
                        st.markdown("**Top Analogues**")
                        ana_df = pd.DataFrame(mr['analogues'][:5])
                        if not ana_df.empty:
                            display_cols = [c for c in ['project_name', 'tec_musd_2024',
                                                        'similarity_score', 'country', 'archetype'] if c in ana_df.columns]
                            st.dataframe(ana_df[display_cols], width='stretch')
                    if mr.get('top_matches'):
                        st.markdown("**Top Equipment Matches**")
                        match_df = pd.DataFrame(mr['top_matches'][:5])
                        if not match_df.empty:
                            display_cols = [c for c in ['project_name', 'tec_musd_2024',
                                                        'similarity', 'archetype', 'country'] if c in match_df.columns]
                            st.dataframe(match_df[display_cols], width='stretch')
                    if mr.get('matched_items'):
                        st.markdown("**Matched Scope Items**")
                        for mi in mr['matched_items']:
                            item = mi.get('scope_item', {})
                            st.markdown(
                                f"- **{item.get('type', '')} / {item.get('facility_type', '')}** - "
                                f"{mi.get('n_chips', 0)} chips, ${mi.get('estimate_musd', 0):,.1f}M"
                            )
                    if mr.get('warning'):
                        st.warning(mr['warning'])

            st.divider()

        # --- Top Analogues Table ---
        st.markdown("#### Comparable Projects")
        analogues = results.get('analogues', [])
        if analogues:
            ana_df = pd.DataFrame(analogues)
            # Prefer escalated cost column if available
            cp30_info = results.get('cp30_escalation')
            if cp30_info:
                esc_col = f"tec_musd_{cp30_info['to_year']}"
                cost_label = f"TEC ($M, {cp30_info['to_year']})"
            else:
                esc_col = 'tec_musd_2024'
                cost_label = 'TEC ($M, 2024)'
            cost_col = esc_col if esc_col in ana_df.columns else 'tec_musd_2024'
            display_cols = [c for c in ['project_name', cost_col, 'similarity',
                                        'country', 'capacity', 'capacity_unit', 'process_domain', 'scope_type']
                            if c in ana_df.columns]
            st.dataframe(
                ana_df[display_cols].rename(columns={
                    cost_col: cost_label,
                    'project_name': 'Project',
                    'similarity': 'Match Score',
                }),
                width='stretch',
            )
        else:
            st.info("Run estimate with an archetype to see comparable projects.")

        # --- Bid Validation ---
        st.divider()
        st.markdown("#### Bid Validation")
        bid_col1, bid_col2, bid_col3 = st.columns([2, 1, 1])
        with bid_col1:
            bid_amount = st.number_input("Bid Amount ($M)", min_value=0.0, value=0.0, key="bid_amt")
        with bid_col2:
            bid_type = st.selectbox("Bid Type", ['TEC', 'EPC_lumpsum'], key="bid_type")
        with bid_col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Validate Bid"):
                if bid_amount > 0:
                    bid_result = validate_bid(results, bid_amount, bid_type)
                    verdict = bid_result['verdict']
                    if verdict == 'WITHIN_RANGE':
                        st.success(f"**{verdict}** - {bid_result['summary']}")
                    elif verdict == 'ABOVE_RANGE':
                        st.warning(f"**{verdict}** - {bid_result['summary']}")
                    elif verdict == 'BELOW_RANGE':
                        st.error(f"**{verdict}** - {bid_result['summary']}")
                    else:
                        st.info(bid_result.get('reason', 'Cannot assess'))

        # --- What-If Sensitivity Analysis ---
        st.divider()
        st.markdown("#### What-If Sensitivity")
        st.caption("Change one parameter and compare. Re-runs all models with the alternate value.")

        _WHATIF_PARAMS = {
            'primary_capacity': {'label': 'Primary Capacity', 'unit': cap_unit if 'last_scope' in st.session_state else '', 'step': 10.0},
            'length_km': {'label': 'Pipeline Length (km)', 'unit': 'km', 'step': 10.0},
            'od_inches': {'label': 'Pipeline Diameter (in)', 'unit': 'in', 'step': 2.0},
            'topsides_weight_te': {'label': 'Topsides Weight (te)', 'unit': 'te', 'step': 500.0},
            'water_depth_m': {'label': 'Water Depth (m)', 'unit': 'm', 'step': 100.0},
            'lng_capacity_mtpa': {'label': 'LNG Capacity (MTPA)', 'unit': 'MTPA', 'step': 0.5},
        }

        # Only show params that have a non-null value in the current scope
        last_scope = st.session_state.get('last_scope', {})
        active_params = {k: v for k, v in _WHATIF_PARAMS.items()
                         if last_scope.get(k) is not None and last_scope.get(k, 0) > 0}

        if active_params:
            with st.expander("Run sensitivity scenario", expanded=False):
                wi_col1, wi_col2, wi_col3 = st.columns([2, 2, 1])
                with wi_col1:
                    wi_param = st.selectbox(
                        "Parameter to change",
                        list(active_params.keys()),
                        format_func=lambda k: active_params[k]['label'],
                        key="wi_param",
                    )
                with wi_col2:
                    base_val = last_scope.get(wi_param, 0)
                    wi_alt = st.number_input(
                        f"Alternate value (base: {base_val:,.1f})",
                        min_value=0.0,
                        value=float(base_val),
                        step=active_params[wi_param]['step'],
                        key="wi_alt",
                    )
                with wi_col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    wi_run = st.button("Run What-If", key="wi_run")

                if wi_run and wi_alt != base_val:
                    # Build alternate scope
                    wi_scope = {**last_scope, wi_param: wi_alt}
                    wi_scope['project_name'] = f"{last_scope.get('project_name', '')} (what-if)"

                    # Propagate to secondary params if needed
                    if wi_param in ('topsides_weight_te', 'water_depth_m'):
                        sp = dict(wi_scope.get('secondary_params') or {})
                        sp[wi_param] = wi_alt
                        wi_scope['secondary_params'] = sp

                    wi_results = screen_project(wi_scope, data)
                    wi_ens = wi_results['ensemble']

                    base_est = ens.get('best_estimate_musd')
                    wi_est = wi_ens.get('best_estimate_musd')

                    if base_est and wi_est:
                        delta_musd = wi_est - base_est
                        delta_pct = (wi_est / base_est - 1) * 100

                        # Hero delta
                        d1, d2, d3 = st.columns(3)
                        with d1:
                            st.metric(
                                "Base P50",
                                f"${base_est:,.0f}M",
                            )
                        with d2:
                            st.metric(
                                "What-If P50",
                                f"${wi_est:,.0f}M",
                                delta=f"{delta_musd:+,.0f}M ({delta_pct:+.1f}%)",
                            )
                        with d3:
                            st.metric(
                                "Parameter Changed",
                                f"{wi_alt:,.1f}",
                                delta=f"{(wi_alt - base_val):+,.1f} {active_params[wi_param]['unit']} vs base",
                                delta_color="off",
                            )

                        # Per-model comparison table
                        rows = []
                        all_model_ids = set(list(models.keys()) + list(wi_results['models'].keys()))
                        for mid in sorted(all_model_ids):
                            bm = models.get(mid, {})
                            wm = wi_results['models'].get(mid, {})
                            b_fire = bm.get('can_fire', False) and not bm.get('excluded_by_rule', False)
                            w_fire = wm.get('can_fire', False) and not wm.get('excluded_by_rule', False)
                            b_est = bm.get('estimate_musd') if b_fire else None
                            w_est = wm.get('estimate_musd') if w_fire else None
                            if b_est or w_est:
                                m_delta = (w_est - b_est) if (b_est and w_est) else None
                                m_pct = ((w_est / b_est - 1) * 100) if (b_est and w_est and b_est > 0) else None
                                rows.append({
                                    'Model': mid,
                                    'Base ($M)': f"{b_est:,.0f}" if b_est else '-',
                                    'What-If ($M)': f"{w_est:,.0f}" if w_est else '-',
                                    'Delta ($M)': f"{m_delta:+,.0f}" if m_delta is not None else '-',
                                    'Delta (%)': f"{m_pct:+.1f}%" if m_pct is not None else '-',
                                })
                        if rows:
                            st.dataframe(
                                pd.DataFrame(rows),
                                width='stretch',
                                hide_index=True,
                            )
                    else:
                        st.warning("One or both scenarios produced no ensemble estimate - cannot compute delta.")
                elif wi_run and wi_alt == base_val:
                    st.info("Alternate value is the same as base - change the value to see a comparison.")
        else:
            st.info("No numeric parameters to vary. Add capacity, pipeline length, or other facility details to enable what-if analysis.")

        # --- HTML report download ---
        st.divider()
        report_html = generate_html_report(results)
        safe_name = "".join(
            c if c.isalnum() or c in ('-', '_') else '_'
            for c in str(results['scope'].get('project_name', 'estimate'))
        )[:60] or 'estimate'
        st.download_button(
            "Download HTML Report",
            data=report_html.encode('utf-8'),
            file_name=f"screening_{safe_name}.html",
            mime="text/html",
            key="dl_report",
        )

        # Disclaimer
        st.markdown(
            '<div class="disclaimer"><b>Disclaimer:</b> '
            + results.get('disclaimer', '') + '</div>',
            unsafe_allow_html=True,
        )
    else:
        # No results yet
        st.markdown("### Estimate Results")
        st.info(
            "Fill **Core Inputs** (archetype + location) and click **Run Screening Estimate** "
            "to see results. Add equipment lists, facility details, or SURF scope to unlock "
            "more models."
        )

        st.markdown("#### Progressive Unlock")
        st.markdown("""
| Step | User Action | Models Unlocked |
|------|-------------|-----------------|
| 1 | Archetype + Location + Year | **Benchmark** (analogue matching) |
| 2 | + Equipment List (type + count) | **EquipmentVector** (best broad - 66% ±30%) |
| 3 | + Facility Type + Capacity | **Calculator** (Onshore/Offshore/Pipeline/LNG) |
| 4 | + Subsea Scope (trees, flowlines, risers) | **SURF_User** (subsea component - offshore only) |
| 5 | + Scope Items (multi-select) | **Composite** (chip matching) |
| Auto | (runs when any Calculator fires) | **OSBL_Estimate** (indirect cost overlay) |
""")
