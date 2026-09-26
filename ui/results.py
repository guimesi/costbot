"""Results panel of the estimator page: readiness checklist, KPI row, model
chart, per-model detail, comparable projects, bid check, what-if, download."""
import altair as alt
import pandas as pd
import streamlit as st

from costbot.labels import ROLE_COLORS
from costbot.report import flatten_detail, generate_html_report
from costbot.screening import model_rows, screen_project, validate_bid
from ui.common import DISCLAIMER, model_label, musd, musd_md

_STATUS_ICON = {
    'ready': ':material/check_circle:',
    'needs': ':material/radio_button_unchecked:',
    'excluded': ':material/block:',
    'auto': ':material/autorenew:',
}


def render_readiness(rows, core_ready: bool) -> None:
    """Live checklist: which models would fire with the current inputs."""
    with st.container(border=True):
        st.markdown("**:material/checklist: Model readiness**")
        if not core_ready:
            st.caption("Pick an archetype and a location to see which models can run.")
            return
        visible = [r for r in rows if r['status'] != 'not_routed']
        n_ready = sum(1 for r in visible if r['status'] == 'ready')
        st.caption(f"{n_ready} of {len(visible)} eligible models ready. Others light up as you add inputs.")
        with st.container(gap=None):
            for r in visible:
                label = model_label(r['model_id'])
                s = r['status']
                if s == 'ready':
                    badge = ':green-badge[Ready]' + (' :blue-badge[automatic]' if r.get('auto') else '')
                elif s == 'excluded':
                    badge = ':red-badge[Excluded for this archetype]'
                elif s == 'auto':
                    badge = f':gray-badge[Needs {r["needs"]}]'
                else:
                    badge = f':gray-badge[Needs {r["needs"]}]'
                st.markdown(f"{_STATUS_ICON[s]} {label} {badge}")


def _model_chart(rows, p50):
    df = pd.DataFrame([{**r, 'model': model_label(r['model_id'])} for r in rows])
    order = df.sort_values('estimate', ascending=False)['model'].tolist()
    base = alt.Chart(df).encode(y=alt.Y('model:N', sort=order, title=None, axis=alt.Axis(labelLimit=220)))
    bars = base.mark_bar(size=18).encode(
        x=alt.X('estimate:Q', title='TEC ($M)', axis=alt.Axis(format='$,.0f')),
        color=alt.Color('role:N', title=None,
                        scale=alt.Scale(domain=list(ROLE_COLORS), range=list(ROLE_COLORS.values())),
                        legend=alt.Legend(orient='bottom')),
        tooltip=[alt.Tooltip('model:N', title='Model'), alt.Tooltip('estimate:Q', title='Estimate ($M)', format=',.0f'),
                 alt.Tooltip('low:Q', title='Low ($M)', format=',.0f'), alt.Tooltip('high:Q', title='High ($M)', format=',.0f'),
                 alt.Tooltip('role:N', title='Role')],
    )
    whiskers = base.mark_rule(color='#5F6B7A', strokeWidth=1.5).encode(x='low:Q', x2='high:Q')
    layers = [bars, whiskers]
    if p50:
        rule = alt.Chart(pd.DataFrame({'p50': [p50]})).mark_rule(color='#B42318', strokeDash=[6, 4], strokeWidth=2).encode(x='p50:Q')
        layers.append(rule)
    return alt.layer(*layers).properties(height=max(160, 34 * len(rows) + 60))


def _detail_table(detail: dict):
    rows = flatten_detail(detail)
    if rows:
        st.dataframe(pd.DataFrame(rows, columns=['Field', 'Value']), hide_index=True,
                     height=min(420, 38 + 35 * len(rows)))


def _render_model_detail(mid, mr):
    st.markdown(f"**{musd_md(mr.get('estimate_musd'))}**  ·  range {musd_md(mr.get('estimate_low_musd'))} "
                f"to {musd_md(mr.get('estimate_high_musd'))}")
    if mr.get('warning'):
        st.warning(mr['warning'], icon=":material/warning:")
    if mr.get('note'):
        st.caption(mr['note'])
    if mr.get('detail'):
        _detail_table(mr['detail'])
    if mr.get('analogues'):
        st.caption("Analogues used")
        df = pd.DataFrame(mr['analogues'][:10])
        cols = [c for c in ['project_name', 'tec_musd_2024', 'similarity_score', 'archetype', 'scope_type'] if c in df.columns]
        st.dataframe(df[cols], hide_index=True, column_config={
            'project_name': 'Project', 'tec_musd_2024': st.column_config.NumberColumn('TEC ($M, 2024)', format='$%d'),
            'similarity_score': st.column_config.ProgressColumn('Similarity', min_value=0, max_value=1, format='%.2f'),
            'archetype': 'Archetype', 'scope_type': 'Scope type'})
    if mr.get('top_matches'):
        st.caption("Closest equipment profiles")
        df = pd.DataFrame(mr['top_matches'][:5])
        cols = [c for c in ['project_name', 'tec_musd_2024', 'similarity', 'archetype', 'country', 'total_items'] if c in df.columns]
        st.dataframe(df[cols], hide_index=True, column_config={
            'project_name': 'Project', 'tec_musd_2024': st.column_config.NumberColumn('TEC ($M, 2024)', format='$%d'),
            'similarity': st.column_config.ProgressColumn('Similarity', min_value=0, max_value=1, format='%.2f'),
            'archetype': 'Archetype', 'country': 'Country', 'total_items': 'Items'})
    if mr.get('unresolved_equipment'):
        st.caption("Not recognised: " + ', '.join(mr['unresolved_equipment']))
    if mr.get('matched_items'):
        st.caption("Scope items matched")
        rows = [{'Item': f"{mi['scope_item'].get('type', '')} / {mi['scope_item'].get('facility_type', '')}",
                 'Chips': mi.get('n_chips', 0), 'Tier': mi.get('match_tier', ''),
                 'Estimate ($M)': mi.get('estimate_musd', 0)} for mi in mr['matched_items']]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    if mr.get('peer_names'):
        st.caption("Peers: " + ', '.join(str(p) for p in mr['peer_names']))


