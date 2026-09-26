"""screen_project(): routing, model execution, escalation, ensemble, OSBL, floor; analogues; bid validation."""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import math
import pandas as pd
from costbot.constants import (ARCHETYPE_ALIASES_POOL, ARCHETYPE_EXCLUSIONS, ARCHETYPE_MODELS,
                               SCREENING_FLOOR_MUSD, ISBL_CORRELATIONS, _FACILITY_ALIASES)
from costbot.data import DataStore
from costbot.ensemble import _assess_confidence
from costbot.escalation import _POOL_BASE_YEAR, _apply_cp30_escalation, _get_cp30_escalation_factor
from costbot.models.benchmark import run_benchmark
from costbot.models.calculator_lng import run_calculator_lng
from costbot.models.calculator_offshore import run_calculator_offshore
from costbot.models.calculator_onshore import run_calculator_onshore
from costbot.models.calculator_pipeline import run_calculator_pipeline
from costbot.models.composite import run_composite
from costbot.models.equipment_vector import run_equipment_vector
from costbot.models.osbl import run_osbl_estimate
from costbot.models.surf import run_surf_user
from costbot.models.unconventional import run_unconventional


# ============================================================================
# Main Screening Engine
# ============================================================================

_MODEL_FN_MAP = {
    'Calculator_Onshore':   run_calculator_onshore,
    'Calculator_Pipeline':  run_calculator_pipeline,
    'Calculator_LNG':       run_calculator_lng,
    'Calculator_Offshore':  run_calculator_offshore,
    'Benchmark':            run_benchmark,
    'EquipmentVector':      run_equipment_vector,
    'Unconventional':       run_unconventional,
    'Composite':            run_composite,
    'SURF_User':            run_surf_user,
}


# Display order for the readiness panel and the report
MODEL_ORDER = [
    'Benchmark', 'EquipmentVector', 'Calculator_Onshore', 'Calculator_Offshore',
    'Calculator_Pipeline', 'Calculator_LNG', 'Unconventional', 'Composite',
    'SURF_User', 'OSBL_Estimate',
]
_DYNAMIC_MODELS = {'EquipmentVector': 'equipment_list', 'SURF_User': 'surf_scope', 'Composite': 'scope_items'}
_OSBL_NOT_APPLICABLE = {'offshore_fpso', 'offshore_platform', 'pipeline_mainline', 'pipeline_gathering'}


def _has(v) -> bool:
    try:
        return v is not None and v != '' and float(v) > 0
    except (TypeError, ValueError):
        return bool(v)


