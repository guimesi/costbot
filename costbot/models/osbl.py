"""OSBL_Estimate: 3-layer indirect cost overlay on an ISBL value."""
from typing import Dict, List, Optional, Any
from costbot.data import DataStore


# ============================================================================
# Model 10: OSBL Estimate - 3-layer architecture (P1)
#   Layer 1a: Heritage Flat (% of ISBL by scope type)
#   Layer 1b: IC Library Parametric (capacity-complexity scaling)
#   Layer 1c: IC Absolute Cost Chain (independent of ISBL)
# source: osbl_estimator.py (1,002 lines), ic_library Rev 6.7
# ============================================================================

# --- Heritage Factors (Layer 1a) ---
_HERITAGE_FACTORS = {
    'onshore_petchem': 0.35, 'integrated_petchem': 0.35,
    'refinery_gf': 0.35, 'refinery_bf': 0.35,
    'ccs': 0.35, 'oil_sands': 0.35, 'power_generation': 0.35,
    'renewable_diesel': 0.35, 'gas_processing': 0.35,
    'onshore_unconventional': 0.35,
    'lng_onshore': 0.25, 'lng_offshore': 0.25,
    'offshore_fpso': 0.0, 'offshore_platform': 0.0,
    'pipeline_mainline': 0.0, 'pipeline_gathering': 0.0,
}
_DEFAULT_HERITAGE_FACTOR = 0.35

# OSBL ratios by scope type (heritage layer indirects)
_OSBL_RATIOS = {
    'grassroots': {
        'osbl_pct_of_isbl': 0.35, 'home_office_pct': 0.12,
        'construction_indirects_pct': 0.10, 'contingency_pct': 0.15,
    },
    'expansion': {
        'osbl_pct_of_isbl': 0.25, 'home_office_pct': 0.10,
        'construction_indirects_pct': 0.08, 'contingency_pct': 0.12,
    },
    'modification': {
        'osbl_pct_of_isbl': 0.15, 'home_office_pct': 0.08,
        'construction_indirects_pct': 0.06, 'contingency_pct': 0.10,
    },
}

# --- IC Library Constants (Layer 1b + 1c) ---
_IC_SPILLOVER_COEFF = 0.3
_IC_EQUIP_TO_INSTALLED = {
    'Power/Electrical': 4.0, 'Steam/Boiler/Air': 5.0,
    'Tank Farm/Storage': 3.0, 'Marine/Loading': 5.0,
}
_IC_EQUIP_DEFAULT = 4.0
_IC_SCOPE_MULTIPLIERS = {
    'grassroots': 1.5, 'expansion': 1.2, 'modification': 1.0,
    'debottleneck': 0.8, 'replacement': 0.8,
}

# Typical OSBL composition profiles (% of OSBL)
_OSBL_COMPOSITION = {
    'refinery_gf':     {'Power/Electrical': 18, 'Cooling Water': 12, 'Steam/Boiler/Air': 22,
                        'Tank Farm/Storage': 15, 'Water Treatment': 8, 'Marine/Loading': 5,
                        'Civil/Infrastructure': 10, 'Flare': 5, 'Other OSBL': 5},
    'refinery_bf':     {'Power/Electrical': 20, 'Cooling Water': 10, 'Steam/Boiler/Air': 18,
                        'Tank Farm/Storage': 18, 'Water Treatment': 8, 'Marine/Loading': 6,
                        'Civil/Infrastructure': 10, 'Flare': 5, 'Other OSBL': 5},
    'onshore_petchem': {'Power/Electrical': 22, 'Cooling Water': 10, 'Steam/Boiler/Air': 25,
                        'Tank Farm/Storage': 12, 'Water Treatment': 6, 'Marine/Loading': 5,
                        'Civil/Infrastructure': 10, 'Flare': 5, 'Other OSBL': 5},
    'lng_onshore':     {'Power/Electrical': 25, 'Cooling Water': 8, 'Steam/Boiler/Air': 15,
                        'Tank Farm/Storage': 20, 'Refrigeration': 12, 'Marine/Loading': 10,
                        'Civil/Infrastructure': 5, 'Flare': 3, 'Other OSBL': 2},
    'gas_processing':  {'Power/Electrical': 25, 'Cooling Water': 9, 'Steam/Boiler/Air': 18,
                        'Tank Farm/Storage': 15, 'Water Treatment': 5, 'Marine/Loading': 5,
                        'Civil/Infrastructure': 12, 'Flare': 5, 'Other OSBL': 7},
}
_OSBL_COMPOSITION_DEFAULT = {
    'Power/Electrical': 20, 'Cooling Water': 10, 'Steam/Boiler/Air': 20,
    'Tank Farm/Storage': 15, 'Water Treatment': 8, 'Marine/Loading': 5,
    'Civil/Infrastructure': 10, 'Flare': 5, 'Other OSBL': 7,
}


