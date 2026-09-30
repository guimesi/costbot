"""Results panel of the estimator page: readiness checklist, KPI row, the
shared-axis range chart, per-model detail, comparable projects, bid check,
what-if, download.

The building blocks (render_bid_check, render_what_if, render_comparables,
render_model_detail, range_axis_chart, model_dot_plot, ...) are shared by
the three estimator layouts; render_results composes them for the current
one. Widget keys are the same in every layout so scripts/ui_test.py can
drive all of them.
"""
import math

import altair as alt
import pandas as pd
import streamlit as st

from costbot.labels import CONFIDENCE_COLORS, MODEL_SPECS, ROLE_COLORS
from costbot.report import flatten_detail, generate_html_report
from costbot.screening import model_rows, screen_project, validate_bid
from ui.common import DISCLAIMER, model_label, musd, musd_md

MONO = "IBM Plex Mono, JetBrains Mono, Menlo, monospace"
SANS = "IBM Plex Sans, Inter, sans-serif"
NAVY, MUTED, FAINT, BORDER, RED = '#1F3A5F', '#5F6B7A', '#9AA5B1', '#D9DFE7', '#B42318'

# Streamlit badge/markdown colour names for the confidence tiers (hex lives in CONFIDENCE_COLORS)
CONFIDENCE_BADGE = {'#1B7F4C': 'green', '#B86E00': 'orange', '#B42318': 'red', '#2A9D8F': 'blue'}
ROLE_BADGE = {'In ensemble': 'blue', 'Gated out': 'gray', 'Component': 'green', 'Indirect overlay': 'orange'}

_STATUS_ICON = {
    'ready': ':material/check_circle:',
    'needs': ':material/radio_button_unchecked:',
    'excluded': ':material/block:',
    'auto': ':material/autorenew:',
}


def confidence_color(conf: str) -> str:
    """Badge colour name ('green', 'orange', ...) for an ensemble confidence tier."""
    return CONFIDENCE_BADGE.get(CONFIDENCE_COLORS.get(conf, ''), 'gray')


def confidence_title(conf: str) -> str:
    return (conf or 'n/a').replace('_', ' ').title().replace('Medium-High', 'Medium-high')


def ensemble_spread(results) -> tuple:
    """(n in ensemble, max/min ratio of their estimates) for the 'n models agree within x' line."""
    ests = [r['estimate'] for r in model_rows(results) if r['role'] == 'In ensemble' and r['estimate']]
    if not ests:
        return 0, None
    return len(ests), (max(ests) / min(ests)) if min(ests) > 0 else None


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


# ----------------------------------------------------------------------------
# Shared-axis charts (design handoff, Sep 2026)
# ----------------------------------------------------------------------------
def axis_domain_max(*values) -> float:
    """0 -> ceil(max(values) x 1.15 / 300) x 300, so the four ticks land on round numbers."""
    top = max((float(v) for v in values if v), default=0.0)
    if top <= 0:
        return 300.0
    return math.ceil(top * 1.15 / 300.0) * 300.0


def _x(field: str, dmax: float):
    """x encoding with the shared domain. Every layer carries the same axis
    definition: Vega-Lite merges identical axes, but drops the axis when one
    layer says None and another does not."""
    ax = alt.Axis(values=[dmax * i / 4 for i in range(5)], labelExpr="'$' + format(datum.value, ',.0f') + 'M'",
                  labelFont=MONO, labelFontSize=10.5, labelColor=FAINT, domainColor=BORDER, tickColor=BORDER,
                  grid=False, title=None)
    return alt.X(field, scale=alt.Scale(domain=[0, dmax], nice=False), axis=ax, title=None)


