"""Unconventional: facility-type lookup for onshore_unconventional with the
capacity-aware 2-point interpolation of cost_bot_api._run_unconventional.

- within the capacity range of same-unit-family peers: 2-point linear interpolation
- outside that range: nearest peer's cost, with an extrapolation warning
- no capacity / fewer than 2 same-family peers: unscaled median, flagged
"""
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from costbot.constants import UNCONVENTIONAL_FACILITY_ALIASES, normalize_capacity
from costbot.data import DataStore


def _clean(s) -> str:
    return str(s or '').lower().strip().replace(' ', '_').replace('-', '_')


def run_unconventional(scope: Dict, data: DataStore) -> Dict:
    facility_type = scope.get('facility_type')
    if not facility_type:
        return {'can_fire': False, 'no_fire_reason': 'missing_facility_type', 'model_id': 'Unconventional'}
    pool = data.pool
    if pool.empty:
        return {'can_fire': False, 'no_fire_reason': 'pool_not_loaded', 'model_id': 'Unconventional'}
    uncon = pool[pool['archetype'] == 'onshore_unconventional']
    excl = [str(x) for x in (scope.get('exclude_planview_ids') or [])]
    if excl and 'planview_id' in uncon.columns:  # LOOCV: evaluation scripts drop the project itself
        uncon = uncon[~uncon['planview_id'].astype(str).isin(excl)]
    if uncon.empty or 'facility_type' not in uncon.columns:
        return {'can_fire': False, 'no_fire_reason': 'no_unconventional_in_pool', 'model_id': 'Unconventional'}

    ft_clean = _clean(facility_type)
    ft_query = UNCONVENTIONAL_FACILITY_ALIASES.get(ft_clean, ft_clean)
    pool_ft = uncon['facility_type'].map(_clean)
    peers = uncon[pool_ft == ft_query]
    if peers.empty:
        # API's broader match: LIKE '%<first token>%'
        peers = uncon[uncon['facility_type'].fillna('').str.lower().str.contains(ft_clean.split('_')[0], regex=False)]
    if peers.empty:
        return {'can_fire': False, 'no_fire_reason': f'no_peers_for_{facility_type}',
                'model_id': 'Unconventional', 'facility_type': ft_query}

    costs = peers['tec_musd_normalized_2024'].dropna().values.astype(float)
    if len(costs) == 0:
        return {'can_fire': False, 'no_fire_reason': 'no_valid_costs', 'model_id': 'Unconventional'}

    user_cap = scope.get('primary_capacity')
    user_unit = scope.get('capacity_unit', '')
    user_norm = normalize_capacity(user_cap, user_unit)

    family_peers = []  # (normalized_cap, cost, name, raw_cap, raw_unit)
    for _, row in peers.iterrows():
        p_norm = normalize_capacity(row.get('primary_capacity'), row.get('capacity_unit') or '')
        p_cost = row.get('tec_musd_normalized_2024')
        if p_norm and user_norm and p_norm[2] == user_norm[2] and pd.notna(p_cost):
            family_peers.append((p_norm[0], float(p_cost), row.get('project_name', '?'),
                                 float(row.get('primary_capacity')), row.get('capacity_unit') or ''))
    family_context = None
    if user_norm and family_peers:
        family_context = (f"only {len(family_peers)} {user_norm[2].replace('_', ' ')} {facility_type}(s) in pool: "
                          + ', '.join(f"{fp[2]} ({fp[3]:.0f} {fp[4]})" for fp in sorted(family_peers, key=lambda x: x[0])))
    peer_names = peers['project_name'].tolist()[:10]
    base = {'can_fire': True, 'model_id': 'Unconventional', 'facility_type': ft_query,
            'n_peers': int(len(costs)), 'peer_names': peer_names, 'family_context': family_context}

    if user_norm and len(family_peers) >= 2:
        family_peers.sort(key=lambda x: x[0])
        caps = [fp[0] for fp in family_peers]
        tecs = [fp[1] for fp in family_peers]
        user_c = user_norm[0]
        points = [{'name': fp[2], 'capacity': fp[3], 'unit': fp[4], 'tec_musd': round(fp[1], 1)} for fp in family_peers]
        if caps[0] <= user_c <= caps[-1]:
            lower_idx = max(i for i, c in enumerate(caps) if c <= user_c)
            upper_idx = min(lower_idx + 1, len(caps) - 1)
            if lower_idx == upper_idx or caps[upper_idx] == caps[lower_idx]:
                est, method = tecs[lower_idx], 'exact_match'
            else:
                frac = (user_c - caps[lower_idx]) / (caps[upper_idx] - caps[lower_idx])
                est, method = tecs[lower_idx] + frac * (tecs[upper_idx] - tecs[lower_idx]), '2-point interpolation'
            return {**base, 'estimate_musd': round(est, 1),
                    'estimate_low_musd': round(min(tecs) * 0.8, 1), 'estimate_high_musd': round(max(tecs) * 1.2, 1),
                    'model_variant': method, 'interpolation_points': points,
                    'detail': {'method': method, 'between': [family_peers[lower_idx][2], family_peers[upper_idx][2]],
                               'user_capacity_canonical': round(user_c, 2), 'unit_family': user_norm[2]}}
        nearest, direction = (family_peers[0], 'below') if user_c < caps[0] else (family_peers[-1], 'above')
        return {**base, 'estimate_musd': round(nearest[1], 1),
                'estimate_low_musd': round(min(tecs) * 0.7, 1), 'estimate_high_musd': round(max(tecs) * 1.5, 1),
                'model_variant': 'nearest_peer (no extrapolation)', 'interpolation_points': points,
                'warning': (f"Capacity {user_cap} {user_unit} is {direction} the range of known peers "
                            f"({caps[0]:.0f} to {caps[-1]:.0f} {user_norm[1]}); nearest peer cost returned without extrapolation."),
                'detail': {'method': 'nearest_peer', 'nearest': nearest[2], 'direction': direction,
                           'user_capacity_canonical': round(user_c, 2), 'unit_family': user_norm[2]}}

    est = float(np.median(costs))
    reason = 'no user capacity provided' if not user_norm else f'only {len(family_peers)} same-family peer(s) with capacity data'
    return {**base, 'estimate_musd': round(est, 1),
            'estimate_low_musd': round(float(np.min(costs)), 1), 'estimate_high_musd': round(float(np.max(costs)), 1),
            'model_variant': 'facility_type_lookup (capacity-blind)', 'capacity_scaling_unavailable': True,
            'detail': {'method': 'median', 'reason': reason, 'n_peers': int(len(costs))}}