def model_readiness(scope: Dict, data: Optional[DataStore] = None) -> List[Dict]:
    """Cheap, compute-free preview of which models would fire for `scope`.

    Mirrors the routing in screen_project() and each runner's input gate so
    the UI can show a live checklist while the user types. Returns one dict
    per model in MODEL_ORDER with:
      status: 'ready' | 'needs' | 'excluded' | 'auto' | 'not_routed'
      needs:  human-readable missing input (for 'needs' / 'auto')
      routed: whether the archetype routes to this model (or it is dynamic)
    It is a prediction, not a guarantee: data-dependent failures (e.g. no
    analogue above threshold) only show up when the models actually run.
    """
    archetype = scope.get('archetype') or ''
    routed = list(ARCHETYPE_MODELS.get(archetype, ['Calculator_Onshore', 'Benchmark'])) if archetype else []
    exclusions = set(ARCHETYPE_EXCLUSIONS.get(archetype, []))
    is_offshore = 'offshore' in archetype
    sp = scope.get('secondary_params') or {}
    if not isinstance(sp, dict):
        sp = {}
    surf = scope.get('surf_scope') or {}
    if not isinstance(surf, dict):
        surf = {}
    trees = surf.get('subsea_trees')
    n_trees = sum(trees.values()) if isinstance(trees, dict) else (surf.get('n_trees') or 0)
    n_flowlines = len(surf.get('flowlines') or [])

    facility = (scope.get('facility_type') or '').strip()
    facility_known = _FACILITY_ALIASES.get(facility, facility) in ISBL_CORRELATIONS if facility else False
    capacity_ok = _has(scope.get('primary_capacity') or scope.get('capacity'))

    gates = {
        'Benchmark': (bool(archetype), 'an archetype'),
        'EquipmentVector': (bool(scope.get('equipment_list')), 'at least one equipment item'),
        'Calculator_Onshore': (
            facility_known and capacity_ok,
            'facility type + capacity' if not facility else
            ('capacity' if facility_known else f"a facility type the calculator knows ('{facility}' is not one)")),
        'Calculator_Offshore': (
            _has(scope.get('topsides_weight_te')) or _has(sp.get('topsides_weight_te')) or capacity_ok,
            'topsides weight or production (KBPD)'),
        'Calculator_Pipeline': (_has(scope.get('length_km') or scope.get('pipeline_length_km')), 'pipeline length (km)'),
        'Calculator_LNG': (_has(scope.get('lng_capacity_mtpa')) or capacity_ok, 'LNG capacity (MTPA)'),
        'Unconventional': (bool(facility), 'facility type'),
        'Composite': (bool(scope.get('scope_items')), 'at least one scope item'),
        'SURF_User': (n_trees > 0 or n_flowlines > 0, 'subsea trees or flowlines'),
    }

    out = []
    onshore_ready = False
    for mid in MODEL_ORDER:
        if mid == 'OSBL_Estimate':
            applicable = bool(archetype) and archetype not in _OSBL_NOT_APPLICABLE
            if not applicable:
                out.append({'model_id': mid, 'status': 'not_routed', 'needs': '', 'routed': False})
            elif onshore_ready:
                out.append({'model_id': mid, 'status': 'ready', 'needs': '', 'routed': True, 'auto': True})
            else:
                out.append({'model_id': mid, 'status': 'auto', 'needs': 'an ISBL from Calculator_Onshore (automatic)',
                            'routed': True, 'auto': True})
            continue
        is_routed = mid in routed
        is_dynamic = mid in _DYNAMIC_MODELS and bool(archetype)
        if mid == 'SURF_User' and not is_offshore:
            is_dynamic = False  # the card only exists for offshore archetypes
        if not is_routed and not is_dynamic:
            out.append({'model_id': mid, 'status': 'not_routed', 'needs': '', 'routed': False})
            continue
        ok, needs = gates[mid]
        if mid in exclusions:
            status = 'excluded'
        elif ok:
            status = 'ready'
        else:
            status = 'needs'
        if mid == 'Calculator_Onshore' and status == 'ready':
            onshore_ready = True
        out.append({'model_id': mid, 'status': status, 'needs': '' if ok else needs, 'routed': True})
    return out