def _model_frame(rows) -> pd.DataFrame:
    """One row per fired model with the fill/stroke colours the mocks use:
    navy filled in ensemble, gold outlined indirect, grey gated out, teal component."""
    recs = []
    for r in rows:
        color = ROLE_COLORS.get(r['role'], NAVY)
        indirect = r['role'] == 'Indirect overlay'
        recs.append({'model': model_label(r['model_id']), 'model_id': r['model_id'], 'estimate': r['estimate'],
                     'low': r['low'], 'high': r['high'], 'role': r['role'],
                     'fill': '#FFFFFF' if indirect else color, 'stroke': color,
                     'range': f"${r['low']:,.0f}M – ${r['high']:,.0f}M", 'est_label': f"${r['estimate']:,.0f}M"})
    return pd.DataFrame(recs)


_TOOLTIP = [alt.Tooltip('model:N', title='Model'), alt.Tooltip('est_label:N', title='Estimate'),
            alt.Tooltip('range:N', title='Range'), alt.Tooltip('role:N', title='Role')]


def range_axis_chart(rows, p50, lo, hi, bid=None, height: int = 90, bid_label: str = 'Bid'):
    """One shared $ axis: P20 to P80 band, P50 marker, one dot per model with
    its low to high whisker, optional dashed bid marker. Replaces the old
    per-model bar chart on every layout."""
    df = _model_frame(rows)
    dmax = axis_domain_max(hi, df['high'].max() if len(df) else 0, bid, p50)
    y = alt.Y('y:Q', scale=alt.Scale(domain=[0, 1]), axis=None, title=None)
    layers = []
    if lo and hi:
        band = pd.DataFrame({'x': [lo], 'x2': [hi], 'y': [0.34], 'y2': [0.66]})
        layers.append(alt.Chart(band).mark_rect(color=NAVY, opacity=0.12, cornerRadius=3)
                      .encode(x=_x('x:Q', dmax), x2='x2:Q', y=y, y2='y2:Q'))
        ends = pd.DataFrame({'x': [lo, hi], 'y': [0.16, 0.16], 't': [f'P20 ${lo:,.0f}', f'P80 ${hi:,.0f}']})
        layers.append(alt.Chart(ends).mark_text(font=MONO, fontSize=11, color=MUTED)
                      .encode(x=_x('x:Q', dmax), y=y, text='t:N'))
    if p50:
        p = pd.DataFrame({'x': [p50], 'y': [0.24], 'y2': [0.84], 't': ['P50'], 'yt': [0.95]})
        layers.append(alt.Chart(p).mark_rule(color=NAVY, strokeWidth=2)
                      .encode(x=_x('x:Q', dmax), y=y, y2='y2:Q'))
        layers.append(alt.Chart(p).mark_text(font=SANS, fontSize=11, fontWeight=600, color=NAVY)
                      .encode(x=_x('x:Q', dmax), y=alt.Y('yt:Q', scale=alt.Scale(domain=[0, 1]), axis=None), text='t:N'))
    if len(df):
        df['y'] = 0.5
        layers.append(alt.Chart(df).mark_rule(color=FAINT, strokeWidth=2)
                      .encode(x=_x('low:Q', dmax), x2='high:Q', y=y))
        layers.append(alt.Chart(df).mark_point(filled=True, size=120, strokeWidth=2)
                      .encode(x=_x('estimate:Q', dmax), y=y,
                              fill=alt.Fill('fill:N', scale=None, legend=None),
                              stroke=alt.Stroke('stroke:N', scale=None, legend=None), tooltip=_TOOLTIP))
    if bid:
        b = pd.DataFrame({'x': [bid], 'y': [0.08], 'y2': [0.92], 't': [f'{bid_label} ${bid:,.0f}M'], 'yt': [0.02]})
        layers.append(alt.Chart(b).mark_rule(color=RED, strokeWidth=2, strokeDash=[5, 4])
                      .encode(x=_x('x:Q', dmax), y=y, y2='y2:Q'))
        layers.append(alt.Chart(b).mark_text(font=MONO, fontSize=11, fontWeight=600, color=RED, baseline='top')
                      .encode(x=_x('x:Q', dmax), y=alt.Y('yt:Q', scale=alt.Scale(domain=[0, 1]), axis=None), text='t:N'))
    if not layers:
        layers.append(alt.Chart(pd.DataFrame({'x': [0], 'y': [0.5]})).mark_point(opacity=0)
                      .encode(x=_x('x:Q', dmax), y=y))
    return alt.layer(*layers).properties(height=height).configure_view(strokeWidth=0)