# --- IC Library Rev 6.7 Curve Functions (8 tier-1-validated) ---

def _ic_purchased_power(cap, circuit='Single', n=1):
    cap = max(50, min(400, cap))
    if circuit == 'Double':
        return (0.4831 * cap + 60.679) * n
    return (0.256 * cap + 52.786) * n

def _ic_substation(size='H'):
    return {'H': 64.0, 'M': 38.0}.get(size, 0.0)

def _ic_feeder_cable(km=10, circuits=1):
    km = max(3, min(20, km))
    return 3.3924 * km ** 0.8458 * circuits * 2.0

def _ic_steam_bfw(cap, treatment='Cold Lime'):
    cap = max(200, min(5000, cap))
    if treatment == 'Hot Lime':
        if cap < 501: return ((cap / 400) ** 0.25) * 250
        elif cap < 1001: return ((cap / 700) ** 0.32) * 300
        elif cap < 2001: return ((cap / 1500) ** 0.46) * 410
        else: return ((cap / 4000) ** 0.65) * 700
    return 0.0000005 * cap ** 2 + 0.0397 * cap + 146.93

def _ic_spheres(kbbl, pressure=150):
    kbbl = max(1.2, min(30, kbbl))
    coeffs = {250: (66.286, 31.981), 150: (36.318, 52.634),
              75: (17.894, 69.488), 50: (12.659, 55.647)}
    a, b = coeffs.get(pressure, coeffs[150])
    return a * kbbl + b

def _ic_product_loading(streams, ptype='C', sets=2):
    streams = max(2, min(40, streams))
    if ptype == 'C':
        c = 0.0006 * streams**3 + 0.0872 * streams**2 - 0.3705 * streams + 3.53
    elif ptype == 'B':
        c = 0.0526 * streams**2 + 0.3268 * streams + 1.7167
    elif ptype == 'A':
        c = 0.0503 * streams**2 + 0.5834 * streams + 6.375
    else:
        c = 0
    return c * sets


def _ic_eval_power(p):
    load = p.get('electrical_load_mva', 100)
    n_sub = max(1, int(load / 100))
    return (_ic_purchased_power(load, 'Single', max(1, int(load / 80)))
            + n_sub * _ic_substation('H' if load > 50 else 'M')
            + n_sub * _ic_feeder_cable(p.get('feeder_cable_km', 10)))

def _ic_eval_steam(p):
    return _ic_steam_bfw(p.get('steam_bfw_klb_hr', 500))

def _ic_eval_storage(p):
    return (p.get('num_spheres', 4)
            * _ic_spheres(p.get('sphere_kbbl', 10), p.get('sphere_pressure_psig', 150)))

def _ic_eval_loading(p):
    return _ic_product_loading(
        p.get('num_loading_streams', 8),
        p.get('loading_pump_type', 'C'),
        p.get('loading_pump_sets', 2))

_IC_SYSTEM_EVALUATORS = {
    'Power/Electrical': _ic_eval_power,
    'Steam/Boiler/Air': _ic_eval_steam,
    'Tank Farm/Storage': _ic_eval_storage,
    'Marine/Loading': _ic_eval_loading,
}