def render_results(results, data, stale: bool) -> None:
    ens = results['ensemble']
    models = results['models']
    best = ens.get('best_estimate_musd')
    conf = ens.get('confidence', 'n/a')

    if stale:
        st.info("Inputs changed since this estimate was run. Press **Run screening estimate** to refresh.",
                icon=":material/history:")

    # --- KPI row ---
    with st.container(horizontal=True):
        st.metric("Best estimate (P50)", musd(best, 'Cannot estimate'), border=True,
                  help="Median of the model estimates that survived the spread gate.")
        lo, hi = ens.get('range_low_musd'), ens.get('range_high_musd')
        st.metric("Range (P20 to P80)", f"{musd(lo)} to {musd(hi)}" if best else 'n/a', border=True,
                  help="Widest span of the surviving models' own ranges, capped at 5x." + (" Range was capped." if ens.get('range_capped') else ''))
        st.metric("Confidence", conf.replace('_', ' ').title(), border=True, help=ens.get('reasoning', ''))
    st.caption(ens.get('reasoning', ''))

    if results.get('screening_floor_note'):
        st.warning(results['screening_floor_note'].replace('$', '\\$'), icon=":material/warning:")
    if results.get('basis_year_note'):
        st.caption(":material/trending_up: " + results['basis_year_note'].replace('$', '\\$'))
    for mid, mr in models.items():
        if mr.get('can_fire') and not mr.get('excluded_by_rule') and mr.get('warning'):
            st.warning(f"{model_label(mid)}: {mr['warning']}", icon=":material/warning:")
    if ens.get('models_gated_out'):
        st.caption("Gated out of the ensemble: " + '; '.join(f"{model_label(g[0])} at {musd_md(g[1])} ({g[2]})" for g in ens['models_gated_out']))

    # --- Model comparison ---
    rows = model_rows(results)
    if rows:
        with st.container(border=True):
            st.markdown("**:material/bar_chart: Model estimates**")
            st.altair_chart(_model_chart(rows, best))
            tabs = st.tabs([model_label(r['model_id']) for r in rows])
            for tab, r in zip(tabs, rows):
                with tab:
                    _render_model_detail(r['model_id'], models[r['model_id']])

    # --- Comparable projects ---
    analogues = results.get('analogues', [])
    with st.container(border=True):
        st.markdown("**:material/compare_arrows: Comparable projects**")
        if analogues:
            df = pd.DataFrame(analogues)
            cp30 = results.get('cp30_escalation')
            cost_col = f"tec_musd_{cp30['to_year']}" if cp30 and f"tec_musd_{cp30['to_year']}" in df.columns else 'tec_musd_2024'
            cost_label = f"TEC ($M, {cp30['to_year']})" if cp30 else 'TEC ($M, 2024)'
            cols = [c for c in ['project_name', cost_col, 'similarity', 'country', 'capacity', 'capacity_unit', 'process_domain', 'scope_type'] if c in df.columns]
            st.dataframe(df[cols], hide_index=True, column_config={
                'project_name': 'Project', cost_col: st.column_config.NumberColumn(cost_label, format='$%d'),
                'similarity': st.column_config.ProgressColumn('Match', min_value=0, max_value=1, format='%.2f'),
                'country': 'Country', 'capacity': st.column_config.NumberColumn('Capacity', format='%.0f'),
                'capacity_unit': 'Unit', 'process_domain': 'Domain', 'scope_type': 'Scope type'})
        else:
            st.caption("No comparable projects found for this archetype.")

    # --- Bid check ---
    with st.container(border=True):
        st.markdown("**:material/request_quote: Bid check**")
        st.caption("Compare a contractor bid with the screening range.")
        with st.container(horizontal=True, vertical_alignment="bottom"):
            bid_amount = st.number_input("Bid amount ($M)", min_value=0.0, value=0.0, key="bid_amt", width=180)
            bid_type = st.segmented_control("Bid type", ['TEC', 'EPC_lumpsum'], default='TEC', key="bid_type",
                                            format_func=lambda x: 'TEC' if x == 'TEC' else 'EPC lump sum')
            check = st.button("Check bid", icon=":material/fact_check:", key="bid_check")
        if check:
            if bid_amount > 0:
                r = validate_bid(results, bid_amount, bid_type or 'TEC')
                v = r['verdict']
                if v == 'WITHIN_RANGE':
                    st.success(f"Within range. {r['summary']}", icon=":material/check_circle:")
                elif v == 'ABOVE_RANGE':
                    st.warning(f"Above range. {r['summary']}", icon=":material/arrow_upward:")
                elif v == 'BELOW_RANGE':
                    st.error(f"Below range. {r['summary']}", icon=":material/arrow_downward:")
                else:
                    st.caption(r.get('reason', 'Cannot assess'))
            else:
                st.caption("Enter a bid amount first.")

    # --- What-if ---
    last_scope = st.session_state.get('last_scope', {})
    params = {
        'primary_capacity': ('Primary capacity', last_scope.get('capacity_unit') or '', 10.0),
        'length_km': ('Pipeline length', 'km', 10.0),
        'od_inches': ('Pipeline diameter', 'in', 2.0),
        'topsides_weight_te': ('Topsides weight', 'te', 500.0),
        'water_depth_m': ('Water depth', 'm', 100.0),
        'lng_capacity_mtpa': ('LNG capacity', 'MTPA', 0.5),
    }
    active = {k: v for k, v in params.items() if last_scope.get(k) not in (None, 0, 0.0)}
    with st.container(border=True):
        st.markdown("**:material/tune: What-if**")
        if not active:
            st.caption("Add a capacity, pipeline length or other numeric input to explore sensitivities.")
        else:
            st.caption("Change one number and rerun every model with it.")
            with st.container(horizontal=True, vertical_alignment="bottom"):
                wi_param = st.selectbox("Parameter", list(active), format_func=lambda k: active[k][0], key="wi_param")
                base_val = float(last_scope.get(wi_param, 0))
                wi_alt = st.number_input(f"New value (now {base_val:,.1f} {active[wi_param][1]})", min_value=0.0,
                                         value=base_val, step=active[wi_param][2], key="wi_alt")
                wi_run = st.button("Run what-if", icon=":material/play_arrow:", key="wi_run")
            if wi_run and wi_alt != base_val:
                wi_scope = {**last_scope, wi_param: wi_alt, 'project_name': f"{last_scope.get('project_name', '')} (what-if)"}
                if wi_param in ('topsides_weight_te', 'water_depth_m'):
                    sp = dict(wi_scope.get('secondary_params') or {})
                    sp[wi_param] = wi_alt
                    wi_scope['secondary_params'] = sp
                wi = screen_project(wi_scope, data)
                wi_best = wi['ensemble'].get('best_estimate_musd')
                if best and wi_best:
                    with st.container(horizontal=True):
                        st.metric("Base P50", musd(best), border=True)
                        st.metric("What-if P50", musd(wi_best), delta=f"{wi_best - best:+,.0f}M ({(wi_best / best - 1) * 100:+.1f}%)", border=True)
                        st.metric(active[wi_param][0], f"{wi_alt:,.1f} {active[wi_param][1]}",
                                  delta=f"{wi_alt - base_val:+,.1f} vs base", delta_color="off", border=True)
                    rows = []
                    for mid in sorted(set(models) | set(wi['models'])):
                        b, w = models.get(mid, {}), wi['models'].get(mid, {})
                        b_est = b.get('estimate_musd') if b.get('can_fire') and not b.get('excluded_by_rule') else None
                        w_est = w.get('estimate_musd') if w.get('can_fire') and not w.get('excluded_by_rule') else None
                        if b_est or w_est:
                            rows.append({'Model': model_label(mid), 'Base ($M)': b_est, 'What-if ($M)': w_est,
                                         'Delta (%)': ((w_est / b_est - 1) * 100) if (b_est and w_est) else None})
                    st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
                        'Base ($M)': st.column_config.NumberColumn(format='$%d'),
                        'What-if ($M)': st.column_config.NumberColumn(format='$%d'),
                        'Delta (%)': st.column_config.NumberColumn(format='%+.1f%%')})
                else:
                    st.warning("One of the scenarios produced no ensemble estimate.", icon=":material/warning:")
            elif wi_run:
                st.caption("Change the value to see a comparison.")

    # --- Report + disclaimer ---
    with st.container(horizontal=True, vertical_alignment="center"):
        safe = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in str(results['scope'].get('project_name', 'estimate')))[:60] or 'estimate'
        st.download_button("Download HTML report", data=generate_html_report(results).encode('utf-8'),
                           file_name=f"screening_{safe}.html", mime="text/html", icon=":material/download:", key="dl_report")
        st.caption(DISCLAIMER)