def model_dot_plot(rows, p50, lo, hi, row_height: int = 36):
    """Proposta B 'How the models land': one row per model on the same $
    axis, ghost P20 to P80 band, whisker, dot, estimate at the right."""
    df = _model_frame(rows)
    if not len(df):
        return None
    dmax = axis_domain_max(hi, df['high'].max(), p50)
    order = df.sort_values('estimate', ascending=False)['model'].tolist()
    df['xr'] = dmax
    y = alt.Y('model:N', sort=order, title=None,
              axis=alt.Axis(labelFont=SANS, labelFontSize=13, labelColor='#1F2933', labelLimit=170,
                            domain=False, ticks=False, grid=False, labelPadding=8))
    layers = []
    if lo and hi:
        layers.append(alt.Chart(pd.DataFrame({'x': [lo], 'x2': [hi]})).mark_rect(color=NAVY, opacity=0.06)
                      .encode(x=_x('x:Q', dmax), x2='x2:Q'))
    if p50:
        layers.append(alt.Chart(pd.DataFrame({'x': [p50]})).mark_rule(color=NAVY, strokeWidth=1.5, opacity=0.5)
                      .encode(x=_x('x:Q', dmax)))
    layers.append(alt.Chart(df).mark_rule(color=FAINT, strokeWidth=2).encode(x=_x('low:Q', dmax), x2='high:Q', y=y))
    layers.append(alt.Chart(df).mark_point(filled=True, size=100, strokeWidth=2)
                  .encode(x=_x('estimate:Q', dmax), y=y, fill=alt.Fill('fill:N', scale=None, legend=None),
                          stroke=alt.Stroke('stroke:N', scale=None, legend=None), tooltip=_TOOLTIP))
    layers.append(alt.Chart(df).mark_text(font=MONO, fontSize=13, fontWeight=500, align='right', dx=-2, color='#1F2933')
                  .encode(x=_x('xr:Q', dmax), y=y, text='est_label:N'))
    return alt.layer(*layers).properties(height=row_height * len(df) + 30).configure_view(strokeWidth=0)


def model_basis(mid: str, mr: dict) -> str:
    """One short 'how it got there' line per model, from the runner output."""
    d = mr.get('detail') or {}
    if mid == 'Calculator_Onshore' and d:
        return (f"ISBL {d.get('correlation_key', '')} scaling, EMMA {float(d.get('emma_factor', 0) or 0):.2f}, "
                f"TEC ×{float(d.get('tec_multiplier', 0) or 0):.2f} {d.get('scope_type_key', '')}")
    if mid == 'Benchmark':
        return f"{mr.get('n_analogues', 0)} analogues, spread {float(mr.get('spread_ratio', 0) or 0):.2f}×, size signal blended 50/50"
    if mid == 'EquipmentVector':
        return f"{mr.get('process_items', 0)} process items, top-5 cosine match against the equipment vectors"
    if mid == 'Composite':
        return f"{mr.get('n_items', 0)} scope item{'s' if mr.get('n_items', 0) != 1 else ''} matched against the chip library"
    if mid == 'OSBL_Estimate':
        return f"derived from the {model_label(mr.get('isbl_source', '')).lower()} ISBL, reported separately"
    if mid == 'SURF_User':
        return "bottom-up subsea component, reported separately"
    for spec in MODEL_SPECS:
        if spec[0] == mid:
            return spec[1]
    return ''


# ----------------------------------------------------------------------------
# Building blocks
# ----------------------------------------------------------------------------
def _detail_table(detail: dict):
    rows = flatten_detail(detail)
    if rows:
        st.dataframe(pd.DataFrame(rows, columns=['Field', 'Value']), hide_index=True,
                     height=min(420, 38 + 35 * len(rows)))


def render_model_detail(mid, mr):
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