def _derive_ic_defaults(archetype, scope_type, user_capacity=None):
    d = {
        'electrical_load_mva': 100, 'feeder_cable_km': 10,
        'steam_bfw_klb_hr': 500, 'num_spheres': 4,
        'sphere_kbbl': 10, 'sphere_pressure_psig': 150,
        'num_loading_streams': 8, 'loading_pump_type': 'C', 'loading_pump_sets': 2,
    }
    uc = user_capacity or {}
    if archetype in ('refinery_bf', 'refinery_gf'):
        crude = uc.get('crude_kbpd', uc.get('primary_capacity', 200))
        d['electrical_load_mva'] = max(50, min(400, crude * 0.5))
        d['steam_bfw_klb_hr'] = max(200, min(5000, crude * 2.5))
        d['num_spheres'] = max(2, int(crude / 50))
        d['num_loading_streams'] = max(4, int(crude / 25))
        if archetype == 'refinery_gf':
            d['electrical_load_mva'] *= 1.5
            d['feeder_cable_km'] = 15
            d['num_spheres'] = int(d['num_spheres'] * 1.5)
    elif archetype in ('onshore_petchem', 'integrated_petchem'):
        ktpa = uc.get('capacity_ktpa', uc.get('primary_capacity', 1000))
        d['electrical_load_mva'] = max(50, min(400, 100 + ktpa * 0.1))
        d['steam_bfw_klb_hr'] = max(200, min(5000, ktpa * 1.5))
        d['num_spheres'] = max(4, int(ktpa / 150))
        d['num_loading_streams'] = max(6, int(ktpa / 100))
    elif archetype == 'lng_onshore':
        mtpa = uc.get('capacity_mtpa', uc.get('lng_capacity_mtpa', 5))
        d['electrical_load_mva'] = max(50, min(400, mtpa * 30))
        d['steam_bfw_klb_hr'] = max(200, min(5000, mtpa * 300))
        d['num_spheres'] = max(4, int(mtpa * 2))
        d['num_loading_streams'] = max(4, int(mtpa * 2))
    elif archetype == 'gas_processing':
        mmscfd = uc.get('capacity_mmscfd', uc.get('primary_capacity', 500))
        d['electrical_load_mva'] = max(50, min(400, mmscfd * 0.15))
        d['steam_bfw_klb_hr'] = max(200, min(5000, mmscfd * 0.8))
        d['num_spheres'] = max(2, int(mmscfd / 200))
        d['num_loading_streams'] = max(2, int(mmscfd / 200))
    else:
        isbl = uc.get('isbl_musd', 200)
        d['electrical_load_mva'] = max(50, min(400, 50 + isbl * 0.25))
        d['steam_bfw_klb_hr'] = max(200, min(5000, 200 + isbl * 1.5))
        d['num_spheres'] = max(2, int(isbl / 50))
        d['num_loading_streams'] = max(4, int(isbl / 30))
    if scope_type in ('modification', 'debottleneck', 'replacement'):
        d['electrical_load_mva'] *= 0.5
        d['feeder_cable_km'] = 5
        d['num_spheres'] = max(1, int(d['num_spheres'] * 0.5))
    elif scope_type == 'expansion':
        d['electrical_load_mva'] *= 0.7
        d['num_spheres'] = max(2, int(d['num_spheres'] * 0.7))
    return d


def _osbl_parametric(archetype, scope_type, isbl_musd, heritage_pct, capacity_dict):
    """Layer 1b: IC Library Parametric - capacity-complexity index."""
    profile = _OSBL_COMPOSITION.get(archetype, _OSBL_COMPOSITION_DEFAULT)
    total_pct = sum(profile.values())
    user_params = _derive_ic_defaults(archetype, scope_type, capacity_dict)
    ref_params = _derive_ic_defaults(archetype, scope_type, None)
    system_scalings = {}
    ic_covered_weight = 0.0
    for sys_type, evaluator in _IC_SYSTEM_EVALUATORS.items():
        user_cost = evaluator(user_params)
        ref_cost = evaluator(ref_params)
        scaling = user_cost / ref_cost if ref_cost > 0 else 1.0
        system_scalings[sys_type] = round(scaling, 3)
        ic_covered_weight += profile.get(sys_type, 0) / total_pct if total_pct > 0 else 0
    if ic_covered_weight > 0:
        weighted_ic_scaling = sum(
            system_scalings.get(st, 1.0) * (profile.get(st, 0) / total_pct)
            for st in _IC_SYSTEM_EVALUATORS
        ) / ic_covered_weight
    else:
        weighted_ic_scaling = 1.0
    non_ic_scaling = 1.0 + _IC_SPILLOVER_COEFF * (weighted_ic_scaling - 1.0)
    overall_index = (ic_covered_weight * weighted_ic_scaling
                     + (1 - ic_covered_weight) * non_ic_scaling)
    overall_index = max(0.5, min(2.0, overall_index))
    parametric_factor = heritage_pct * overall_index
    parametric_osbl = isbl_musd * parametric_factor
    return {
        'parametric_osbl_musd': round(parametric_osbl, 1),
        'parametric_factor': round(parametric_factor, 4),
        'complexity_index': round(overall_index, 3),
        'weighted_ic_scaling': round(weighted_ic_scaling, 3),
        'ic_coverage_pct': round(ic_covered_weight * 100, 1),
        'system_scalings': system_scalings,
    }


