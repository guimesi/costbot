"""Proposta B ("Console") main area: header row with scenario pills and the
report button, the estimate strip (P50, confidence, shared $ axis with a bid
marker, inline bid check) and two cards (model dot-plot, comparable projects).

Only presentation: the numbers come from `results` as produced by
costbot.screening.screen_project; widget keys match ui.results.
"""
from datetime import date

import streamlit as st

from costbot.screening import model_rows
from ui.common import DISCLAIMER, model_label, musd, musd_md
from ui.results import (bid_verdict, confidence_color, confidence_title, ensemble_spread, model_basis,
                        model_dot_plot, range_axis_chart, render_comparables, render_model_detail,
                        render_report_download, render_warnings, render_what_if)


def render_header(results, stale: bool) -> str:
    """Title row: date, project name, stale pill, scenario control, report button.
    Returns the selected scenario ('Base' or 'What-if')."""
    scope = results.get('scope', {})
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(width="content", gap=None):
            st.caption(f"Screening estimate · {date.today():%d %b %Y}")
            st.markdown(f"## {scope.get('project_name', 'Screening estimate')}"
                        + (" :orange-badge[:material/history: outdated]" if stale else ""))
        scenario = st.segmented_control("Scenario", ["Base", "What-if"], default="Base", key="b_scenario",
                                        label_visibility="collapsed",
                                        format_func=lambda s: s if s == "Base" else "+ What-if scenario")
        st.space()
        render_report_download(results, label="Report")
    return scenario or "Base"


def render_estimate_strip(results) -> None:
    ens = results['ensemble']
    best, lo, hi = ens.get('best_estimate_musd'), ens.get('range_low_musd'), ens.get('range_high_musd')
    conf = ens.get('confidence', 'n/a')
    year = results.get('scope', {}).get('basis_year', 2024)
    rows = model_rows(results)
    n_in, spread = ensemble_spread(results)

    with st.container(border=True):
        left, right = st.columns([1, 2.6], gap="large", vertical_alignment="center")
        with left:
            st.metric(f"P50 · TEC {year}", musd_md(best, 'Cannot estimate'),
                      help="Median of the model estimates that survived the spread gate.")
            st.markdown(f":{confidence_color(conf)}[● **{confidence_title(conf)} confidence**]")
        with right:
            with st.container(horizontal=True, vertical_alignment="center"):
                st.caption(f"P20 – P80 range: **{musd_md(lo)} – {musd_md(hi)}**" if best else "No ensemble range",
                           width="stretch")
                if n_in:
                    st.caption(f"{n_in} model{'s' if n_in != 1 else ''} in ensemble"
                               + (f" · spread {spread:.2f}×" if spread else ''))
            # Bid check widgets sit under the axis but must exist before the chart draws the marker
            chart_slot = st.empty()
            with st.container(horizontal=True, vertical_alignment="center"):
                st.markdown("**Bid check**")
                bid_amount = st.number_input("Bid ($M)", min_value=0.0, value=0.0, key="bid_amt", width=130,
                                             label_visibility="collapsed", placeholder="Bid $M")
                bid_type = st.segmented_control("Bid type", ['TEC', 'EPC_lumpsum'], default='TEC', key="bid_type",
                                                label_visibility="collapsed",
                                                format_func=lambda x: 'TEC' if x == 'TEC' else 'EPC lump sum')
                _verdict, line, _color = bid_verdict(results, bid_amount, bid_type)
                st.markdown(line)
            bid_marker = bid_amount if bid_amount and bid_amount > 0 else None
            if bid_marker and bid_type == 'EPC_lumpsum':
                bid_marker = bid_marker / 1.175  # same normalisation as validate_bid
            chart_slot.altair_chart(range_axis_chart(rows, best, lo, hi, bid=bid_marker, height=92))


def render_models_card(results) -> None:
    ens, models = results['ensemble'], results['models']
    best, lo, hi = ens.get('best_estimate_musd'), ens.get('range_low_musd'), ens.get('range_high_musd')
    rows = model_rows(results)
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**How the models land**", width="stretch")
            st.caption("Open a row for its detail and analogues")
        chart = model_dot_plot(rows, best, lo, hi)
        if chart is None:
            st.caption("No model produced an estimate.")
            return
        st.altair_chart(chart)
        for r in sorted(rows, key=lambda x: -x['estimate']):
            mr = models[r['model_id']]
            with st.expander(f"**{model_label(r['model_id'])}** · `{musd(r['estimate'])}` :gray[· {r['role']} · "
                             f"{model_basis(r['model_id'], mr)}]"):
                render_model_detail(r['model_id'], mr)
        n_in, spread = ensemble_spread(results)
        note = (f"Median of the {n_in} total-cost survivor{'s' if n_in != 1 else ''} of the 3× spread gate"
                + (f" (spread {spread:.2f}×)" if spread else '') + ". OSBL is indirect and reported separately.")
        if results.get('basis_year_note'):
            note += " " + results['basis_year_note']
        st.caption(":material/rule: " + note.replace('$', '\\$'))


def render_comparables_card(results, limit: int = 5) -> None:
    n = len(results.get('analogues', []))
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**Comparable projects**", width="stretch")
            st.caption(f"{n} found" if n else "")
        render_comparables(results, limit=limit, compact=True)
        if n > limit:
            with st.expander(f"All {n} comparable projects"):
                render_comparables(results, compact=True)


def render_results_b(results, data, stale: bool) -> None:
    scenario = render_header(results, stale)
    render_estimate_strip(results)
    render_warnings(results)
    if scenario == "What-if":
        with st.container(border=True):
            st.markdown("**:material/tune: What-if scenario**")
            render_what_if(results, data, framed=False)
    c1, c2 = st.columns([1.1, 1], gap="medium")
    with c1:
        render_models_card(results)
    with c2:
        render_comparables_card(results)
    st.caption(":material/info: " + DISCLAIMER)
