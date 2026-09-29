"""Calculator_Onshore: port of the reference `onshore_calculator.estimate_onshore_tec()`
called the way `cost_bot_api._run_calculator_onshore()` calls it.

Chain (GOM 2000 constant USD, reference sections 1 to 6):
  1. ISBL from the facility type: IC Library linear curve (single CDU) when the
     name resolves to one and the capacity is inside its valid range; else a
     power-law tuple ISBL = base * (capacity / base_capacity) ** exponent found by
     exact key, alias, substring match; else the generic process-plant fallback.
  1b. A facility name containing modification / conversion / debottleneck forces
     the BF-unit-mod chain.
  2. EMMA: ISBL * location index / 202 (index from `EMMA_LOCATION_INDEX`, first
     substring hit, else 202 = factor 1.0).
  3. TEC multiplier by scope type: GF 2.58, BF-expansion 2.61, BF-unit-mod 1.30,
     anything else 2.58. The API sends BF-expansion for any brownfield / expansion /
     modification / debottleneck scope and GF otherwise.
  4. Escalation 6% (estimate to expenditure, the indices are 4Q2025).
  5. No contingency: the multipliers were calibrated on TEC truth that already
     includes it (reference D.5 fix, 2026-09-15).
  6. Range +/-50% around the TEC (API wrapper; the reference's own -30/+50 is unused).

Intentional deviations (documented in docs/PARITY_cost_bot_api.md):
  - `capacity_unit` is converted to the correlation's unit when a conversion is
    known (KBPD -> BPD, MTPA -> KTA, ...). The reference uses the raw number
    whatever the unit. With no known conversion the raw number is used, as in the
    reference, and a warning is attached.
  - An empty facility type means `process_plant_generic` (the API's documented
    default). In the reference an empty string substring-matches the first alias.
"""
from typing import Dict, Optional, Tuple
from costbot.constants import (ISBL_CORRELATIONS, TEC_MULTIPLIERS, _FACILITY_ALIASES,
                               FACILITY_TYPE_CORRELATION_MAP, IC_LIBRARY_FORMULAS,
                               CALIBRATION_STATUS, _HERITAGE_CURVE_REFERENCES)
from costbot.data import DataStore
from costbot.escalation import _get_emma_index

ESCALATION_PCT = 0.06          # reference default `escalation_pct`
DEFAULT_TEC_MULTIPLIER = 2.58  # reference `TEC_MULTIPLIERS.get(scope_type, 2.58)`
MODIFICATION_KEYWORDS = ('modification', 'conversion', 'debottleneck')
GENERIC = 'process_plant_generic'


def _norm_ft(name) -> str:
    return str(name or '').lower().replace(' ', '_').replace('-', '_')


def api_scope_type(scope: Dict) -> str:
    """cost_bot_api rule: BF-expansion for any brownfield / expansion / modification /
    debottleneck scope, else GF. `calculator_scope_type` (golden tests) passes through."""
    if scope.get('calculator_scope_type'):
        return str(scope['calculator_scope_type'])
    bfgf = (scope.get('greenfield_brownfield') or '').lower()
    st = (scope.get('scope_type') or '').lower()
    return 'BF-expansion' if ('brown' in bfgf or st in ('expansion', 'modification', 'debottleneck')) else 'GF'


def _ic_library_isbl(key: str, capacity: float, unit: str) -> Tuple[Optional[float], float, str]:
    """(ISBL GOM $M or None when out of range, capacity in kB/SD, note)."""
    ic = IC_LIBRARY_FORMULAS[key]
    cap = capacity / 1000.0 if unit.upper().strip() in ('BPD', 'BPSD') else capacity  # else assumed kB/SD
    if cap < ic['valid_min'] or cap > ic['valid_max']:
        return None, cap, (f"IC Library {key}: {cap:.1f} kB/SD outside valid range "
                           f"{ic['valid_min']}-{ic['valid_max']}. Refusing to extrapolate.")
    return ic['a_slope'] * cap + ic['b_intercept'], cap, ic['scope_note']


def _resolve_alias(ft: str) -> Optional[str]:
    """Reference alias chain: exact alias, substring over aliases (first hit), substring
    over tuple keys (first hit). None when nothing matches."""
    resolved = _FACILITY_ALIASES.get(ft)
    if not resolved:
        for alias_key, target in _FACILITY_ALIASES.items():
            if alias_key in ft or ft in alias_key:
                resolved = target
                break
    if not resolved:
        for key in ISBL_CORRELATIONS:
            if key in ft or ft in key:
                resolved = key
                break
    return resolved


