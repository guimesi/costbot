"""Unconventional: facility-type median lookup for onshore_unconventional."""
from typing import Dict, List, Optional, Any
import numpy as np
from costbot.constants import UNCONVENTIONAL_FACILITY_ALIASES
from costbot.data import DataStore


# ============================================================================
# Model 7: Unconventional
# ============================================================================

def run_unconventional(scope: Dict, data: DataStore) -> Dict:
    facility_type = (scope.get('facility_type') or '').lower().strip().replace(' ', '_')
    pool = data.pool.copy()
    if pool.empty:
        return {'can_fire': False, 'no_fire_reason': 'pool_not_loaded', 'model_id': 'Unconventional'}

    # Filter to unconventional entries
    uncon = pool[pool['archetype'] == 'onshore_unconventional'].copy()
    if uncon.empty:
        return {'can_fire': False, 'no_fire_reason': 'no_unconventional_in_pool', 'model_id': 'Unconventional'}

    lookup_ft = UNCONVENTIONAL_FACILITY_ALIASES.get(facility_type, facility_type)

    # Match by facility_type
    if lookup_ft and 'facility_type' in uncon.columns:
        peers = uncon[uncon['facility_type'].fillna('').str.lower().str.strip() == lookup_ft]
    else:
        peers = uncon

    if peers.empty:
        # No peers for this facility_type — don't fall back to all, can't fire
        return {'can_fire': False, 'no_fire_reason': f'no_peers_for_{lookup_ft}',
                'model_id': 'Unconventional', 'facility_type': lookup_ft}

    costs = peers['tec_musd_normalized_2024'].dropna().values
    if len(costs) == 0:
        return {'can_fire': False, 'no_fire_reason': 'no_cost_data', 'model_id': 'Unconventional'}

    estimate = float(np.median(costs))

    return {
        'can_fire': True,
        'model_id': 'Unconventional',
        'estimate_musd': round(estimate, 1),
        'estimate_low_musd': round(float(np.min(costs)), 1),
        'estimate_high_musd': round(float(np.max(costs)), 1),
        'n_peers': len(costs),
        'facility_type': lookup_ft or 'all_unconventional',
        'peer_names': peers['project_name'].tolist()[:10],
    }