def render_warnings(results) -> None:
    """Floor note, model warnings and the gated-out line. Shared by every layout."""
    ens, models = results['ensemble'], results['models']
    if results.get('screening_floor_note'):
        st.warning(results['screening_floor_note'].replace('$', '\\$'), icon=":material/warning:")
    for mid, mr in models.items():
        if mr.get('can_fire') and not mr.get('excluded_by_rule') and mr.get('warning'):
            st.warning(f"{model_label(mid)}: {mr['warning']}", icon=":material/warning:")
    if ens.get('models_gated_out'):
        st.caption("Gated out of the ensemble: " + '; '.join(f"{model_label(g[0])} at {musd_md(g[1])} ({g[2]})" for g in ens['models_gated_out']))


def comparables_frame(results, limit=None):
    """(DataFrame, cost column, cost label) for the comparable projects table, or (None, ...)."""
    analogues = results.get('analogues', [])
    if not analogues:
        return None, None, None
    df = pd.DataFrame(analogues if limit is None else analogues[:limit])
    cp30 = results.get('cp30_escalation')
    cost_col = f"tec_musd_{cp30['to_year']}" if cp30 and f"tec_musd_{cp30['to_year']}" in df.columns else 'tec_musd_2024'
    cost_label = f"TEC ($M, {cp30['to_year']})" if cp30 else 'TEC ($M, 2024)'
    return df, cost_col, cost_label


def render_comparables(results, limit=None, compact: bool = False) -> None:
    """Comparable projects table. `compact` keeps Project, TEC, Match, Country, Capacity, Scope (the mocks)."""
    df, cost_col, cost_label = comparables_frame(results, limit)
    if df is None:
        st.caption("No comparable projects found for this archetype.")
        return
    wanted = ['project_name', cost_col, 'similarity', 'country', 'capacity', 'capacity_unit', 'scope_type'] if compact else \
             ['project_name', cost_col, 'similarity', 'country', 'capacity', 'capacity_unit', 'process_domain', 'scope_type']
    cols = [c for c in wanted if c in df.columns]
    st.dataframe(df[cols], hide_index=True, column_config={
        'project_name': 'Project', cost_col: st.column_config.NumberColumn(cost_label, format='$%d'),
        'similarity': st.column_config.ProgressColumn('Match', min_value=0, max_value=1, format='%.2f'),
        'country': 'Country', 'capacity': st.column_config.NumberColumn('Capacity', format='%.0f'),
        'capacity_unit': 'Unit', 'process_domain': 'Domain', 'scope_type': 'Scope type'})


def bid_verdict(results, bid_amount, bid_type) -> tuple:
    """(verdict, markdown line, badge colour) for a bid, in the mocks' wording:
    'Within range · +17% vs P50'. Empty bid gives the grey placeholder."""
    if not bid_amount or bid_amount <= 0:
        return None, ":gray[Enter a bid to place it on the range]", 'gray'
    r = validate_bid(results, bid_amount, bid_type or 'TEC')
    v = r['verdict']
    if v == 'CANNOT_ASSESS':
        return v, f":gray[{r.get('reason', 'Cannot assess')}]", 'gray'
    pct = (r['ratio'] - 1) * 100
    if v == 'WITHIN_RANGE':
        return v, f":green[**Within range · {pct:+.0f}% vs P50**]", 'green'
    if v == 'ABOVE_RANGE':
        return v, f":orange[**Above range · {pct:+.0f}% vs P50**]", 'orange'
    return v, f":red[**Below range · {pct:+.0f}% vs P50**]", 'red'


def render_bid_check(results, framed: bool = True) -> None:
    """Bid amount + type + Check button, verdict as a status box. Keys: bid_amt, bid_type, bid_check."""
    with st.container(border=framed):
        if framed:
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