def resolve_facility(facility_type: str) -> Tuple[str, str, Optional[str]]:
    """Reference lookup order: exact IC Library key, exact tuple key, alias chain,
    generic fallback. Returns (kind, key, fallback_reason), kind in {'ic', 'tuple', 'ic_alias'}."""
    ft = _norm_ft(facility_type)
    if ft in IC_LIBRARY_FORMULAS:
        return 'ic', ft, None
    if ft in ISBL_CORRELATIONS:
        return 'tuple', ft, None
    resolved = _resolve_alias(ft)
    if resolved and resolved in IC_LIBRARY_FORMULAS:
        return 'ic_alias', resolved, None
    if resolved and resolved in ISBL_CORRELATIONS:
        return 'tuple', resolved, None
    return 'tuple', GENERIC, (f"No calibrated anchor for '{ft}'. Used generic screening fallback "
                              f"(DEPRECATED - prefer EquipmentVector).")


def run_calculator_onshore(scope: Dict, data: DataStore) -> Dict:
    mid = 'Calculator_Onshore'
    requested_ft = scope.get('facility_type') or GENERIC
    # API applies FACILITY_TYPE_CORRELATION_MAP before calling the calculator
    facility_type = FACILITY_TYPE_CORRELATION_MAP.get(_norm_ft(requested_ft), requested_ft)
    capacity = scope.get('primary_capacity')
    if capacity is None:
        capacity = scope.get('capacity')
    capacity_unit = str(scope.get('capacity_unit') or '')
    location = scope.get('location')
    if location is None:
        location = 'US Gulf Coast'  # API default when the key is absent
    scope_type = api_scope_type(scope)

    if capacity is None:
        return {'can_fire': False, 'no_fire_reason': 'missing_capacity', 'model_id': mid}
    try:
        capacity = float(capacity)
    except (TypeError, ValueError):
        return {'can_fire': False, 'no_fire_reason': 'capacity_not_numeric', 'model_id': mid}
    if capacity < 0:
        return {'can_fire': False, 'no_fire_reason': 'capacity_value must be >= 0', 'model_id': mid}

    warnings = []
    # --- Step 1: ISBL (GOM 2000 $M) ---
    kind, key, fallback_reason = resolve_facility(facility_type)
    heritage_reference = _HERITAGE_CURVE_REFERENCES.get(_norm_ft(facility_type))
    tuple_verified = False
    is_ic = False
    if kind == 'ic':
        isbl_gom, cap_used, note = _ic_library_isbl(key, capacity, capacity_unit)
        if isbl_gom is None:
            # reference: out of range falls through to the tuple lookup for the same name
            fallback_reason = note
            ft = _norm_ft(facility_type)
            if ft in ISBL_CORRELATIONS:
                key = ft
            else:
                resolved = _resolve_alias(ft)
                if resolved in IC_LIBRARY_FORMULAS:
                    return {'can_fire': False, 'no_fire_reason': f'ic_library_out_of_range: {note}', 'model_id': mid}
                key = resolved if resolved in ISBL_CORRELATIONS else GENERIC
        else:
            is_ic = True
    elif kind == 'ic_alias':
        isbl_gom, cap_used, note = _ic_library_isbl(key, capacity, capacity_unit)
        if isbl_gom is None:
            # reference: no tuple is bound in this branch, the power-law step raises and
            # the API reports the calculator as not fired
            return {'can_fire': False, 'no_fire_reason': f'ic_library_out_of_range: {note}', 'model_id': mid}
        is_ic = True

    if is_ic:
        ic = IC_LIBRARY_FORMULAS[key]
        expected_unit = ic['capacity_unit']
        heritage_reference = ic['source']
        tuple_verified = True
        fallback_reason = note
        base_cost, base_cap, exponent = ic['b_intercept'], None, None
    else:
        base_cost, base_cap, exponent, expected_unit = ISBL_CORRELATIONS[key]
        tuple_verified = key != GENERIC
        cap_used = _convert_capacity(capacity, capacity_unit, expected_unit)
        if cap_used is None:
            cap_used = capacity  # reference behaviour: raw number, whatever the unit
            if capacity_unit.strip() and capacity_unit.upper().strip() != expected_unit.upper():
                warnings.append(f"Capacity given in {capacity_unit} but the {key} correlation expects "
                                f"{expected_unit}; the raw number was used (as the reference does).")
        isbl_gom = base_cost * (cap_used / base_cap) ** exponent
        if key == GENERIC and fallback_reason:
            warnings.append(f"No calibrated correlation for '{_norm_ft(facility_type)}': generic "
                            f"process-plant fallback (145.4 $M at 500 KTA, deprecated in the reference; "
                            f"prefer the equipment vector).")

    # --- Step 1b: modification-class facility names force BF-unit-mod ---
    if any(kw in _norm_ft(facility_type) for kw in MODIFICATION_KEYWORDS) and scope_type != 'BF-unit-mod':
        scope_type = 'BF-unit-mod'

    # --- Step 2: EMMA ---
    loc_index = _get_emma_index(location)
    emma_factor = loc_index / 202.0
    isbl_at_location = isbl_gom * emma_factor

    # --- Step 3: TEC multiplier ---
    multiplier = TEC_MULTIPLIERS.get(scope_type, DEFAULT_TEC_MULTIPLIER)
    tec_constant = isbl_at_location * multiplier

    # --- Step 4: escalation; Step 5: no contingency (D.5) ---
    escalation = tec_constant * ESCALATION_PCT
    tec_escalated = tec_constant + escalation

    if scope_type == 'BF-unit-mod':
        warnings.append("BF-unit-mod: the correlation scales with the parent unit's capacity. For a "
                        "bounded equipment list (named adds, a debottleneck package) the reference "
                        "measured a 4 to 14x overstatement; cross-check with analogues.")

    return {
        'can_fire': True,
        'model_id': mid,
        'estimate_musd': round(tec_escalated, 1),
        'estimate_low_musd': round(tec_escalated * 0.5, 1),
        'estimate_high_musd': round(tec_escalated * 1.5, 1),
        'model_variant': 'heritage_onshore_calculator',
        'warning': ' '.join(warnings) or None,
        'detail': {
            'facility_type': facility_type,
            'correlation_key': key,
            'correlation_used': key,
            'is_ic_library': is_ic,
            'tuple_verified': tuple_verified,
            'heritage_reference': heritage_reference,
            'fallback_reason': fallback_reason,
            'calibration_status': CALIBRATION_STATUS.get(key, {'N': 0, 'circular': None, 'source_project': 'unknown'}),
            'capacity_used': cap_used,
            'capacity_unit': expected_unit,
            'base_cost': base_cost, 'base_capacity': base_cap, 'exponent': exponent,
            'isbl_gom_M': round(isbl_gom, 2),
            'location': location,
            'emma_location_index': loc_index,
            'emma_factor': round(emma_factor, 4),
            'isbl_at_location_M': round(isbl_at_location, 2),
            'scope_type': scope_type,
            'scope_type_key': scope_type,
            'tec_multiplier': multiplier,
            'tec_constant_M': round(tec_constant, 2),
            'escalation_pct': ESCALATION_PCT,
            'escalation_M': round(escalation, 2),
            'contingency_M': 0.0,
            'tec_escalated_M': round(tec_escalated, 2),
        },
    }


