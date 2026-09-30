"""Scope assembly and input summaries shared by the estimator page variants
(current, Proposta A, Proposta B). The widgets differ per layout; the scope
dict handed to the engine and the one-line summaries do not."""
from costbot.constants import ISBL_CORRELATIONS, _FACILITY_ALIASES, resolve_country
from costbot.labels import ARCHETYPE_LABELS, model_label

CAPACITY_UNITS = ['KTA', 'BPD', 'KBPD', 'KBOPD', 'MMSCFD', 'MTPA', 'MTPA_CO2', 'KBD', 'KBSD', 'KBD NGL', 'miles', 'km']
HULL_TYPES = ['FPSO_newbuild', 'FPSO_converted', 'semi_sub', 'jacket_shallow']
PROCESS_DOMAINS = ['chemicals', 'refining', 'offshore', 'pipeline', 'lng', 'oil_sands', 'ccs',
                   'gas_processing', 'upstream_unconventional', 'upstream_conventional', 'power']
SCOPE_TYPES = ['greenfield', 'brownfield', 'expansion', 'modification']

# Short chip labels for the compact readiness strips (A) and group chips (B)
SHORT_MODEL_LABELS = {
    'Benchmark': 'Benchmark', 'EquipmentVector': 'Equipment vector', 'Calculator_Onshore': 'Onshore calc',
    'Calculator_Offshore': 'Offshore calc', 'Calculator_Pipeline': 'Pipeline calc', 'Calculator_LNG': 'LNG calc',
    'Unconventional': 'Unconventional', 'Composite': 'Composite', 'SURF_User': 'SURF', 'OSBL_Estimate': 'OSBL overlay',
}


def short_label(model_id: str) -> str:
    return SHORT_MODEL_LABELS.get(model_id, model_label(model_id))


def build_scope(*, archetype='', location=None, basis_year=None, bf_gf=None, project_name='', process_domain=None,
                facility_type=None, capacity=0.0, cap_unit=None, pipeline_length=0.0, pipeline_od=36.0,
                topsides_wt=0.0, water_depth=0.0, hull_type='FPSO_newbuild', lng_mtpa=0.0,
                surf_trees=0, surf_flowlines=0, surf_risers=0, surf_manifolds=0, surf_umbilicals=0,
                equipment_items=None, scope_items=None) -> dict:
    """The scope dict `screen_project` expects, from raw widget values.
    Zero and empty widget values become None so the readiness gates and
    the runners see 'missing', not 'zero'."""
    archetype = archetype or ''
    surf_has_scope = (surf_trees + surf_flowlines + surf_risers) > 0
    return {
        'project_name': project_name or (f'{archetype} screening' if archetype else 'screening'),
        'archetype': archetype,
        'process_domain': process_domain or None,
        'location': location or '',
        'country': resolve_country({'location': location or ''}),
        'basis_year': basis_year or 2024,
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
        'equipment_list': [dict(e) for e in (equipment_items or [])] or None,
        'scope_items': [dict(i) for i in (scope_items or [])] or None,
        'surf_scope': {
            'subsea_trees': {'generic': surf_trees} if surf_trees > 0 else {},
            'flowlines': [{'id': f'FL{i+1}', 'count': 1} for i in range(surf_flowlines)],
            'risers': [{'id': f'R{i+1}', 'count': 1} for i in range(surf_risers)],
            'manifolds': {'generic': surf_manifolds} if surf_manifolds > 0 else {},
            'umbilicals': [{'id': f'U{i+1}'} for i in range(surf_umbilicals)],
            'water_depth_m': water_depth if water_depth > 0 else 1500,
        } if surf_has_scope else None,
    }


