"""Calculator_Pipeline: CET-style section decomposition (UNVERIFIED per README)."""
from typing import Dict, List, Optional, Any
from costbot.data import DataStore


# ============================================================================
# Model 2: Calculator_Pipeline (simplified)
# ============================================================================

def run_calculator_pipeline(scope: Dict, data: DataStore) -> Dict:
    """Pipeline Calculator (P4 upgraded).
    Reference: pipeline_calculator_v2.py — section-level decomposition with CET rate tables.
    Sections: linepipe material, mainline construction, crossings (HDD/open cut),
    MLV stations, metering, pump/compressor stations, engineering, survey, contingency.
    """
    # Inputs as cost_bot_api._run_calculator_pipeline reads them: OD and options
    # from secondary_params (or top level), length from length_km or from
    # primary_capacity in miles/km. Defaults NGL / X65 / rural / 500 m HDD.
    sp = scope.get('secondary_params') or {}
    if not isinstance(sp, dict):
        sp = {}
    def _opt(key, default=None):
        v = sp.get(key)
        return v if v is not None else scope.get(key, default)
    length_km = scope.get('length_km') or scope.get('pipeline_length_km')
    if length_km is None and scope.get('primary_capacity'):
        unit = (scope.get('capacity_unit') or 'miles').lower()
        if unit in ('km', 'miles', 'mile', 'mi'):
            length_km = float(scope['primary_capacity']) * (1.0 if unit == 'km' else 1.60934)
    od_in = _opt('od_inches') or scope.get('diameter_inches', 36)
    location = scope.get('location', '')
    grade = _opt('grade', 'X65')
    service = str(_opt('service', 'NGL')).lower()
    congestion = str(_opt('congestion', 'rural')).lower()
    num_hdd = _opt('num_hdd_crossings', 0)
    avg_hdd_m = _opt('avg_hdd_length_m', 500.0)
    num_pump_stations = _opt('num_pump_stations')

    if length_km is None:
        return {'can_fire': False, 'no_fire_reason': 'missing_pipeline_length',
                'model_id': 'Calculator_Pipeline'}

    length_km = float(length_km)
    od_in = float(od_in)
    length_ft = length_km * 3280.84

    # --- Congestion factor (CET rows 106-110) ---
    _CONGESTION = {'rural': 0.9, 'low': 0.9, 'moderate': 0.95, 'medium': 0.95,
                   'high': 1.0, 'severe': 1.2, 'unconventional': 1.3}
    congestion_f = _CONGESTION.get(congestion, 1.0)

    # --- Location factor (Pipeline Rates sheet) ---
    _PIPE_LOC = {
        'Texas-BTN (GOM)': 1.0, 'US Gulf Coast': 1.0, 'GOM': 1.0,
        'Texas-West (Permian)': 1.16, 'Louisiana': 0.98,
        'Alberta': 1.38, 'British Columbia': 1.69, 'Eastern Canada': 1.50,
        'Appalachia': 1.27, 'Midwest': 1.10, 'Northeast US': 1.50,
        'Rocky Mountain': 1.19, 'California': 1.82, 'Southeast US': 0.90,
        'Western Canada': 1.56,
    }
    loc_f = 1.0
    for k, v in _PIPE_LOC.items():
        if k.lower() == location.lower() or k.lower() in location.lower():
            loc_f = v
            break

    # --- I. Linepipe Material ---
    # Pipe weight (lb/ft) = 10.69 * (OD - WT) * WT
    wt_in = 0.5 if od_in >= 24 else 0.375 if od_in >= 12 else 0.25
    pipe_wt_lb_ft = 10.69 * (od_in - wt_in) * wt_in
    grade_mult = {'X42': 0.85, 'X52': 0.90, 'X60': 0.95, 'X65': 1.0, 'X70': 1.05, 'X80': 1.15}.get(grade, 1.0)
    steel_price_per_lb = 0.45 * grade_mult  # ~$900/ton base
    linepipe_cost = pipe_wt_lb_ft * steel_price_per_lb * length_ft

    # --- II. Mainline Construction (labor + equipment, GOM base) ---
    # CET base rate per foot varies with diameter
    _MAINLINE_RATE = {  # $/ft GOM2000 base (from CET mainline spread rates)
        8: 55, 10: 65, 12: 80, 14: 95, 16: 110, 18: 130,
        20: 150, 24: 195, 30: 260, 36: 330, 42: 420, 48: 520, 54: 630, 60: 750,
    }
    # Interpolate from nearest
    diameters = sorted(_MAINLINE_RATE.keys())
    if od_in <= diameters[0]:
        ml_rate = _MAINLINE_RATE[diameters[0]]
    elif od_in >= diameters[-1]:
        ml_rate = _MAINLINE_RATE[diameters[-1]]
    else:
        for i in range(len(diameters)-1):
            if diameters[i] <= od_in <= diameters[i+1]:
                lo, hi = diameters[i], diameters[i+1]
                frac = (od_in - lo) / (hi - lo)
                ml_rate = _MAINLINE_RATE[lo] + frac * (_MAINLINE_RATE[hi] - _MAINLINE_RATE[lo])
                break
    mainline_cost = ml_rate * congestion_f * loc_f * length_ft

    # --- III. Crossings (HDD) ---
    hdd_rate_per_ft = 850.0 * (od_in / 36.0) ** 1.2  # CET crossing base crew rate * diameter scale
    hdd_total_ft = num_hdd * avg_hdd_m * 3.28084
    hdd_cost = hdd_rate_per_ft * hdd_total_ft * loc_f

    # --- IV. MLV Stations ---
    mlv_spacing_km = 24 if service == 'oil' else 32
    num_mlv = max(0, int(length_km / mlv_spacing_km) - 1) if length_km > mlv_spacing_km else 0
    mlv_cost_each = 160000 + 1200 * od_in  # CET MLV material+labor formula
    mlv_cost = num_mlv * mlv_cost_each * loc_f

    # --- V. Pump/Compressor Stations ---
    if num_pump_stations is None:
        if service == 'oil' and length_km > 200:
            num_pump_stations = max(1, int(length_km / 200))
        elif service == 'gas' and length_km > 150:
            num_pump_stations = max(1, int(length_km / 150))
        else:
            num_pump_stations = 0
    station_cost_each = 5.5e6 if service == 'oil' else 8.0e6  # CET pump/compressor station reference
    station_cost = num_pump_stations * station_cost_each * loc_f

    # --- VI. Metering Stations (2 per pipeline: origin + destination) ---
    meter_cost_each = 1.2e6 + 50 * od_in * 1000  # CET metering material + labor
    metering_cost = 2 * meter_cost_each * loc_f

    # --- VII. Engineering + Survey ---
    engineering_cost = 32.63 * length_ft + 2_000_000  # CET row 1315
    survey_cost = 15.999 * length_ft + 241_300  # CET row 1315

    # --- Sum Direct Costs ---
    direct_total = (linepipe_cost + mainline_cost + hdd_cost + mlv_cost +
                    station_cost + metering_cost)

    # --- Indirects: engineering + survey + contingency (20%) + escalation (6%) ---
    subtotal = direct_total + engineering_cost + survey_cost
    contingency = subtotal * 0.20
    tec = (subtotal + contingency) * 1.06  # 6% escalation

    tec_musd = tec / 1e6

    # Range as cost_bot_api: -30% / +50%
    range_low = tec_musd * 0.7
    range_high = tec_musd * 1.5

    return {
        'can_fire': True,
        'model_id': 'Calculator_Pipeline',
        'estimate_musd': round(tec_musd, 1),
        'estimate_low_musd': round(range_low, 1),
        'estimate_high_musd': round(range_high, 1),
        'warning': ('Pipeline calculator is UNVERIFIED: pipeline truth values differ '
                    'between sources (README, MEASUREMENTS_LOG). Treat as directional.'),
        'detail': {
            'length_km': length_km, 'od_inches': od_in,
            'linepipe_M': round(linepipe_cost / 1e6, 1),
            'mainline_M': round(mainline_cost / 1e6, 1),
            'hdd_crossings_M': round(hdd_cost / 1e6, 1),
            'mlv_stations': num_mlv,
            'pump_stations': num_pump_stations,
            'station_cost_M': round(station_cost / 1e6, 1),
            'engineering_M': round(engineering_cost / 1e6, 1),
            'direct_total_M': round(direct_total / 1e6, 1),
            'contingency_M': round(contingency / 1e6, 1),
            'location_factor': loc_f,
            'congestion_factor': congestion_f,
        },
    }