def _osbl_absolute_chain(archetype, scope_type, capacity_dict):
    """Layer 1c: IC Absolute Cost Chain - capacity-driven, ISBL-independent."""
    user_params = _derive_ic_defaults(archetype, scope_type, capacity_dict)
    esc_factor = 1.03 ** (2025-1996)
    total_baseyear_kusd = 0.0
    total_installed_musd = 0.0
    per_system = []
    for sys_type, evaluator in _IC_SYSTEM_EVALUATORS.items():
        baseyear_kusd = evaluator(user_params)
        escalated_kusd = baseyear_kusd * esc_factor
        e2i = _IC_EQUIP_TO_INSTALLED.get(sys_type, _IC_EQUIP_DEFAULT)
        installed_musd = escalated_kusd / 1000.0 * e2i
        total_baseyear_kusd += baseyear_kusd
        total_installed_musd += installed_musd
        per_system.append({'system_type': sys_type,
                           'baseyear_kusd': round(baseyear_kusd, 1),
                           'installed_musd': round(installed_musd, 2)})
    scope_key = 'grassroots' if 'green' in scope_type or 'grass' in scope_type else scope_type
    scope_mult = _IC_SCOPE_MULTIPLIERS.get(scope_key, 1.0)
    scoped_musd = total_installed_musd * scope_mult
    profile = _OSBL_COMPOSITION.get(archetype, _OSBL_COMPOSITION_DEFAULT)
    total_pct = sum(profile.values())
    ic_pct = sum(profile.get(st, 0) for st in _IC_SYSTEM_EVALUATORS) / total_pct if total_pct > 0 else 0.1
    ic_pct = max(ic_pct, 0.05)
    ic_osbl_musd = scoped_musd / ic_pct
    return {
        'ic_absolute_osbl_musd': round(ic_osbl_musd, 1),
        'ic_cost_chain': {
            'baseyear_kusd': round(total_baseyear_kusd, 1),
            'escalation_factor': round(esc_factor, 3),
            'installed_musd': round(total_installed_musd, 2),
            'scope_multiplier': scope_mult,
            'ic_coverage_pct': round(ic_pct * 100, 1),
        },
        'per_system': per_system,
    }


