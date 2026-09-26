"""Calculator_Onshore: six-tenths scaling, EMMA, TEC multiplier chain."""
from typing import Dict, List, Optional, Any
from costbot.constants import ISBL_CORRELATIONS, TEC_MULTIPLIERS, _FACILITY_ALIASES
from costbot.data import DataStore
from costbot.escalation import _get_emma_factor


# ============================================================================
# Model 1: Calculator_Onshore
# ============================================================================

def run_calculator_onshore(scope: Dict, data: DataStore) -> Dict:
    """Onshore Calculator (P4 upgraded).
    Steps from reference onshore_calculator.py:
    1. ISBL from capacity correlation (or facility alias)
    1b. Scope-type override for modification facility types
    2. EMMA location adjustment (index / 202)
    3. TEC multiplier (GF/BF/expansion)
    4. Escalation (6% default)
    5. AACE Class 5 range
    """
    facility_type = scope.get('facility_type') or ''
    capacity = scope.get('primary_capacity') or scope.get('capacity')
    capacity_unit = scope.get('capacity_unit') or ''
    location = scope.get('location', '')
    bf_gf = (scope.get('greenfield_brownfield') or scope.get('scope_type') or 'greenfield').lower()

    if not facility_type or capacity is None:
        return {'can_fire': False, 'no_fire_reason': 'missing_facility_type_or_capacity',
                'model_id': 'Calculator_Onshore'}

    capacity = float(capacity)
    if capacity <= 0:
        return {'can_fire': False, 'no_fire_reason': 'capacity_must_be_positive',
                'model_id': 'Calculator_Onshore'}

    corr_key = _FACILITY_ALIASES.get(facility_type, facility_type)
    if corr_key not in ISBL_CORRELATIONS:
        return {'can_fire': False, 'no_fire_reason': f'no_correlation_for_{facility_type}',
                'model_id': 'Calculator_Onshore'}

    # --- Step 1: ISBL from capacity correlation ---
    base_cost, base_cap, exponent, unit = ISBL_CORRELATIONS[corr_key]
    cap_for_calc = _convert_capacity(capacity, capacity_unit, unit)
    if cap_for_calc is None:
        # Unit mismatch: user's capacity unit can't convert to correlation's expected unit
        # Don't blindly use the raw number — it will produce nonsense estimates
        if capacity_unit.upper().strip() != unit.upper().strip() and capacity_unit.strip():
            return {'can_fire': False, 'no_fire_reason': f'capacity_unit_mismatch_{capacity_unit}_vs_{unit}',
                    'model_id': 'Calculator_Onshore'}
        cap_for_calc = capacity  # same unit or no unit specified — use raw
    isbl_gom = base_cost * (cap_for_calc / base_cap) ** exponent

    # --- Step 1b: Scope-type override (ref L449-460) ---
    scope_type_key = bf_gf
    ft_lower = facility_type.lower()
    if any(kw in ft_lower for kw in ['modification', 'conversion', 'debottleneck']):
        if 'modification' not in scope_type_key and 'brownfield' not in scope_type_key:
            scope_type_key = 'modification'

    # --- Step 2: EMMA location adjustment ---
    emma = _get_emma_factor(location)
    isbl_at_location = isbl_gom * emma

    # --- Step 3: TEC multiplier ---
    # Map scope-type variants: BF-unit-mod, BF, BF-expansion, GF, modification, brownfield
    stk = scope_type_key.lower().replace('-', '_')
    if 'unit_mod' in stk or 'modification' in stk:
        tec_mult = TEC_MULTIPLIERS.get('modification', 1.30)
    elif 'brownfield' in stk or stk.startswith('bf'):
        # BF without unit-mod or expansion → default BF = expansion-class
        if 'expansion' in stk:
            tec_mult = TEC_MULTIPLIERS.get('expansion', 2.61)
        else:
            tec_mult = TEC_MULTIPLIERS.get('expansion', 2.61)
    elif 'expansion' in stk:
        tec_mult = TEC_MULTIPLIERS.get('expansion', 2.61)
    else:
        tec_mult = TEC_MULTIPLIERS.get('greenfield', 2.58)
    tec_constant = isbl_at_location * tec_mult

    # --- Step 4: Escalation (6%) ---
    escalation_pct = 0.06
    tec_escalated = tec_constant * (1 + escalation_pct)

    # --- Step 5: AACE Class 5 range ---
    if 'unit_mod' in stk or 'modification' in stk:
        range_low = tec_escalated * 0.85    # BF-mod: -15% / +50%
        range_high = tec_escalated * 1.50
    elif 'expansion' in stk or stk.startswith('bf'):
        range_low = tec_escalated * 0.75    # expansion: -25% / +40%
        range_high = tec_escalated * 1.40
    else:
        range_low = tec_escalated * 0.70    # GF: -30% / +50%
        range_high = tec_escalated * 1.50

    return {
        'can_fire': True,
        'model_id': 'Calculator_Onshore',
        'estimate_musd': round(tec_escalated, 1),
        'estimate_low_musd': round(range_low, 1),
        'estimate_high_musd': round(range_high, 1),
        'detail': {
            'correlation_key': corr_key,
            'isbl_gom_M': round(isbl_gom, 2),
            'emma_factor': round(emma, 4),
            'isbl_at_location_M': round(isbl_at_location, 2),
            'tec_multiplier': tec_mult,
            'tec_constant_M': round(tec_constant, 2),
            'escalation_pct': escalation_pct,
            'tec_escalated_M': round(tec_escalated, 2),
            'scope_type_key': scope_type_key,
            'capacity_used': cap_for_calc,
            'capacity_unit': unit,
        },
    }



def _convert_capacity(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    from_u = from_unit.upper().strip()
    to_u = to_unit.upper().strip()
    if from_u == to_u:
        return value
    conversions = {
        ('KBD', 'BPD'): lambda v: v * 1000,
        ('KBPD', 'BPD'): lambda v: v * 1000,
        ('KBOPD', 'BPD'): lambda v: v * 1000,
        ('KSBPD', 'BPD'): lambda v: v * 1000,
        ('BPD', 'KBD'): lambda v: v / 1000,
        ('BPD', 'KBPD'): lambda v: v / 1000,
        ('KTA', 'KTA'): lambda v: v,
        ('MTPA', 'KTA'): lambda v: v * 1000,
        ('KTA', 'MTPA'): lambda v: v / 1000,
        ('MTPA_CO2', 'MTPA_CO2'): lambda v: v,
        ('MMSCFD', 'MMSCFD'): lambda v: v,
        # Cross-family conversions for common mismatches
        ('MTPA', 'MTPA_CO2'): lambda v: v,           # mass rate CO2 = mass rate
        ('MTPA_CO2', 'MTPA'): lambda v: v,
        ('MTPA_CO2', 'KTA'): lambda v: v * 1000,
        ('KTA', 'MTPA_CO2'): lambda v: v / 1000,
        ('KTA', 'BPD'): lambda v: v * 1000 / 365 / 6.29,     # KTA->BPD via oil density
        ('BPD', 'KTA'): lambda v: v * 365 / 1000 * 6.29,
        ('KBPD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
        ('KBD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
        ('KSBPD', 'KTA'): lambda v: v * 1000 * 365 / 1000 / 6.29,
    }
    key = (from_u, to_u)
    if key in conversions:
        return conversions[key](value)
    return None