def screen_project(scope: Dict, data: DataStore) -> Dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    archetype = scope.get('archetype', 'UNKNOWN')

    screening_floor_note = None

    models_to_run = list(ARCHETYPE_MODELS.get(archetype, ['Calculator_Onshore', 'Benchmark']))
    if scope.get('equipment_list') and 'EquipmentVector' not in models_to_run:
        models_to_run.append('EquipmentVector')
    if scope.get('surf_scope') and 'SURF_User' not in models_to_run:
        models_to_run.append('SURF_User')
    if scope.get('scope_items') and 'Composite' not in models_to_run:
        models_to_run.append('Composite')

    exclusions = ARCHETYPE_EXCLUSIONS.get(archetype, [])

    model_results = {}
    for model_id in models_to_run:
        fn = _MODEL_FN_MAP.get(model_id)
        if not fn:
            model_results[model_id] = {'can_fire': False, 'no_fire_reason': f'no_runner_{model_id}',
                                       'model_id': model_id}
            continue
        try:
            result = fn(scope, data)
        except Exception as e:
            result = {'can_fire': False, 'no_fire_reason': str(e)[:300], 'model_id': model_id}

        if model_id in exclusions and result.get('can_fire'):
            result['excluded_by_rule'] = True
            result['exclusion_reason'] = f'{model_id} is pre-excluded for {archetype}'
        model_results[model_id] = result

    # --- CP30 basis-year escalation (P3) ---
    # Pool-based models produce estimates in 2024 USD -> user's target
    # basis year differs, escalate using the GOM CP30 combined index ratio.
    target_year = scope.get('basis_year', _POOL_BASE_YEAR)
    cp30_factor = _get_cp30_escalation_factor(data.cp30, target_year)
    # Pre-fetch analogues so they can be escalated together with models
    analogues = _get_analogues(scope, data)
    _apply_cp30_escalation(model_results, analogues, cp30_factor, target_year)

    # Separate TEC models from component models
    tec_viable = []
    component_estimates = []
    for r in model_results.values():
        if not r.get('can_fire') or r.get('excluded_by_rule'):
            continue
        if r.get('is_component'):
            component_estimates.append(r)
        else:
            tec_viable.append(r)

    ensemble = _assess_confidence(tec_viable, archetype=archetype)

    if component_estimates:
        comp_dict = {}
        for c in component_estimates:
            comp_type = c.get('component_type', c.get('model_id', 'unknown'))
            comp_dict[comp_type] = {
                'estimate_musd': c.get('estimate_musd'),
                'range': [c.get('estimate_low_musd'), c.get('estimate_high_musd')],
            }
        ensemble['component_estimates'] = comp_dict
        if ensemble['confidence'] == 'CANNOT_ESTIMATE' and comp_dict:
            ensemble['confidence'] = 'COMPONENT_ONLY'

    # --- OSBL auto-fire when ISBL is available ---
    osbl_result = None
    isbl_musd = None
    isbl_source = None

    calc_onshore = model_results.get('Calculator_Onshore', {})
    if calc_onshore.get('can_fire') and not calc_onshore.get('excluded_by_rule'):
        detail = calc_onshore.get('detail', {})
        isbl_val = detail.get('isbl_at_location_M') or detail.get('isbl_gom_M')
        if isbl_val and float(isbl_val) > 0:
            isbl_musd = float(isbl_val)
            isbl_source = 'Calculator_Onshore'

    if isbl_musd is None and scope.get('isbl_musd'):
        isbl_musd = float(scope['isbl_musd'])
        isbl_source = 'user_provided'

    if isbl_musd and isbl_musd > 0:
        osbl_result = run_osbl_estimate(scope, data, isbl_musd=isbl_musd,
                                        isbl_source=isbl_source)
        model_results['OSBL_Estimate'] = osbl_result
    else:
        model_results['OSBL_Estimate'] = {
            'can_fire': False, 'no_fire_reason': 'no_isbl_available',
            'model_id': 'OSBL_Estimate',
        }

    # --- Screening floor check (post-hoc on ensemble P50) ---
    best_est = ensemble.get('best_estimate_musd')
    user_ballpark = scope.get('project_scale_musd')  # optional user override
    check_value = user_ballpark if user_ballpark is not None else best_est
    if check_value is not None and check_value < SCREENING_FLOOR_MUSD:
        screening_floor_note = (
            f"At ~${check_value:,.0f}M, this project is below our screening threshold "
            f"(${SCREENING_FLOOR_MUSD:.0f}M). Projects under ${SCREENING_FLOOR_MUSD:.0f}M "
            f"are generally not screening candidates \u2014 estimates at this scale carry "
            f"disproportionate uncertainty."
        )

    # Analogues already fetched and escalated above (CP30 block)

    # Build basis-year note for display
    basis_year_note = None
    if target_year != _POOL_BASE_YEAR and abs(cp30_factor - 1.0) >= 0.0001:
        basis_year_note = (
            f"Pool-based estimates escalated from {_POOL_BASE_YEAR} to {target_year} USD "
            f"(CP30 factor: {cp30_factor:.4f}; +{(cp30_factor-1)*100:.1f}%)"
        )

    return {
        'scope': scope,
        'screening_floor_note': screening_floor_note,
        'basis_year_note': basis_year_note,
        'cp30_escalation': {'from_year': _POOL_BASE_YEAR, 'to_year': target_year,
                            'factor': round(cp30_factor, 4)} if basis_year_note else None,
        'models': model_results,
        'ensemble': ensemble,
        'analogues': analogues,
        'osbl': osbl_result,
        'timestamp': timestamp,
        'disclaimer': (
            'Screening estimate only. Class 5 accuracy target (±50%). '
            'Not a basis of estimate.'
        ),
    }


