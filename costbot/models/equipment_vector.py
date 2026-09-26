"""EquipmentVector: 52-dim equipment composition cosine similarity."""
from typing import Dict, List, Optional, Any
import json
import numpy as np
import pandas as pd
from costbot.constants import EQUIPMENT_ALIASES, EQUIPMENT_TYPES_52, EQ_TYPE_INDEX, _PROCESS_EQUIPMENT
from costbot.data import DataStore


# ============================================================================
# Helper functions
# ============================================================================


def _resolve_equipment_type(name: str) -> Optional[str]:
    name_lower = name.lower().strip()
    if name_lower in EQ_TYPE_INDEX:
        return name_lower
    if name_lower in EQUIPMENT_ALIASES:
        return EQUIPMENT_ALIASES[name_lower]
    for alias, canonical in EQUIPMENT_ALIASES.items():
        if alias in name_lower or name_lower in alias:
            return canonical
    for t in EQUIPMENT_TYPES_52:
        if t in name_lower or name_lower in t:
            return t
    return None


_NON_PROCESS_ZERO = {'valve', 'instrument', 'panel', 'meter', 'switchgear', 'transformer'}


def _build_equipment_vector(equipment_items: dict) -> tuple:
    raw = np.zeros(52)
    resolved = {}
    unresolved = []
    total_items = 0
    process_items = 0
    for item_name, count in equipment_items.items():
        canonical = _resolve_equipment_type(item_name)
        if canonical:
            idx = EQ_TYPE_INDEX[canonical]
            raw[idx] += count
            resolved[canonical] = resolved.get(canonical, 0) + count
            total_items += count
            if canonical in _PROCESS_EQUIPMENT:
                process_items += count
        else:
            unresolved.append(item_name)
    # Zero out non-discriminating dims before L2 normalization
    # README: "zero out valve/instrument/panel/meter/switchgear/transformer"
    for eq_type in _NON_PROCESS_ZERO:
        if eq_type in EQ_TYPE_INDEX:
            raw[EQ_TYPE_INDEX[eq_type]] = 0.0
    norm = np.linalg.norm(raw)
    vector_norm = raw / norm if norm > 0 else raw
    return vector_norm, resolved, unresolved, total_items, process_items

# ============================================================================
# Model 6: EquipmentVector
# ============================================================================

def run_equipment_vector(scope: Dict, data: DataStore) -> Dict:
    equipment_list = scope.get('equipment_list')
    if not equipment_list:
        return {'can_fire': False, 'no_fire_reason': 'no_equipment_list',
                'model_id': 'EquipmentVector'}

    # Build user equipment dict
    if isinstance(equipment_list, list):
        eq_dict = {}
        for item in equipment_list:
            if isinstance(item, dict):
                eq_dict[item.get('type', '')] = item.get('count', 1)
            elif isinstance(item, str):
                eq_dict[item] = eq_dict.get(item, 0) + 1
    elif isinstance(equipment_list, dict):
        eq_dict = equipment_list
    else:
        return {'can_fire': False, 'no_fire_reason': 'invalid_equipment_format',
                'model_id': 'EquipmentVector'}

    user_vec, resolved, unresolved, total, process = _build_equipment_vector(eq_dict)
    if total == 0:
        return {'can_fire': False, 'no_fire_reason': 'no_resolved_equipment',
                'model_id': 'EquipmentVector'}

    ev_df = data.equipment_vectors
    if ev_df.empty:
        return {'can_fire': False, 'no_fire_reason': 'equipment_vectors_not_loaded',
                'model_id': 'EquipmentVector'}

    # Parse stored vectors and compute similarity
    matches = []
    for _, row in ev_df.iterrows():
        vec_str = row.get('vector_norm')
        tec = row.get('tec_musd_2024')
        if pd.isna(vec_str) or pd.isna(tec):
            continue
        try:
            if isinstance(vec_str, str):
                pool_vec = np.array(json.loads(vec_str))
            else:
                continue
        except Exception:
            continue

        if len(pool_vec) != 52:
            continue

        # Cosine similarity
        dot = np.dot(user_vec, pool_vec)
        norm_a = np.linalg.norm(user_vec)
        norm_b = np.linalg.norm(pool_vec)
        if norm_a > 0 and norm_b > 0:
            sim = dot / (norm_a * norm_b)
        else:
            sim = 0.0

        if sim > 0.1:
            matches.append({
                'project_name': row.get('project_name', ''),
                'project_id': row.get('project_id', ''),
                'archetype': row.get('archetype', ''),
                'tec_musd_2024': float(tec),
                'similarity': round(float(sim), 4),
                'country': row.get('country', ''),
                'total_items': row.get('total_items', 0),
            })

    if not matches:
        return {'can_fire': False, 'no_fire_reason': 'no_similar_equipment_profiles',
                'model_id': 'EquipmentVector'}

    matches.sort(key=lambda x: -x['similarity'])
    top5 = matches[:5]

    # Weighted average (similarity-weighted)
    weights = np.array([m['similarity'] for m in top5])
    costs = np.array([m['tec_musd_2024'] for m in top5])
    w_sum = weights.sum()
    if w_sum > 0:
        estimate = float(np.dot(weights, costs) / w_sum)
    else:
        estimate = float(np.median(costs))

    return {
        'can_fire': True,
        'model_id': 'EquipmentVector',
        'estimate_musd': round(estimate, 1),
        'estimate_low_musd': round(estimate * 0.5, 1),
        'estimate_high_musd': round(estimate * 1.5, 1),
        'top_matches': top5,
        'resolved_equipment': resolved,
        'unresolved_equipment': unresolved,
        'total_items': total,
        'process_items': process,
    }