def render_what_if(results, data, framed: bool = True) -> None:
    """Change one numeric input and rerun every model. Keys: wi_param, wi_alt, wi_run."""
    ens, models = results['ensemble'], results['models']
    best = ens.get('best_estimate_musd')
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
    with st.container(border=framed):
        if framed:
            st.markdown("**:material/tune: What-if**")
        if not active:
            st.caption("Add a capacity, pipeline length or other numeric input to explore sensitivities.")
            return
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
                    st.metric("Base P50", musd_md(best), border=True)
                    st.metric("What-if P50", musd_md(wi_best), delta=f"{wi_best - best:+,.0f}M ({(wi_best / best - 1) * 100:+.1f}%)", border=True)
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


def render_report_download(results, label: str = "Download HTML report") -> None:
    safe = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in str(results['scope'].get('project_name', 'estimate')))[:60] or 'estimate'
    st.download_button(label, data=generate_html_report(results).encode('utf-8'),
                       file_name=f"screening_{safe}.html", mime="text/html", icon=":material/download:", key="dl_report")


def render_empty_state() -> None:
    """Shown on the results side before the first run."""
    with st.container(border=True):
        st.markdown("**:material/rocket_launch: How it unlocks**")
        st.markdown("""
1. **Archetype + location** unlock the benchmark against 503 completed projects.
2. **Equipment list** unlocks the equipment vector model, the best broad model.
3. **Facility type + capacity** unlock the calculators (onshore, offshore, pipeline, LNG).
4. **Subsea scope** (offshore only) unlocks the SURF component estimate.
5. **Scope items** unlock the composite chip model.

The OSBL overlay runs automatically whenever the onshore calculator produces an ISBL.
Press **Run screening estimate** once the readiness list shows what you need.
""")


# ----------------------------------------------------------------------------
# Current layout
# ----------------------------------------------------------------------------
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
        st.metric("Best estimate (P50)", musd_md(best, 'Cannot estimate'), border=True,
                  help="Median of the model estimates that survived the spread gate.")
        lo, hi = ens.get('range_low_musd'), ens.get('range_high_musd')
        # st.metric values are Markdown: two bare '$' would render as LaTeX
        st.metric("Range (P20 to P80)", f"{musd_md(lo)} to {musd_md(hi)}" if best else 'n/a', border=True,
                  help="Widest span of the surviving models' own ranges, capped at 5x." + (" Range was capped." if ens.get('range_capped') else ''))
        st.metric("Confidence", conf.replace('_', ' ').title(), border=True, help=ens.get('reasoning', ''))
    st.caption(ens.get('reasoning', ''))

    if results.get('basis_year_note'):
        st.caption(":material/trending_up: " + results['basis_year_note'].replace('$', '\\$'))
    render_warnings(results)

    # --- Model comparison on one shared axis ---
    rows = model_rows(results)
    if rows:
        with st.container(border=True):
            st.markdown("**:material/bar_chart: Model estimates**")
            st.altair_chart(range_axis_chart(rows, best, lo, hi, height=100))
            n_in = sum(1 for r in rows if r['role'] == 'In ensemble')
            n_out = sum(1 for r in rows if r['role'] == 'Gated out')
            st.caption(f":blue[●] In ensemble ({n_in}) · :orange[●] Indirect overlay, not in total · "
                       f":gray[●] Gated out ({n_out}) · P20 to P80 band, P50 line")
            tabs = st.tabs([model_label(r['model_id']) for r in rows])
            for tab, r in zip(tabs, rows):
                with tab:
                    render_model_detail(r['model_id'], models[r['model_id']])

    # --- Comparable projects ---
    with st.container(border=True):
        st.markdown("**:material/compare_arrows: Comparable projects**")
        render_comparables(results)

    render_bid_check(results)
    render_what_if(results, data)

    # --- Report + disclaimer ---
    with st.container(horizontal=True, vertical_alignment="center"):
        render_report_download(results)
        st.caption(DISCLAIMER)


__all__ = ['render_readiness', 'render_results', 'render_results', 'render_model_detail', 'render_warnings',
           'render_comparables', 'render_bid_check', 'render_what_if', 'render_report_download',
           'render_empty_state', 'range_axis_chart', 'model_dot_plot', 'model_basis', 'bid_verdict',
           'confidence_color', 'confidence_title', 'ensemble_spread', 'comparables_frame', 'musd']
