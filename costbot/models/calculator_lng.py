"""Calculator_LNG: CET subsystem regressions. Known miscalibrated."""
from typing import Dict, List, Optional, Any
from costbot.data import DataStore


# ============================================================================
# Model 3: Calculator_LNG (simplified)
# ============================================================================

def run_calculator_lng(scope: Dict, data: DataStore) -> Dict:
    """LNG Calculator (P4 upgraded).
    Reference: lng_calculator.py - 30+ subsystem regressions from CET,
    multi-train scaling, 25-location factors, loading factor approach.
    """
    mtpa = scope.get('lng_capacity_mtpa') or scope.get('primary_capacity')
    if mtpa is None:
        return {'can_fire': False, 'no_fire_reason': 'missing_lng_capacity',
                'model_id': 'Calculator_LNG'}
    mtpa = float(mtpa)
    location = scope.get('location', '')
    num_trains = scope.get('num_trains', max(1, int(mtpa / 5.0 + 0.5)))
    technology = (scope.get('technology') or 'C3MR').upper()

    # Per-train MTPA
    mtpa_per_train = mtpa / num_trains

    def _regress(intercept, coeff, exp, min_v, max_v, driver):
        if exp is not None:
            r = (intercept or 0) + coeff * (driver ** exp)
        else:
            r = (intercept or 0) + coeff * driver
        if min_v is not None: r = max(r, min_v)
        if max_v is not None: r = min(r, max_v)
        return r

    # --- Subsystem regressions (hours "h" + materials "m", per-train MTPA) ---
    # source: lng_calculator.py EQUATIONS (rows 21-52 of LNG CET)
    # All material costs in USD (2025 basis)

    # Common process (hours not costed here — included in loading factor)
    inlet_treat_m = _regress(-117.52e6, 7.6565e6, None, 120e6, 150e6, mtpa_per_train)
    inlet_no_m = _regress(7.0691e6, 0.8064e6, None, 10e6, 45e6, mtpa_per_train)
    ngl_frac_m = _regress(5.0597e6, 35.174e6, None, 5e6, 150e6, mtpa_per_train)

    # Process train (technology-dependent liquefaction)
    liq_key = {'C3MR': 'C3MR', 'SMR': 'SMR', 'APX': 'APX'}.get(technology, 'C3MR')
    _LIQ_M = {
        'C3MR': lambda d: _regress(33.051e6, 44.965e6, None, 100e6, 330e6, d),
        'SMR': lambda d: _regress(5.6354e6, 28.689e6, None, 20e6, 65e6, d),
        'APX': lambda d: _regress(140.76e6, 30.228e6, None, 300e6, 500e6, d),
    }
    liq_m = _LIQ_M[liq_key](mtpa_per_train)

    # Supporting subsystems
    dehydration_m = _regress(-13.891e6, 6.9152e6, None, 10e6, 300e6, mtpa_per_train)
    end_flash_m = _regress(3.5837e6, 1.4661e6, None, 7e6, 25e6, mtpa_per_train)
    power_plant_m = _regress(0, 4000000, 0.7099, 15e6, 2000e6, mtpa_per_train)

    # Offsites
    bog_m = _regress(0, 1e9, -0.547, 2e6, 50e6, mtpa_per_train)
    cond_tank_m = _regress(4.5431e6, 80, None, 5e6, 15e6, mtpa_per_train)
    jetty_topsides_m = _regress(2.134e6, 63600, None, 2e6, 5e6, mtpa_per_train)

    # Marine infrastructure (common, not per-train)
    jetty_head_m = _regress(-4.7934e6, 11.647e6, None, 0, 75e6, num_trains)
    jetty_trestle_m = _regress(0, 12563.3, None, 0, 150e6, mtpa * 1000)  # driver = length proxy

    # Sum per-train costs * num_trains + common
    per_train_direct = (inlet_treat_m + inlet_no_m + ngl_frac_m + liq_m +
                        dehydration_m + end_flash_m + power_plant_m +
                        bog_m + cond_tank_m + jetty_topsides_m)
    total_direct = per_train_direct * num_trains + jetty_head_m + jetty_trestle_m

    # --- TEC Loading Factor (2.8-3.5x depending on location/complexity) ---
    # source: lng_calculator.py L466-506
    _LNG_LOC_FACTORS = {
        'Texas-BTN (GOM)': 1.0, 'US Gulf Coast': 1.0, 'GOM': 1.0,
        'Australia': 1.35, 'Western Australia': 1.45,
        'Papua New Guinea': 1.40, 'Mozambique': 1.30,
        'Qatar': 0.85, 'Nigeria': 1.25, 'Canada': 1.20,
        'Russia': 1.10,
    }
    loc_factor = _LNG_LOC_FACTORS.get(location, 1.0)
    if loc_factor == 1.0:
        # try substring match
        for k, v in _LNG_LOC_FACTORS.items():
            if k.lower() in location.lower() or location.lower() in k.lower():
                loc_factor = v
                break

    loading_factor = 3.1  # base TEC/direct ratio (includes indirects, eng, contingency)
    tec_musd = total_direct * loading_factor * loc_factor / 1e6

    # AACE range (LNG: -30% to +100% — high uncertainty)
    range_low = tec_musd * 0.70
    range_high = tec_musd * 2.00

    return {
        'can_fire': True,
        'model_id': 'Calculator_LNG',
        'estimate_musd': round(tec_musd, 1),
        'estimate_low_musd': round(range_low, 1),
        'estimate_high_musd': round(range_high, 1),
        'detail': {
            'mtpa': mtpa, 'num_trains': num_trains,
            'mtpa_per_train': round(mtpa_per_train, 2),
            'technology': technology,
            'per_train_direct_M': round(per_train_direct / 1e6, 1),
            'total_direct_M': round(total_direct / 1e6, 1),
            'loading_factor': loading_factor,
            'location_factor': loc_factor,
        },
    }
