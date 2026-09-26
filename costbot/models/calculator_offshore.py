"""Calculator_Offshore: topsides weight curves + parametric hull."""
from typing import Dict, List, Optional, Any
import json
from costbot.data import DataStore


# ============================================================================
# Model 4: Calculator_Offshore (simplified)
# ============================================================================

def run_calculator_offshore(scope: Dict, data: DataStore) -> Dict:
    """Offshore Calculator (P4 upgraded).
    Reference: offshore_calculator.py — 16 steps, CET weight models, parametric hull,
    subsea equipment, SURF, installation, transportation, engineering, owners, contingency.
    """
    topsides_te = scope.get('topsides_weight_te')
    sp = scope.get('secondary_params') or {}
    if isinstance(sp, str):
        try:
            sp = json.loads(sp)
        except Exception:
            sp = {}
    if topsides_te is None:
        topsides_te = sp.get('topsides_weight_te')

    kbpd = scope.get('primary_capacity')
    hull_type = sp.get('hull_type', 'FPSO_newbuild')
    location = scope.get('location', '')
    water_depth_m = sp.get('water_depth_m', 1500)
    n_wells = sp.get('n_wells', 0)
    surf_km = sp.get('surf_km', 0)
    fab_location = sp.get('fab_location', 'asian')

    # --- Step 1: Topsides Weight (CET row 227 regressions) ---
    _WEIGHT_MODELS = {
        'FPSO_conversion': lambda k: 1598.70 * (k ** 0.4431),
        'FPSO_newbuild': lambda k: 63.69 * k + 10982,
        'GBS': lambda k: 36.29 * k + 24903,
        'semi_sub': lambda k: 287.19 * (k ** 0.8041),
        'TLP': lambda k: 287.19 * (k ** 0.8041),
        'jacket_shallow': lambda k: 4.61 * k + 983,
        'jacket_deep': lambda k: 4.61 * k + 983,
        'SPJ_oil': lambda k: 50 * k + 4250,
        'SPJ_gas': lambda k: k * 55 + 6500,
        'spar': lambda k: 200 * (k ** 0.6),
    }

    if topsides_te is None and kbpd:
        kbpd_f = float(kbpd)
        wt_fn = _WEIGHT_MODELS.get(hull_type, _WEIGHT_MODELS['FPSO_newbuild'])
        topsides_te = max(0, wt_fn(kbpd_f))
    elif topsides_te is None:
        return {'can_fire': False, 'no_fire_reason': 'missing_topsides_weight',
                'model_id': 'Calculator_Offshore'}

    topsides_te = float(topsides_te)

    # --- Step 2: Topsides Cost (CET rate per MT by hull type) ---
    _TOPSIDES_RATE = {  # $/MT, CET discipline-based
        'FPSO_newbuild': 45000, 'FPSO_conversion': 45000,
        'semi_sub': 55000, 'TLP': 60000, 'spar': 50000,
        'jacket_shallow': 35000, 'jacket_deep': 40000,
        'GBS': 40000, 'SPJ_oil': 40000, 'SPJ_gas': 40000,
    }
    topsides_rate = _TOPSIDES_RATE.get(hull_type, 45000)
    topsides_cost_M = topsides_te * topsides_rate / 1e6

    # --- Step 3: Hull Cost (parametric, ref L243-365) ---
    _FAB_FACTOR = {'asian': 0.75, 'gom': 1.0, 'european': 1.15, 'middle_east': 0.85}
    fab_factor = _FAB_FACTOR.get(fab_location.lower(), 1.0)

    ht = hull_type.upper()
    if 'FPSO' in ht or 'FSO' in ht:
        storage_Mbbls = 2.0
        if 'CONVERSION' in ht or 'converted' in hull_type.lower():
            hull_cost_M = 175 * (storage_Mbbls / 1.5) ** 0.5 * fab_factor
        else:
            hull_cost_M = 350 * (storage_Mbbls / 1.7) ** 0.7 * fab_factor
    elif 'SEMI' in ht:
        hull_cost_M = topsides_te * 4700 / 1e6 * fab_factor
    elif 'TLP' in ht:
        hull_cost_M = topsides_te * 6000 / 1e6 * fab_factor
    elif 'SPAR' in ht:
        hull_cost_M = topsides_te * 4000 / 1e6 * fab_factor
    elif 'JACKET' in ht or 'SPJ' in ht:
        wd_factor = (water_depth_m / 1000) ** 1.05
        load_factor = (topsides_te / 10000) ** 0.5
        hull_cost_M = 110 * wd_factor * load_factor * fab_factor
    elif 'GBS' in ht:
        concrete_m3 = 80000 * (water_depth_m / 100)
        hull_cost_M = (concrete_m3 * 5500 / 1e6) + 50
    else:
        hull_cost_M = 350 * fab_factor

    # --- Step 4: Yard CM + HUC (~8% of topsides+hull) ---
    cm_huc_M = (topsides_cost_M + hull_cost_M) * 0.08

    # --- Step 5: Subsea Equipment (CET formula: base * depth scaling * qty) ---
    subsea_cost_M = 0.0
    if n_wells and n_wells > 0:
        tree_base_M = 15.0  # $15M per tree (GOM deepwater)
        ds_x = 1.0 + max(0, water_depth_m - 500) * 0.0002  # depth surcharge
        subsea_cost_M = n_wells * tree_base_M * ds_x

    # --- Step 6: SURF (flowlines + risers, CET OD×depth table) ---
    surf_cost_M = 0.0
    if surf_km and surf_km > 0:
        # Base rate: $3-6M/km depending on water depth
        base_surf_rate = 3.0 + min(water_depth_m, 3000) * 0.002  # ~$3M/km to $9M@3000m
        surf_cost_M = surf_km * base_surf_rate

    # --- Step 7: SURF Installation (~60% of SURF material) ---
    surf_install_M = surf_cost_M * 0.60

    # --- Step 8: Ocean Transportation ---
    if 'FPSO' in ht:
        transport_M = 50.0  # FPSO tow + mooring hookup
    elif 'JACKET' in ht:
        transport_M = 15.0
    else:
        transport_M = 30.0

    # --- Step 9: Sum Direct Costs ---
    directs_M = (topsides_cost_M + hull_cost_M + cm_huc_M + subsea_cost_M +
                 surf_cost_M + surf_install_M + transport_M)

    # --- Step 10: Engineering (8-12% of directs by hull type) ---
    eng_pct = 0.10 if 'FPSO' in ht else 0.12
    engineering_M = directs_M * eng_pct

    # --- Step 11: Owners Cost (5-8% of subtotal) ---
    owners_M = (directs_M + engineering_M) * 0.06

    # --- Step 12: Subtotal ---
    subtotal_M = directs_M + engineering_M + owners_M

    # --- Step 13: Contingency (15-25% depending on complexity) ---
    contingency_pct = 0.20
    contingency_M = subtotal_M * contingency_pct

    # --- Step 14: TEC ---
    tec_M = subtotal_M + contingency_M

    # --- Location factor (offshore-specific, NOT EMMA) ---
    # Note: EMMA removed — the parametric rates ($45K/MT, $15M/tree, $6.8M/km)
    # are already calibrated at 2024 cost levels. EMMA was double-counting
    # escalation, inflating offshore estimates by ~2x.
    emma = 1.0  # neutral — location already reflected in fab_factor

    # --- AACE range (offshore: -25% to +50%) ---
    range_low = tec_M * 0.75
    range_high = tec_M * 1.50

    return {
        'can_fire': True,
        'model_id': 'Calculator_Offshore',
        'estimate_musd': round(tec_M, 1),
        'estimate_low_musd': round(range_low, 1),
        'estimate_high_musd': round(range_high, 1),
        'detail': {
            'topsides_te': round(topsides_te, 0),
            'topsides_cost_M': round(topsides_cost_M, 1),
            'hull_type': hull_type,
            'hull_cost_M': round(hull_cost_M, 1),
            'subsea_cost_M': round(subsea_cost_M, 1),
            'surf_cost_M': round(surf_cost_M, 1),
            'surf_install_M': round(surf_install_M, 1),
            'directs_M': round(directs_M, 1),
            'engineering_M': round(engineering_M, 1),
            'contingency_M': round(contingency_M, 1),
            'emma_factor': 1.0,  # EMMA disabled for offshore
            'fab_factor': fab_factor,
        },
    }