def facility_hint(facility_type) -> str:
    """'Reference for polyethylene: 625 KTA. Scaling exponent 0.6.' when the
    onshore calculator knows the facility type, else an empty string."""
    name = (facility_type or '').strip()
    if not name:
        return ''
    key = _FACILITY_ALIASES.get(name, name)
    corr = ISBL_CORRELATIONS.get(key)
    if not corr:
        return f"'{name}' is not a calculator facility type; the benchmark and composite models still run."
    _base, ref_cap, exponent, unit = corr
    return f"Reference for {key.replace('_', ' ')}: {ref_cap:g} {unit}. Scaling exponent {exponent:g}."


def project_summary(archetype, location, basis_year, bf_gf) -> str:
    parts = [ARCHETYPE_LABELS.get(archetype, archetype) if archetype else None, location or None,
             f"{basis_year or 2024} USD", (bf_gf or 'greenfield').capitalize()]
    return ' · '.join(p for p in parts if p)


def equipment_summary(items, max_types: int = 6) -> str:
    if not items:
        return ''
    total = sum(int(e.get('count', 0)) for e in items)
    top = sorted(items, key=lambda e: -int(e.get('count', 0)))
    listed = ', '.join(f"{e['type']} {e['count']}" for e in top[:max_types])
    more = f", +{len(top) - max_types} more" if len(top) > max_types else ''
    return f"{total} items · {listed}{more}"


def facility_summary(facility_type, capacity, cap_unit) -> str:
    parts = [(facility_type or '').strip() or None,
             f"{capacity:g} {cap_unit or ''}".strip() if capacity and capacity > 0 else None]
    return ' · '.join(p for p in parts if p)


def scope_items_summary(items) -> str:
    if not items:
        return ''
    return f"{len(items)} item{'s' if len(items) != 1 else ''} · " + ', '.join(i['facility_type'] for i in items[:4]) \
        + (f", +{len(items) - 4} more" if len(items) > 4 else '')


def visible_readiness(rows) -> list:
    """Readiness rows the user can act on: everything except models the
    archetype does not route to."""
    return [r for r in rows if r['status'] != 'not_routed']


def readiness_chip(row, *, short: bool = True) -> str:
    """One markdown chip: filled green dot when ready, outlined grey dot plus
    what it needs otherwise. Excluded models get a red dot."""
    label = short_label(row['model_id']) if short else model_label(row['model_id'])
    s = row['status']
    if s == 'ready':
        return f":green[●] {label}" + (" :gray[auto]" if row.get('auto') else '')
    if s == 'excluded':
        return f":red[●] :gray[{label} · excluded]"
    if s == 'auto':
        return f":gray[○ {label} · auto with the onshore calc]"
    return f":gray[○ {label} · needs {row['needs']}]"


def scope_from_state(ss) -> dict:
    """Scope built from the widget values already in session_state, for
    layouts that need readiness *above* the widgets (Proposta B's group
    chips). Session state holds the new value before a widget is re-created,
    so this is live, not one rerun behind."""
    def num(key, default=0.0):
        try:
            return float(ss.get(key) or 0) or default
        except (TypeError, ValueError):
            return default

    return build_scope(
        archetype=ss.get('archetype') or '', location=ss.get('location'), basis_year=ss.get('basis_year'),
        bf_gf=ss.get('bf_gf'), project_name=ss.get('project_name') or '', process_domain=ss.get('process_domain'),
        facility_type=ss.get('facility_type'), capacity=num('capacity'), cap_unit=ss.get('cap_unit'),
        pipeline_length=num('pipe_len'), pipeline_od=num('pipe_od', 36.0), topsides_wt=num('topsides_wt'),
        water_depth=num('water_depth'), hull_type=ss.get('hull_type') or 'FPSO_newbuild', lng_mtpa=num('lng_mtpa'),
        surf_trees=int(num('surf_trees_input')), surf_flowlines=int(num('surf_flowlines')),
        surf_risers=int(num('surf_risers')), surf_manifolds=int(num('surf_manifolds')),
        surf_umbilicals=int(num('surf_umbilicals')),
        equipment_items=ss.get('equipment_items') or [], scope_items=ss.get('scope_items') or [],
    )