def _get_analogues(scope: Dict, data: DataStore, limit: int = 10) -> List[Dict]:
    archetype = scope.get('archetype', '')
    pool = data.pool
    if pool.empty:
        return []

    pool_arch = ARCHETYPE_ALIASES_POOL.get(archetype, archetype)
    subset = pool[pool['archetype'].fillna('').str.lower() == pool_arch.lower()]
    if subset.empty:
        return []

    s_pd = (scope.get('process_domain') or '').lower()
    s_st = (scope.get('scope_type') or '').lower()
    s_ft = (scope.get('facility_type') or '').lower()
    user_cap = scope.get('primary_capacity')

    scored = []
    for _, row in subset.iterrows():
        r_pd = str(row.get('process_domain', '')).lower()
        r_st = str(row.get('scope_type', '')).lower()
        r_ft = str(row.get('facility_type', '')).lower()
        tec = row.get('tec_musd_normalized_2024')
        if pd.isna(tec) or float(tec) <= 0:
            continue

        feat = 0.0
        if s_pd and r_pd and s_pd == r_pd: feat += 0.33
        if s_st and r_st and s_st == r_st: feat += 0.33
        if s_ft and r_ft and s_ft == r_ft: feat += 0.34

        cap_score = 0.0
        a_cap = row.get('primary_capacity')
        if user_cap and a_cap and pd.notna(a_cap) and float(user_cap) > 0 and float(a_cap) > 0:
            cap_score = max(0, 1.0 - abs(math.log(float(a_cap) / float(user_cap))))

        blended = 0.6 * feat + 0.4 * cap_score

        scored.append({
            'project_name': row.get('project_name', ''),
            'archetype': row.get('archetype', ''),
            'tec_musd_2024': round(float(tec), 1),
            'country': row.get('country', ''),
            'capacity': row.get('primary_capacity'),
            'capacity_unit': row.get('capacity_unit', ''),
            'similarity': round(blended, 3),
            'process_domain': row.get('process_domain', ''),
            'scope_type': row.get('scope_type', ''),
        })

    scored.sort(key=lambda x: -x['similarity'])
    return scored[:limit]


def model_rows(results: Dict) -> List[Dict]:
    """Fired, non-excluded models with their role in the ensemble, for charts
    and tables (UI and HTML report share this)."""
    ens = results.get('ensemble', {})
    included = set(ens.get('models_included') or [])
    if 'GeometricBlend' in included:
        included |= {'Calculator_Onshore', 'Benchmark'}
    gated = {g[0] for g in ens.get('models_gated_out') or []}
    rows = []
    for mid, mr in results.get('models', {}).items():
        if not mr.get('can_fire') or mr.get('excluded_by_rule') or not mr.get('estimate_musd'):
            continue
        if mr.get('is_component'):
            role = 'Component'
        elif mr.get('is_indirect'):
            role = 'Indirect overlay'
        elif mid in gated:
            role = 'Gated out'
        else:
            role = 'In ensemble'
        rows.append({'model_id': mid, 'estimate': mr['estimate_musd'],
                     'low': mr.get('estimate_low_musd') or mr['estimate_musd'],
                     'high': mr.get('estimate_high_musd') or mr['estimate_musd'], 'role': role})
    return rows


def validate_bid(results: Dict, bid_musd: float, bid_type: str = 'TEC') -> Dict:
    ens = results.get('ensemble', {})
    if ens.get('best_estimate_musd') is None:
        return {'verdict': 'CANNOT_ASSESS', 'reason': 'No screening estimate available.'}

    adjusted_bid = bid_musd
    if bid_type == 'EPC_lumpsum':
        adjusted_bid = bid_musd / 1.175

    ratio = adjusted_bid / ens['best_estimate_musd']
    if adjusted_bid > ens.get('range_high_musd', float('inf')):
        verdict = 'ABOVE_RANGE'
        pct = round((adjusted_bid / ens['range_high_musd'] - 1) * 100, 0)
        summary = f"Bid is {pct:.0f}% above upper bound."
    elif adjusted_bid < ens.get('range_low_musd', 0):
        verdict = 'BELOW_RANGE'
        pct = round((1 - adjusted_bid / ens['range_low_musd']) * 100, 0)
        summary = f"Bid is {pct:.0f}% below lower bound."
    else:
        verdict = 'WITHIN_RANGE'
        summary = f"Bid is within screening range (ratio: {ratio:.2f}x)."

    return {
        'verdict': verdict,
        'ratio': round(ratio, 3),
        'adjusted_bid_musd': round(adjusted_bid, 1),
        'best_estimate_musd': ens['best_estimate_musd'],
        'range': [ens.get('range_low_musd'), ens.get('range_high_musd')],
        'summary': summary,
    }