def _convert_capacity(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert between the unit the user typed and the correlation's unit, or None when
    no conversion is known. (Engine addition; the reference uses the raw value.)"""
    from_u = (from_unit or '').upper().strip()
    to_u = (to_unit or '').upper().strip()
    if from_u == to_u:
        return value
    conversions = {
        ('KBD', 'BPD'): lambda v: v * 1000,
        ('KBPD', 'BPD'): lambda v: v * 1000,
        ('KBOPD', 'BPD'): lambda v: v * 1000,
        ('KSBPD', 'BPD'): lambda v: v * 1000,
        ('KBSD', 'BPD'): lambda v: v * 1000,
        ('BPSD', 'BPD'): lambda v: v,
        ('BPD', 'KBD'): lambda v: v / 1000,
        ('BPD', 'KBPD'): lambda v: v / 1000,
        ('KBD', 'KBPD'): lambda v: v,
        ('KBPD', 'KBD'): lambda v: v,
        ('KBD', 'KBD_NGL'): lambda v: v,
        ('KBPD', 'KBD_NGL'): lambda v: v,
        ('BPD', 'KBD_NGL'): lambda v: v / 1000,
        ('MTPA', 'KTA'): lambda v: v * 1000,
        ('KTA', 'MTPA'): lambda v: v / 1000,
        ('KTPA', 'KTA'): lambda v: v,
        ('MTPA', 'MTPA_CO2'): lambda v: v,
        ('MTPA_CO2', 'MTPA'): lambda v: v,
        ('MTPA_CO2', 'KTA'): lambda v: v * 1000,
        ('KTA', 'MTPA_CO2'): lambda v: v / 1000,
        ('KTA', 'BPD'): lambda v: v * 1000 / 365 / 6.29,     # KTA->BPD via oil density
        ('BPD', 'KTA'): lambda v: v * 365 / 1000 * 6.29,
        ('KBPD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
        ('KBD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
        ('KSBPD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
    }
    fn = conversions.get((from_u, to_u))
    return fn(value) if fn else None
