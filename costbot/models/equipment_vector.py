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

def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _parse_vector_table(ev_df: pd.DataFrame):
    """One-time parse of ref_equipment_vectors.csv into a (n, 52) float matrix
    plus per-row metadata. Rows with a missing TEC or an unparseable / wrong
    length vector are skipped, exactly as the per-call loop used to do."""
    rows, meta = [], []
    for _, row in ev_df.iterrows():
        vec_str = row.get('vector_norm')
        tec = row.get('tec_musd_2024')
        if pd.isna(vec_str) or pd.isna(tec) or not isinstance(vec_str, str):
            continue
        try:
            vec = np.asarray(json.loads(vec_str), dtype=float)
        except Exception:
            continue
        if vec.shape != (52,):
            continue
        rows.append(vec)
        meta.append({
            'project_name': row.get('project_name', ''),
            'project_id': row.get('project_id', ''),
            'archetype': row.get('archetype', ''),
            'tec_musd_2024': float(tec),
            'country': row.get('country', ''),
            'total_items': row.get('total_items', 0),
        })
    matrix = np.vstack(rows) if rows else np.zeros((0, 52))
    return matrix, meta


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
    if process < 2:
        # cost_bot_api: valves/instruments alone do not discriminate
        return {'can_fire': False, 'model_id': 'EquipmentVector',
                'no_fire_reason': f'too_few_process_items ({process}). Need pumps/exchangers/towers/drums, not just valves/instruments.',
                'resolved_equipment': resolved, 'unresolved_equipment': unresolved}

    ev_df = data.equipment_vectors
    if ev_df.empty:
        return {'can_fire': False, 'no_fire_reason': 'equipment_vectors_not_loaded',
                'model_id': 'EquipmentVector'}

    matrix, meta = data.derived('equipment_vector_matrix', lambda: _parse_vector_table(ev_df))
    if matrix.shape[0] == 0:
        return {'can_fire': False, 'no_fire_reason': 'no_parseable_equipment_vectors',
                'model_id': 'EquipmentVector'}

    # Pool gates as cost_bot_api._run_equipment_vector_user: TEC >= screening
    # floor, at least 3 items, and the archetype's own subset when it has >= 5 rows.
    keep = np.array([(m['tec_musd_2024'] >= 20.0) and (_int(m['total_items']) >= 3) for m in meta], dtype=bool)
    excl = {str(x) for x in (scope.get('exclude_planview_ids') or [])}
    if excl:  # LOOCV: evaluation scripts drop the project's own vector
        keep &= np.array([str(m['project_id']) not in excl for m in meta], dtype=bool)
    archetype = scope.get('archetype')
    if archetype:
        arch_mask = keep & np.array([str(m['archetype']) == str(archetype) for m in meta], dtype=bool)
        if arch_mask.sum() >= 5:
            keep = arch_mask
    if not keep.any():
        return {'can_fire': False, 'no_fire_reason': 'empty_vector_pool', 'model_id': 'EquipmentVector'}

    # Cosine similarity against every stored vector in one matrix product.
    # Stored vectors are already L2-normalised but we renormalise defensively.
    norm_a = float(np.linalg.norm(user_vec))
    norms_b = np.linalg.norm(matrix, axis=1)
    with np.errstate(divide='ignore', invalid='ignore'):
        sims = np.where((norm_a > 0) & (norms_b > 0), matrix @ user_vec / (norm_a * norms_b), 0.0)
    sims = np.where(keep, sims, 0.0)

    matches = []
    for i in np.where(sims >= 0.30)[0]:  # API threshold for sparse user input
        m = meta[i]
        matches.append({
            'project_name': m['project_name'],
            'project_id': m['project_id'],
            'archetype': m['archetype'],
            'tec_musd_2024': m['tec_musd_2024'],
            'similarity': round(float(sims[i]), 4),
            'country': m['country'],
            'total_items': m['total_items'],
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

    # Range: P20/P80 of the broader candidate set (top 15), as in the API
    broad = np.array([m['tec_musd_2024'] for m in matches[:15]])
    p20, p80 = float(np.percentile(broad, 20)), float(np.percentile(broad, 80))

    return {
        'can_fire': True,
        'model_id': 'EquipmentVector',
        'estimate_musd': round(estimate, 1),
        'estimate_low_musd': round(p20, 1),
        'estimate_high_musd': round(p80, 1),
        'n_candidates': len(matches),
        'top_matches': top5,
        'resolved_equipment': resolved,
        'unresolved_equipment': unresolved,
        'total_items': total,
        'process_items': process,
    }