def run_osbl_estimate(scope: Dict, data: DataStore, isbl_musd: float = None,
                      isbl_source: str = None) -> Dict:
    """3-layer OSBL estimate: heritage flat + IC parametric + IC absolute."""
    if isbl_musd is None or isbl_musd <= 0:
        return {'can_fire': False, 'no_fire_reason': 'no_isbl_available',
                'model_id': 'OSBL_Estimate'}
    archetype = scope.get('archetype', 'UNKNOWN')
    if archetype in ('offshore_fpso', 'offshore_platform',
                      'pipeline_mainline', 'pipeline_gathering'):
        return {
            'can_fire': True, 'model_id': 'OSBL_Estimate',
            'estimate_musd': 0.0, 'estimate_low_musd': 0.0, 'estimate_high_musd': 0.0,
            'is_indirect': True, 'isbl_source': isbl_source,
            'note': 'OSBL not applicable for offshore/pipeline.',
        }
    scope_type = (scope.get('scope_type') or scope.get('greenfield_brownfield') or 'modification').lower()
    if 'greenfield' in scope_type or 'grassroots' in scope_type:
        scope_key = 'grassroots'
    elif 'expansion' in scope_type:
        scope_key = 'expansion'
    else:
        scope_key = 'modification'
    ratios = _OSBL_RATIOS[scope_key]

    # Layer 1a: Heritage Flat
    heritage_pct = _HERITAGE_FACTORS.get(archetype, _DEFAULT_HERITAGE_FACTOR)
    osbl_cost = isbl_musd * heritage_pct
    home_office = isbl_musd * ratios['home_office_pct']
    construction_indirects = isbl_musd * ratios['construction_indirects_pct']
    contingency = isbl_musd * ratios['contingency_pct']
    heritage_total = osbl_cost + home_office + construction_indirects + contingency
    layer_1a = {'heritage_osbl_musd': round(osbl_cost, 1),
                'heritage_total_musd': round(heritage_total, 1), 'heritage_pct': heritage_pct}

    # Layer 1b: IC Library Parametric
    capacity = scope.get('primary_capacity')
    layer_1b = None
    if capacity and capacity > 0:
        cap_dict = {'primary_capacity': capacity, 'isbl_musd': isbl_musd}
        if archetype in ('refinery_bf', 'refinery_gf'):
            cap_dict['crude_kbpd'] = capacity
        elif archetype in ('onshore_petchem', 'integrated_petchem'):
            cap_dict['capacity_ktpa'] = capacity
        elif archetype == 'lng_onshore':
            cap_dict['capacity_mtpa'] = scope.get('lng_capacity_mtpa', capacity)
        elif archetype == 'gas_processing':
            cap_dict['capacity_mmscfd'] = capacity
        layer_1b = _osbl_parametric(archetype, scope_key, isbl_musd, heritage_pct, cap_dict)

    # Layer 1c: IC Absolute Cost Chain
    layer_1c = None
    if capacity and capacity > 0:
        cap_dict_abs = cap_dict.copy() if layer_1b else {'isbl_musd': isbl_musd}
        layer_1c = _osbl_absolute_chain(archetype, scope_key, cap_dict_abs)

    # Blend
    estimates = [heritage_total]
    weights = [1.0]
    parametric_total = None
    if layer_1b:
        indirects_mult = heritage_total / osbl_cost if osbl_cost > 0 else 1.0
        parametric_total = layer_1b['parametric_osbl_musd'] * indirects_mult
        estimates.append(parametric_total)
        weights = [0.5, 0.3]
    if layer_1c:
        estimates.append(layer_1c['ic_absolute_osbl_musd'])
        if len(weights) == 2:
            weights = [0.4, 0.35, 0.25]
        else:
            weights = [0.6, 0.4]
    w_sum = sum(weights)
    weights = [w / w_sum for w in weights]
    blended = sum(e * w for e, w in zip(estimates, weights))

    if len(estimates) > 1:
        range_low = min(blended * 0.7, min(estimates) * 0.85)
        range_high = max(blended * 1.3, max(estimates) * 1.15)
    else:
        range_low = blended * 0.7
        range_high = blended * 1.3

    layer_labels = ['1a'] + (['1b'] if layer_1b else []) + (['1c'] if layer_1c else [])
    return {
        'can_fire': True, 'model_id': 'OSBL_Estimate',
        'estimate_musd': round(blended, 1),
        'estimate_low_musd': round(range_low, 1),
        'estimate_high_musd': round(range_high, 1),
        'is_indirect': True, 'isbl_source': isbl_source,
        'isbl_musd_used': round(isbl_musd, 1),
        'layers_used': layer_labels,
        'detail': {
            'scope_type_used': scope_key,
            'layer_1a_heritage': layer_1a,
            'layer_1b_parametric': {
                **layer_1b,
                'parametric_total_musd': round(parametric_total, 1),
            } if layer_1b else None,
            'layer_1c_absolute': layer_1c,
            'blend_weights': {f'layer_{l}': round(w, 2) for l, w in zip(layer_labels, weights)},
            'ratios': ratios,
        },
    }
