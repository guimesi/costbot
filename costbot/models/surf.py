"""SURF_User: subsea component bottom-up (component model, not TEC)."""
from typing import Dict, List, Optional, Any
import json
from costbot.data import DataStore


# ============================================================================
# Model 9: SURF_User (simplified from surf_estimator.py)
# ============================================================================

def run_surf_user(scope: Dict, data: DataStore) -> Dict:
    surf_scope = scope.get('surf_scope', {}) or {}
    if isinstance(surf_scope, str):
        try:
            surf_scope = json.loads(surf_scope)
        except Exception:
            surf_scope = {}

    if not surf_scope:
        return {'can_fire': False, 'no_fire_reason': 'no_surf_scope',
                'model_id': 'SURF_User', 'is_component': True}

    water_depth = surf_scope.get('water_depth_m', 1500)
    n_trees = sum(surf_scope.get('subsea_trees', {}).values()) if isinstance(surf_scope.get('subsea_trees'), dict) else surf_scope.get('n_trees', 0)
    n_flowlines = len(surf_scope.get('flowlines', []))
    n_risers = sum(r.get('count', 1) for r in surf_scope.get('risers', []))

    if n_trees == 0 and n_flowlines == 0:
        return {'can_fire': False, 'no_fire_reason': 'insufficient_surf_scope',
                'model_id': 'SURF_User', 'is_component': True}

    # Simplified SURF estimation
    tree_cost = n_trees * 12.0  # ~$12M per subsea tree (installed)
    flowline_cost = n_flowlines * 25.0  # ~$25M per flowline (average)
    riser_cost = n_risers * 15.0  # ~$15M per riser
    manifold_cost = sum(surf_scope.get('manifolds', {}).values()) * 8.0 if isinstance(surf_scope.get('manifolds'), dict) else 0
    umbilical_cost = len(surf_scope.get('umbilicals', [])) * 10.0

    heritage_total = tree_cost + flowline_cost + riser_cost + manifold_cost + umbilical_cost

    # Apply calibration factor (from LOOCV mean factor ~1.34)
    calibration_factor = 1.34
    calibrated_total = heritage_total * calibration_factor

    return {
        'can_fire': True,
        'model_id': 'SURF_User',
        'is_component': True,
        'component_type': 'SURF',
        'estimate_musd': round(calibrated_total, 1),
        'estimate_low_musd': round(calibrated_total * 0.7, 1),
        'estimate_high_musd': round(calibrated_total * 1.3, 1),
        'detail': {
            'heritage_total_M': round(heritage_total, 1),
            'calibration_factor': calibration_factor,
            'n_trees': n_trees,
            'n_flowlines': n_flowlines,
            'n_risers': n_risers,
            'water_depth_m': water_depth,
        },
    }
