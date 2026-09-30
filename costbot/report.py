"""Self-contained HTML screening report (no external assets, prints cleanly).

Layout mirrors the Streamlit app: header with project meta, KPI cards,
flags, model estimates (inline SVG chart + table), per-model detail,
comparable projects, screening basis, method notes, disclaimer.
"""
import html as html_mod
from typing import Dict, List

from costbot.constants import ARCHETYPE_EXCLUSIONS
from costbot.labels import (ARCHETYPE_LABELS, CONFIDENCE_COLORS, ENSEMBLE_RULES, MODEL_SPECS,
                            ROLE_COLORS, archetype_label, model_label)
from costbot.screening import MODEL_ORDER, model_rows

REPORT_VERSION = "POC v1.1"

_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
     font-size:14px;line-height:1.5;color:#1F2933;background:#F4F6F9;padding:32px 16px}
.page{max-width:980px;margin:0 auto}
header{margin-bottom:20px}
h1{font-size:24px;font-weight:600;color:#1F3A5F;display:inline}
.badge{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;
       background:#E4EAF3;color:#1F3A5F;vertical-align:middle;margin-left:8px}
.badge.green{background:#DDF3E4;color:#116329}.badge.orange{background:#FFF1DB;color:#8A5300}
.badge.red{background:#FDE2E1;color:#8E1B12}.badge.gray{background:#E9EDF2;color:#4B5563}
.badge.blue{background:#E4EAF3;color:#1F3A5F}
.meta{color:#5F6B7A;font-size:13px;margin-top:6px}
.meta span+span::before{content:"·";margin:0 8px;color:#9AA5B1}
.card{background:#fff;border:1px solid #D9DFE7;border-radius:8px;padding:18px 20px;margin-bottom:16px}
.card h2{font-size:15px;font-weight:600;color:#1F3A5F;margin-bottom:12px}
.card h3{font-size:14px;font-weight:600;margin:14px 0 6px}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.kpi{background:#fff;border:1px solid #D9DFE7;border-radius:8px;padding:16px 18px}
.kpi .label{font-size:12px;color:#5F6B7A;margin-bottom:4px}
.kpi .value{font-size:26px;font-weight:600;color:#1F3A5F;line-height:1.2}
.kpi .sub{font-size:12px;color:#5F6B7A;margin-top:4px}
.flag{border-left:3px solid #E9A23B;background:#FFF8EB;padding:8px 12px;border-radius:0 6px 6px 0;
      margin-bottom:8px;font-size:13px}
.flag.red{border-color:#B42318;background:#FDF2F1}.flag.blue{border-color:#1F3A5F;background:#F0F4FA}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
th{text-align:left;font-weight:600;color:#5F6B7A;background:#F4F6F9;padding:7px 10px;border-bottom:1px solid #D9DFE7}
td{padding:7px 10px;border-bottom:1px solid #EEF1F5;vertical-align:top}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:#5F6B7A;margin:8px 0 4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.note{font-size:12px;color:#5F6B7A}
ul{margin:6px 0 0 18px}li{margin-bottom:4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
footer{color:#5F6B7A;font-size:12px;margin-top:8px;padding:0 4px}
.status{font-weight:600}.status.fired{color:#116329}.status.excluded{color:#8E1B12}.status.off{color:#9AA5B1}
@media print{body{background:#fff;padding:0}.card,.kpi{break-inside:avoid;box-shadow:none}
  .page{max-width:none}}
@media (max-width:720px){.kpis,.grid2{grid-template-columns:1fr}}
"""


def _esc(text) -> str:
    return '' if text is None else html_mod.escape(str(text))


def _musd(value, fallback='n/a') -> str:
    try:
        if value is None or value != value:
            return fallback
        return f"${float(value):,.0f}M"
    except (TypeError, ValueError):
        return fallback


def _fmt_value(v) -> str:
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, float):
        return f"{v:,.4g}" if abs(v) < 1000 else f"{v:,.0f}"
    return str(v)


def flatten_detail(detail: Dict) -> List[List[str]]:
    """Model `detail` dict -> [[field, value], ...] rows. One level of nesting
    is flattened to 'parent · child'; lists and deeper dicts are dropped."""
    rows = []
    for k, v in (detail or {}).items():
        if v is None or isinstance(v, list):
            continue
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if v2 is None or isinstance(v2, (list, dict)):
                    continue
                rows.append([f"{k} · {k2}", _fmt_value(v2)])
        else:
            rows.append([k, _fmt_value(v)])
    return rows


def _table(headers: List, rows: List[List], num_cols=()) -> str:
    th = ''.join(f'<th class="{"num" if i in num_cols else ""}">{_esc(h)}</th>' for i, h in enumerate(headers))
    body = ''
    for r in rows:
        body += '<tr>' + ''.join(
            f'<td class="{"num" if i in num_cols else ""}">{c if isinstance(c, _Raw) else _esc(c)}</td>'
            for i, c in enumerate(r)) + '</tr>'
    return f'<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


class _Raw(str):
    """Marker for pre-escaped HTML cell content."""


def _svg_chart(rows: List[Dict], p50) -> str:
    if not rows:
        return ''
    rows = sorted(rows, key=lambda r: -r['estimate'])
    xmax = max(max(r['high'] for r in rows), p50 or 0) * 1.08 or 1.0
    W, LW, RW, RH = 900, 210, 90, 34
    PW = W - LW - RW
    H = RH * len(rows) + 44

    def x(v):
        return LW + (v / xmax) * PW

    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Model estimates" '
           f'style="font-family:inherit;font-size:12px">']
    for i in range(6):
        v = xmax * i / 5
        out.append(f'<line x1="{x(v):.1f}" y1="6" x2="{x(v):.1f}" y2="{H-30}" stroke="#EEF1F5"/>')
        out.append(f'<text x="{x(v):.1f}" y="{H-12}" text-anchor="middle" fill="#5F6B7A">${v:,.0f}M</text>')
    for i, r in enumerate(rows):
        y = 8 + i * RH
        color = ROLE_COLORS.get(r['role'], '#1F3A5F')
        out.append(f'<rect x="{LW}" y="{y+6}" width="{max(1, x(r["estimate"])-LW):.1f}" height="20" rx="3" fill="{color}"/>')
        out.append(f'<line x1="{x(r["low"]):.1f}" y1="{y+16}" x2="{x(r["high"]):.1f}" y2="{y+16}" stroke="#4B5563" stroke-width="1.5"/>')
        for xx in (x(r['low']), x(r['high'])):
            out.append(f'<line x1="{xx:.1f}" y1="{y+11}" x2="{xx:.1f}" y2="{y+21}" stroke="#4B5563" stroke-width="1.5"/>')
        out.append(f'<text x="{LW-10}" y="{y+20}" text-anchor="end" fill="#1F2933">{_esc(model_label(r["model_id"]))}</text>')
        out.append(f'<text x="{W-RW+8}" y="{y+20}" fill="#1F2933" font-weight="600">{_musd(r["estimate"])}</text>')
    if p50:
        out.append(f'<line x1="{x(p50):.1f}" y1="2" x2="{x(p50):.1f}" y2="{H-30}" stroke="#B42318" stroke-width="2" stroke-dasharray="6 4"/>')
        out.append(f'<text x="{x(p50)+6:.1f}" y="{H-34}" fill="#B42318" font-weight="600">P50 {_musd(p50)}</text>')
    out.append('</svg>')
    return ''.join(out)


def _model_detail_block(mid: str, mr: Dict) -> str:
    parts = [f'<h3>{_esc(model_label(mid))} <span class="note">{_musd(mr.get("estimate_musd"))}, '
             f'range {_musd(mr.get("estimate_low_musd"))} to {_musd(mr.get("estimate_high_musd"))}</span></h3>']
    if mr.get('warning'):
        parts.append(f'<div class="flag">{_esc(mr["warning"])}</div>')
    if mr.get('note'):
        parts.append(f'<p class="note">{_esc(mr["note"])}</p>')
    kv = flatten_detail(mr.get('detail'))
    if kv:
        parts.append(_table(['Field', 'Value'], kv))
    if mr.get('analogues'):
        parts.append(_table(['Analogue', 'TEC ($M, 2024)', 'Similarity', 'Archetype', 'Scope type'],
                            [[a.get('project_name', ''), _musd(a.get('tec_musd_2024')),
                              f"{a.get('similarity_score', 0):.2f}", a.get('archetype', ''), a.get('scope_type', '')]
                             for a in mr['analogues'][:8]], num_cols=(1, 2)))
    if mr.get('top_matches'):
        parts.append(_table(['Closest equipment profile', 'TEC ($M, 2024)', 'Similarity', 'Archetype', 'Country'],
                            [[m.get('project_name', ''), _musd(m.get('tec_musd_2024')), f"{m.get('similarity', 0):.2f}",
                              m.get('archetype', ''), m.get('country', '')] for m in mr['top_matches'][:5]], num_cols=(1, 2)))
    if mr.get('matched_items'):
        parts.append(_table(['Scope item', 'Chips', 'Tier', 'Estimate ($M)'],
                            [[f"{mi['scope_item'].get('type', '')} / {mi['scope_item'].get('facility_type', '')}",
                              mi.get('n_chips', 0), mi.get('match_tier', ''), _musd(mi.get('estimate_musd', 0))]
                             for mi in mr['matched_items']], num_cols=(1, 3)))
    if mr.get('peer_names'):
        parts.append(f'<p class="note">Peers: {_esc(", ".join(str(p) for p in mr["peer_names"]))}</p>')
    return ''.join(parts)


def generate_html_report(results: Dict) -> str:
    """Build the HTML report from screen_project() output."""
    scope = results.get('scope', {}) or {}
    ens = results.get('ensemble', {}) or {}
    models = results.get('models', {}) or {}
    analogues = results.get('analogues', []) or []
    cp30 = results.get('cp30_escalation')
    archetype = scope.get('archetype') or ''
    best = ens.get('best_estimate_musd')
    conf = ens.get('confidence', 'n/a') or 'n/a'
    conf_color = CONFIDENCE_COLORS.get(conf, '#5F6B7A')
    project_name = scope.get('project_name') or 'Unnamed project'
    cap = scope.get('primary_capacity')
    cap_display = f"{cap:,.0f} {scope.get('capacity_unit', '') or ''}".strip() if cap else None

    meta = [archetype_label(archetype) or 'No archetype', scope.get('location') or 'No location',
            f"Basis year {scope.get('basis_year', 2024)}"]
    if cap_display:
        meta.insert(2, cap_display)
    meta_html = ''.join(f'<span>{_esc(m)}</span>' for m in meta)

    # --- KPIs ---
    kpis = f"""<div class="kpis">
<div class="kpi"><div class="label">Best estimate (P50)</div><div class="value">{_musd(best, 'Cannot estimate')}</div>
<div class="sub">{_esc(ens.get('reasoning', ''))}</div></div>
<div class="kpi"><div class="label">Range (P20 to P80)</div>
<div class="value">{(_musd(ens.get('range_low_musd')) + ' to ' + _musd(ens.get('range_high_musd'))) if best else 'n/a'}</div>
<div class="sub">{'Capped at 5x around the median' if ens.get('range_capped') else 'Widest span of the surviving models'}</div></div>
<div class="kpi"><div class="label">Confidence</div><div class="value" style="color:{conf_color}">{_esc(conf.replace('_', ' ').title())}</div>
<div class="sub">{ens.get('models_fired', 0)} model(s) fired, {len(ens.get('models_included') or [])} in the ensemble</div></div>
</div>"""

    # --- Flags ---
    flags = []
    if results.get('screening_floor_note'):
        flags.append(('red', results['screening_floor_note']))
    for g in ens.get('models_gated_out') or []:
        flags.append(('', f"{model_label(g[0])} gated out of the ensemble at {_musd(g[1])}: {g[2] if len(g) > 2 else ''}"))
    for mid, mr in models.items():
        if mr.get('can_fire') and not mr.get('excluded_by_rule') and mr.get('warning'):
            flags.append(('', f"{model_label(mid)}: {mr['warning']}"))
    if results.get('basis_year_note'):
        flags.append(('blue', results['basis_year_note']))
    bm = models.get('Benchmark') or {}
    alt = results.get('benchmark_alternate')
    if bm.get('can_fire') and bm.get('model_variant'):
        from costbot.models.benchmark import BENCHMARK_MODES
        used = BENCHMARK_MODES.get('engine' if bm['model_variant'].startswith('engine') else 'reference', bm['model_variant'])
        line = f"Analogue model used: {used}"
        if alt:
            other = BENCHMARK_MODES.get(alt['mode'], alt['mode'])
            line += (f". The other variant, {other}, gives {_musd(alt['estimate_musd'])} "
                     f"({alt.get('n_analogues') or 0} analogues)" if alt.get('can_fire')
                     else f". The other variant, {other}, did not fire ({alt.get('no_fire_reason')})")
        flags.append(('blue', line))
    if ens.get('confidence') == 'COMPONENT_ONLY':
        flags.append(('blue', 'Only a component estimate (subsea) is available; this is not a total project cost.'))
    flags_html = ''.join(f'<div class="flag {c}">{_esc(t)}</div>' for c, t in flags)
    flags_card = f'<div class="card"><h2>Flags</h2>{flags_html}</div>' if flags else ''

    # --- Model estimates: chart + status table ---
    rows = model_rows(results)
    legend = ''.join(f'<span><i style="background:{c}"></i>{_esc(r)}</span>' for r, c in ROLE_COLORS.items())
    role_by_id = {r['model_id']: r['role'] for r in rows}
    status_rows = []
    for mid in MODEL_ORDER:
        mr = models.get(mid)
        if mr is None:
            continue
        if mr.get('excluded_by_rule'):
            status = _Raw('<span class="status excluded">Excluded</span>')
            est, rng, why = '', '', mr.get('exclusion_reason', '')
        elif mr.get('can_fire'):
            status = _Raw('<span class="status fired">Fired</span>')
            est = _musd(mr.get('estimate_musd'))
            rng = f"{_musd(mr.get('estimate_low_musd'))} to {_musd(mr.get('estimate_high_musd'))}"
            why = role_by_id.get(mid, '')
        else:
            status = _Raw('<span class="status off">Not fired</span>')
            est, rng, why = '', '', mr.get('no_fire_reason', 'missing inputs')
        status_rows.append([model_label(mid), status, est, rng, why])
    estimates_card = f"""<div class="card"><h2>Model estimates</h2>
{_svg_chart(rows, best) if rows else '<p class="note">No model produced an estimate.</p>'}
<div class="legend">{legend}<span><i style="background:#B42318"></i>Ensemble P50</span><span>Whiskers: each model's own range</span></div>
{_table(['Model', 'Status', 'Estimate', 'Range', 'Role / reason'], status_rows, num_cols=(2, 3))}
</div>"""

    # --- Per-model detail ---
    detail_blocks = ''.join(_model_detail_block(mid, models[mid]) for mid in MODEL_ORDER
                            if mid in models and models[mid].get('can_fire') and not models[mid].get('excluded_by_rule'))
    detail_card = f'<div class="card"><h2>Model detail</h2>{detail_blocks}</div>' if detail_blocks else ''

    # --- Comparable projects ---
    cost_key = f"tec_musd_{cp30['to_year']}" if cp30 else 'tec_musd_2024'
    cost_label = f"TEC ($M, {cp30['to_year']})" if cp30 else 'TEC ($M, 2024)'
    ana_rows = [[a.get('project_name', ''), _musd(a.get(cost_key, a.get('tec_musd_2024'))),
                 f"{a.get('similarity', 0):.2f}", a.get('country', ''),
                 f"{a.get('capacity'):,.0f} {a.get('capacity_unit', '')}" if a.get('capacity') else '',
                 a.get('process_domain', ''), a.get('scope_type', '')] for a in analogues[:15]]
    comparables_card = f"""<div class="card"><h2>Comparable projects</h2>
{_table(['Project', cost_label, 'Match', 'Country', 'Capacity', 'Domain', 'Scope type'], ana_rows, num_cols=(1, 2))
 if ana_rows else '<p class="note">No comparable projects found for this archetype.</p>'}
</div>"""

    # --- Basis ---
    basis = [['Project', project_name], ['Archetype', f"{archetype_label(archetype)} ({archetype})" if archetype else ''],
             ['Location', scope.get('location', '')], ['Basis year', scope.get('basis_year', 2024)],
             ['Scope type', scope.get('scope_type', '')], ['Facility type', scope.get('facility_type') or ''],
             ['Capacity', cap_display or '']]
    if scope.get('length_km'):
        basis.append(['Pipeline', f"{scope['length_km']:,.0f} km, {scope.get('od_inches', '')} in"])
    if scope.get('topsides_weight_te'):
        basis.append(['Topsides weight', f"{scope['topsides_weight_te']:,.0f} t"])
    if scope.get('water_depth_m'):
        basis.append(['Water depth', f"{scope['water_depth_m']:,.0f} m"])
    if scope.get('lng_capacity_mtpa'):
        basis.append(['LNG capacity', f"{scope['lng_capacity_mtpa']} MTPA"])
    if scope.get('equipment_list'):
        basis.append(['Equipment', ', '.join(f"{e.get('type', '')} × {e.get('count', 1)}" for e in scope['equipment_list'])])
    if scope.get('scope_items'):
        basis.append(['Scope items', '; '.join(f"{i.get('type', '')}: {i.get('facility_type', '')}" for i in scope['scope_items'])])
    surf = scope.get('surf_scope') or {}
    if surf:
        trees = surf.get('subsea_trees') or {}
        basis.append(['Subsea scope', f"{sum(trees.values()) if isinstance(trees, dict) else 0} trees, "
                                      f"{len(surf.get('flowlines') or [])} flowlines, {len(surf.get('risers') or [])} risers"])
    basis_rows = [[k, v] for k, v in basis if v not in ('', None)]

    # --- Method ---
    excl = ARCHETYPE_EXCLUSIONS.get(archetype, [])
    excl_html = (f"<p>Excluded for {_esc(archetype_label(archetype))}: {_esc(', '.join(model_label(m) for m in excl))}.</p>"
                 if excl else '<p class="note">No archetype exclusion applies.</p>')
    rules_html = ''.join(f'<li>{_esc(r)}</li>' for r in ENSEMBLE_RULES)
    spec_rows = [[_Raw(f'{_esc(model_label(mid))} <span class="badge {colour}">{_esc(badge)}</span>'), method, acc]
                 for mid, method, badge, colour, _algo, acc, _libs in MODEL_SPECS]
    method_card = f"""<div class="card"><h2>Method</h2>
<div class="grid2"><div><h3>Ensemble rules</h3><ul>{rules_html}</ul><h3>Exclusions</h3>{excl_html}</div>
<div><h3>Screening basis</h3>{_table(['Input', 'Value'], basis_rows)}</div></div>
<h3>Model reference</h3>
<p class="note">Reported accuracy comes from the reference evaluation; it has not been reproduced on this engine.</p>
{_table(['Model', 'Method', 'Reported accuracy'], spec_rows)}
</div>"""

    disclaimer = results.get('disclaimer') or 'Screening estimate only. Not a basis of estimate.'
    timestamp = results.get('timestamp', '')

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Screening estimate: {_esc(project_name)}</title>
<style>{_CSS}</style></head>
<body><div class="page">
<header><h1>Screening estimate: {_esc(project_name)}</h1><span class="badge">{REPORT_VERSION}</span>
<div class="meta">{meta_html}</div></header>
{kpis}
{flags_card}
{estimates_card}
{detail_card}
{comparables_card}
{method_card}
<footer><p>{_esc(disclaimer)}</p><p>Generated {_esc(timestamp)} · GP screening cost estimator {REPORT_VERSION}</p></footer>
</div></body></html>"""
