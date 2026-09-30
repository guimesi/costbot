"""Proposta A ("Guiada") results column: hero card with the shared $ axis,
an evidence card with tabs (Models, Comparable projects, Bid check, What-if)
and a preview of the closest comparable projects.

Only presentation: the numbers come from `results` as produced by
costbot.screening.screen_project; widgets reuse the keys of ui.results.
"""
import pandas as pd
import streamlit as st

from costbot.screening import model_rows
from ui.common import DISCLAIMER, model_label, musd_md
from ui.results import (confidence_color, confidence_title, ensemble_spread, model_basis, range_axis_chart,
                        render_bid_check, render_comparables, render_model_detail, render_report_download,
                        render_warnings, render_what_if)


def render_stale_banner() -> None:
    st.info("Inputs changed since this estimate. Run again to refresh.", icon=":material/history:")


def render_hero(results) -> None:
    ens = results['ensemble']
    best, lo, hi = ens.get('best_estimate_musd'), ens.get('range_low_musd'), ens.get('range_high_musd')
    conf = ens.get('confidence', 'n/a')
    scope = results.get('scope', {})
    rows = model_rows(results)
    n_in, spread = ensemble_spread(results)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 3.2, 2.2, 2], vertical_alignment="top")
        with c1:
            st.metric("Best estimate · P50", musd_md(best, 'Cannot estimate'),
                      help="Median of the model estimates that survived the spread gate.")
            st.caption(f"TEC, {scope.get('basis_year', 2024)} USD · {scope.get('project_name', '')}")
        with c2:
            # Smaller than the P50 on purpose (22px vs 44px in the mock); a metric would truncate it
            st.caption("Range · P20 to P80")
            st.markdown(f"### {musd_md(lo)} – {musd_md(hi)}" if best else "### n/a",
                        help="Widest span of the surviving models' own ranges, capped at 5x."
                             + (" Range was capped." if ens.get('range_capped') else ''))
            if best and lo and hi:
                st.caption(f"−{(1 - lo / best) * 100:.0f}% / +{(hi / best - 1) * 100:.0f}% around P50")
        with c3:
            st.caption("Confidence")
            st.badge(confidence_title(conf), color=confidence_color(conf), icon=":material/circle:")
            if n_in and spread:
                st.caption(f"{n_in} model{'s' if n_in != 1 else ''} agree within {spread:.1f}×")
            else:
                st.caption(ens.get('reasoning', ''))
        with c4:
            with st.container(horizontal_alignment="right"):
                render_report_download(results, label="HTML report")

        st.altair_chart(range_axis_chart(rows, best, lo, hi, height=96))

        n_out = sum(1 for r in rows if r['role'] == 'Gated out')
        n_comp = sum(1 for r in rows if r['role'] == 'Component')
        legend = [f":blue[●] In ensemble ({n_in})", ":orange[●] Indirect overlay, not in total", f":gray[●] Gated out ({n_out})"]
        if n_comp:
            legend.append(f":green[●] Component, reported separately ({n_comp})")
        with st.container(horizontal=True, vertical_alignment="center"):
            st.caption("  ·  ".join(legend), width="stretch")
            if results.get('basis_year_note'):
                st.caption(":material/trending_up: " + results['basis_year_note'].replace('$', '\\$'))


def _models_tab(results) -> None:
    ens, models = results['ensemble'], results['models']
    rows = model_rows(results)
    if not rows:
        st.caption("No model produced an estimate.")
        return
    table = pd.DataFrame([{
        'Model': model_label(r['model_id']),
        'Estimate': r['estimate'], 'Low': r['low'], 'High': r['high'],
        'Role · basis': f"{r['role']} · {model_basis(r['model_id'], models[r['model_id']])}",
    } for r in rows])
    st.caption("Select a row for its detail and analogues.")
    event = st.dataframe(table, hide_index=True, on_select="rerun", selection_mode="single-row", key="models_table",
                         column_config={
                             'Estimate': st.column_config.NumberColumn('Estimate ($M)', format='$%d'),
                             'Low': st.column_config.NumberColumn('Low ($M)', format='$%d'),
                             'High': st.column_config.NumberColumn('High ($M)', format='$%d'),
                             'Role · basis': st.column_config.TextColumn(width="large")})
    selected = event.selection.rows if event and event.selection else []
    if selected:
        r = rows[selected[0]]
        st.markdown(f"**{model_label(r['model_id'])}** :{'blue' if r['role'] == 'In ensemble' else 'gray'}-badge[{r['role']}]")
        render_model_detail(r['model_id'], models[r['model_id']])
    gated = ens.get('models_gated_out') or []
    n_in, spread = ensemble_spread(results)
    footer = (f"Ensemble: {n_in} total-cost model{'s' if n_in != 1 else ''} survived the 3× spread gate"
              + (f" (spread {spread:.2f}×)" if spread else '') + ". P50 is their median. Range is the widest of their "
              "ranges, capped at 5×. OSBL and SURF never enter the median."
              + (" Gated out: " + '; '.join(f"{model_label(g[0])} ({g[2]})" for g in gated) + '.' if gated else ''))
    st.caption(":material/rule: " + footer.replace('$', '\\$'))


def render_evidence(results, data) -> None:
    n_comp = len(results.get('analogues', []))
    with st.container(border=True):
        tab_models, tab_comps, tab_bid, tab_wi = st.tabs(["Models", f"Comparable projects ({n_comp})", "Bid check", "What-if"])
        with tab_models:
            _models_tab(results)
        with tab_comps:
            render_comparables(results, compact=True)
        with tab_bid:
            render_bid_check(results, framed=False)
        with tab_wi:
            render_what_if(results, data, framed=False)


def render_comparables_preview(results, limit: int = 4) -> None:
    n = len(results.get('analogues', []))
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**Closest comparable projects**", width="stretch")
            if n > limit:
                st.caption(f"All {n} in the Comparable projects tab")
        render_comparables(results, limit=limit, compact=True)


def render_results_a(results, data, stale: bool) -> None:
    if stale:
        render_stale_banner()
    render_hero(results)
    render_warnings(results)
    render_evidence(results, data)
    render_comparables_preview(results)
    st.caption(":material/info: " + DISCLAIMER)
