"""Self-contained HTML screening report."""
from typing import Dict, List, Optional, Any
from costbot.constants import ARCHETYPE_EXCLUSIONS


# ============================================================================
# HTML Report Generation (P6)
# ============================================================================

def generate_html_report(results: Dict) -> str:
    """Generate a self-contained HTML screening report from screen_project() output.

    Produces a 5-tab report: Basis, Model Results, Comparable Projects,
    Uncertainties, Disclaimer. Navy/green/amber palette, self-contained.
    """
    import html as html_mod

    def _g(val, fmt=",.0f", prefix="$", suffix="M", fallback="N/A"):
        if val is None:
            return fallback
        try:
            fval = float(val)
            if fval != fval:
                return fallback
            return f"{prefix}{fval:{fmt}}{suffix}"
        except (ValueError, TypeError):
            return fallback

    def _esc(text):
        if text is None:
            return ""
        return html_mod.escape(str(text))

    scope = results.get('scope', {})
    ens = results.get('ensemble', {})
    models = results.get('models', {})
    analogues = results.get('analogues', [])
    cp30_info = results.get('cp30_escalation')

    project_name = _esc(scope.get('project_name', 'Unnamed Project'))
    archetype = _esc(scope.get('archetype', '?'))
    location = _esc(scope.get('location', '?'))
    basis_year = scope.get('basis_year', 2024)
    timestamp = _esc(results.get('timestamp', ''))
    cap = scope.get('primary_capacity')
    cap_unit = _esc(scope.get('capacity_unit', ''))
    cap_display = f"{cap:,.0f} {cap_unit}" if cap else 'No capacity'

    conf = ens.get('confidence', 'N/A')
    conf_colors = {'HIGH': '#28A745', 'MEDIUM-HIGH': '#5CB85C', 'MEDIUM': '#FFC107',
                   'LOW': '#DC3545', 'CANNOT_ESTIMATE': '#DC3545', 'COMPONENT_ONLY': '#17A2B8'}
    conf_color = conf_colors.get(conf, '#999')

    # Hero values
    best = ens.get('best_estimate_musd')
    hero_est = _g(best) if best else '<span class="bad">CANNOT ESTIMATE</span>'
    hero_range = f"{_g(ens.get('range_low_musd'))} &ndash; {_g(ens.get('range_high_musd'))}" if best else 'N/A'
    hero_detail = _esc(ens.get('reasoning', ''))

    # --- TAB 1: Screening Basis ---
    scope_rows = ""
    scope_fields = [
        ('Project', project_name), ('Archetype', archetype), ('Location', location),
        ('Basis Year', str(basis_year)), ('Scope Type', _esc(scope.get('scope_type', ''))),
        ('Facility Type', _esc(scope.get('facility_type', '') or '')),
        ('Capacity', cap_display),
    ]
    if scope.get('length_km'):
        scope_fields.append(('Pipeline Length', f"{scope['length_km']:.1f} km"))
    if scope.get('topsides_weight_te'):
        scope_fields.append(('Topsides Weight', f"{scope['topsides_weight_te']:,.0f} te"))
    if scope.get('equipment_list'):
        eq_str = ", ".join(f"{e.get('type','')} x{e.get('count',1)}" for e in scope['equipment_list'])
        scope_fields.append(('Equipment List', _esc(eq_str)))
    for label, val in scope_fields:
        if val:
            scope_rows += f'<tr><td style="font-weight:600;width:180px">{label}</td><td>{val}</td></tr>'

    cp30_note = ""
    if cp30_info:
        cp30_note = (
            f'<div class="method-note">Pool-based estimates escalated from '
            f'{cp30_info["from_year"]} to {cp30_info["to_year"]} USD '
            f'(CP30 factor: {cp30_info["factor"]:.4f}).'
            f'</div>'
        )

    tab1 = f"""<h2>Screening Basis</h2>
<table>{scope_rows}</table>
{cp30_note}
<div class="method-note">
<b>Screening floor:</b> $20M. Projects below this threshold carry disproportionate uncertainty.<br>
<b>Ensemble range cap:</b> High/low ratio capped at 5x (symmetric in log-space around median).
</div>"""

    # --- TAB 2: Model Results ---
    model_rows = ""
    for mid in ['Benchmark', 'EquipmentVector', 'Calculator_Onshore', 'Calculator_Offshore',
                'Calculator_Pipeline', 'Calculator_LNG', 'Unconventional', 'Composite',
                'SURF_User', 'OSBL_Estimate']:
        mr = models.get(mid, {})
        fired = mr.get('can_fire', False)
        excluded = mr.get('excluded_by_rule', False)
        if excluded:
            status = '<span class="bad">EXCLUDED</span>'
            est_str = '&mdash;'
            range_str = _esc(mr.get('exclusion_reason', ''))[:80]
        elif fired:
            status = '<span class="good">FIRED</span>'
            est_str = _g(mr.get('estimate_musd'))
            lo = mr.get('estimate_low_musd')
            hi = mr.get('estimate_high_musd')
            range_str = f'{_g(lo)} &ndash; {_g(hi)}' if lo and hi else '&mdash;'
        else:
            status = '<span style="color:#999">Not fired</span>'
            est_str = '&mdash;'
            range_str = _esc(mr.get('no_fire_reason', 'missing inputs'))[:80]
        esc_tag = ''
        if mr.get('escalated_to_year'):
            esc_tag = f' <span style="font-size:10px;color:#666">({mr["escalated_to_year"]} USD)</span>'
        model_rows += f'<tr><td><b>{_esc(mid)}</b></td><td>{status}</td><td>{est_str}{esc_tag}</td><td>{range_str}</td></tr>'

    tab2 = f"""<h2>Model Results</h2>
<table>
<tr><th>Model</th><th>Status</th><th>Estimate</th><th>Range / Reason</th></tr>
{model_rows}
</table>"""

    # --- TAB 3: Comparable Projects ---
    ana_rows = ""
    cost_key = f"tec_musd_{cp30_info['to_year']}" if cp30_info else 'tec_musd_2024'
    cost_label = f"TEC ($M, {cp30_info['to_year']})" if cp30_info else 'TEC ($M, 2024)'
    for a in analogues[:15]:
        cost_val = a.get(cost_key, a.get('tec_musd_2024'))
        ana_rows += (
            f'<tr><td>{_esc(a.get("project_name", ""))}</td>'
            f'<td>{_g(cost_val)}</td>'
            f'<td>{a.get("similarity", 0):.3f}</td>'
            f'<td>{_esc(a.get("country", ""))}</td>'
            f'<td>{_esc(a.get("process_domain", ""))}</td></tr>'
        )
    if not ana_rows:
        ana_rows = '<tr><td colspan="5" style="color:#999">No comparable projects found</td></tr>'

    tab3 = f"""<h2>Comparable Projects</h2>
<table>
<tr><th>Project</th><th>{cost_label}</th><th>Similarity</th><th>Country</th><th>Domain</th></tr>
{ana_rows}
</table>"""

    # --- TAB 4: Uncertainties ---
    unc_items = ""
    if ens.get('spread_gated'):
        for g in ens.get('models_gated_out', []):
            unc_items += f'<li><b>{_esc(g[0])}</b> gated out at {_g(g[1])} &ndash; {_esc(g[2] if len(g) > 2 else "")}</li>'
    if ens.get('range_capped'):
        unc_items += '<li>Ensemble range was capped at 5x (high/low ratio exceeded limit)</li>'
    n_fired = ens.get('models_fired', 0)
    if n_fired <= 1:
        unc_items += f'<li>Only {n_fired} model(s) produced estimates &ndash; low redundancy</li>'
    for mid, mr in models.items():
        if mr.get('warning'):
            unc_items += f'<li><b>{_esc(mid)}:</b> {_esc(mr["warning"][:200])}</li>'
    if results.get('screening_floor_note'):
        unc_items += f'<li class="bad">{_esc(results["screening_floor_note"])}</li>'
    if not unc_items:
        unc_items = '<li>No significant uncertainties flagged</li>'

    tab4 = f"""<h2>Uncertainties &amp; Flags</h2>
<ul>{unc_items}</ul>"""

    # --- TAB 5: Disclaimer ---
    excl_items = ''.join(
        f'<li><b>{_esc(a)}</b>: {_esc(", ".join(ms))} excluded</li>'
        for a, ms in ARCHETYPE_EXCLUSIONS.items()
    ) or '<li>None</li>'
    tab5 = f"""<h2>Validation &amp; Disclaimer</h2>
<div class="method-note">
{_esc(results.get('disclaimer', 'Screening estimate only.'))}
</div>
<h3>Exclusion Rules Applied</h3>
<ul>{excl_items}</ul>
<h3>Model Accuracy Reference</h3>
<table>
<tr><th>Model</th><th>LOOCV Accuracy (&plusmn;30%)</th><th>Notes</th></tr>
<tr><td>Calculator_Onshore</td><td>79% (N=14)</td><td>Strongest: refinery brownfield</td></tr>
<tr><td>Calculator_Offshore</td><td>50% (N=2)</td><td>FPSO only</td></tr>
<tr><td>Calculator_Pipeline</td><td>67% (N=3)</td><td>Truth values under review</td></tr>
<tr><td>Calculator_LNG</td><td>0%</td><td class="bad">Miscalibrated &mdash; directional only</td></tr>
<tr><td>Benchmark</td><td>10% (regression)</td><td>Pool expansion under investigation</td></tr>
<tr><td>EquipmentVector</td><td class="good">66% (N=29)</td><td>Best broad model</td></tr>
<tr><td>Unconventional</td><td>70% (N=10)</td><td>Short-cycle projects</td></tr>
<tr><td>SURF_User</td><td>4/4 LOOCV</td><td>Guyana deepwater calibration</td></tr>
</table>
<p style="margin-top:16px;font-size:11px;color:#999">Generated {timestamp} | GP Screening Cost Estimator POC v1.0</p>"""

    # --- ASSEMBLE ---
    tab_names = ['Basis', 'Model Results', 'Comparable Projects', 'Uncertainties', 'Disclaimer']
    tab_contents = [tab1, tab2, tab3, tab4, tab5]

    tabs_html = ''.join(
        f'<div class="tab{" active" if i == 0 else ""}" onclick="switchTab({i})">{n}</div>'
        for i, n in enumerate(tab_names)
    )
    content_html = ''.join(
        f'<div class="tab-content{" active" if i == 0 else ""}">{c}</div>'
        for i, c in enumerate(tab_contents)
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Screening Estimate: {project_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;line-height:1.6;color:#333;background:#fff;padding:24px;max-width:1200px;margin:0 auto}}
h1{{font-size:22px;color:#003366;margin-bottom:4px}}
.subtitle{{font-size:13px;color:#666;margin-bottom:20px}}
.hero{{display:flex;gap:16px;margin:16px 0 24px 0}}
.hero-card{{flex:1;border:1px solid #e0e0e0;border-radius:6px;padding:20px;text-align:center;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,0.08)}}
.hero-card .label{{font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#666;margin-bottom:4px}}
.hero-card .value{{font-size:28px;font-weight:700}}
.hero-card .detail{{font-size:11px;color:#888;margin-top:2px}}
.confidence{{display:inline-block;background:{conf_color};color:#fff;font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px}}
.tabs{{display:flex;border-bottom:2px solid #e0e0e0;margin:20px 0 0 0;flex-wrap:wrap}}
.tab{{padding:8px 14px;cursor:pointer;font-size:12px;font-weight:500;color:#666;border-bottom:3px solid transparent;margin-bottom:-2px}}
.tab:hover{{color:#003366}}.tab.active{{color:#003366;border-bottom-color:#003366}}
.tab-content{{display:none;padding:20px 0}}.tab-content.active{{display:block}}
h2{{font-size:16px;color:#003366;margin:20px 0 8px 0;padding-bottom:4px;border-bottom:2px solid #003366}}
h3{{font-size:14px;color:#003366;margin:16px 0 6px 0}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:12px}}
th{{background:#003366;color:#fff;padding:8px 10px;text-align:left;font-size:11px}}
td{{padding:6px 10px;border-bottom:1px solid #eee}}
tr:hover{{background:#f8f9fa}}
.method-note{{background:#f0f4f8;border-left:3px solid #003366;padding:10px 14px;margin:12px 0;font-size:12px;border-radius:0 4px 4px 0}}
.good{{color:#28A745;font-weight:600}}.bad{{color:#DC3545;font-weight:600}}
ul{{margin:8px 0 8px 20px;font-size:12px}}li{{margin-bottom:4px}}
@media print{{.tabs{{display:none}}.tab-content{{display:block!important;page-break-inside:avoid}}}}
</style></head><body>

<h1>Screening Estimate: {project_name}</h1>
<p class="subtitle">{archetype} | {location} | {cap_display} | Basis Year {basis_year} | {timestamp}</p>

<div class="hero">
<div class="hero-card"><div class="label">Best Estimate (P50)</div>
<div class="value" style="color:#003366">{hero_est}</div>
<div class="detail">{hero_detail}</div></div>
<div class="hero-card"><div class="label">Estimate Range</div>
<div class="value" style="color:#003366;font-size:22px">{hero_range}</div>
<div class="detail">P20 &ndash; P80</div></div>
<div class="hero-card"><div class="label">Confidence</div>
<div class="value"><span class="confidence">{_esc(conf)}</span></div>
<div class="detail">{_esc(str(ens.get('reasoning', '')))}</div></div>
</div>

<div class="tabs">{tabs_html}</div>
{content_html}

<script>
function switchTab(n){{
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active', i===n));
  document.querySelectorAll('.tab-content').forEach((c,i)=>c.classList.toggle('active', i===n));
}}
</script>
</body></html>"""

    return html
