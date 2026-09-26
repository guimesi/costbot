"""Composite: multi-item scope builder matched against the frankenstein chip library."""
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from costbot.data import DataStore


# ============================================================================
# Model 8: Composite (Chip Matching)
# ============================================================================

# --- Scope Piece Keyword Matching (from composite_estimator.py) ---
# Curated synonym table: maps user terms to patterns in chip scope_name/scope_type.
# source: composite_estimator.py L240-281
_SCOPE_SYNONYMS = {
    'furnaces': ['furnace', 'furnaces', 'epf', 'heater'],
    'hydrogen': ['h2', 'hydrogen'],
    'hydrotreater': ['hydrotreater', 'hdt', 'hds'],
    'hydrocracker': ['hydrocracker', 'hcu', 'hydrocracking'],
    'topper': ['topper', 'desalter', 'cdu', 'crude unit'],
    'reformer': ['reformer', 'reforming', 'ccr'],
    'coker': ['coker', 'coking', 'delayed coker'],
    'fcc': ['fcc', 'fluid cat', 'catalytic crack'],
    'alkylation': ['alky', 'alkylation'],
    'polyethylene': ['pe', 'polyethylene'],
    'olefins': ['olefins', 'olefin', 'ethylene'],
    'meg': ['meg', 'mono ethylene glycol'],
    'compression': ['compression', 'compressor', 'dehydration'],
    'injection': ['injection', 'injector'],
    'utilities': ['utilities', 'osbl', 'offsites', 'offsite'],
    'infrastructure': ['infrastructure', 'infra'],
    'pipeline': ['pipeline', 'flowline', 'surf'],
    'fpso': ['fpso', 'floating production'],
    'surf': ['surf', 'subsea', 'riser', 'flowline'],
    'drilling': ['drilling', 'drill', 'wells'],
    'topsides': ['topsides', 'topside'],
    'mining': ['mining', 'opp', 'ore'],
    'storage': ['storage', 'storage wells'],
    'ccs facilities': ['facilities', 'capture'],
    'onsites': ['onsites', 'onsite', 'isbl'],
    'revamp': ['revamp', 'retrofit'],
}

# Adjacent archetypes for fallback peer search
_ARCHETYPE_ADJACENCY = {
    'refinery_bf': ['refinery_gf', 'onshore_petchem', 'renewable_diesel'],
    'refinery_gf': ['refinery_bf', 'onshore_petchem'],
    'onshore_petchem': ['integrated_petchem', 'refinery_gf'],
    'integrated_petchem': ['onshore_petchem'],
    'ccs': ['gas_processing', 'onshore_petchem'],
    'gas_processing': ['ccs', 'onshore_petchem'],
    'pipeline_mainline': ['pipeline_gathering'],
    'pipeline_gathering': ['pipeline_mainline'],
    'offshore_fpso': ['offshore_platform'],
    'offshore_platform': ['offshore_fpso'],
    'lng_onshore': ['gas_processing'],
    'onshore_unconventional': [],
    'oil_sands': [],
}


def _match_chip_score(target: str, chip_name: str, chip_desc: str = None,
                      chip_scope_type: str = None) -> float:
    """Score how well a chip matches a target keyword (0-1).
    5-tier matching from composite_estimator.py L300-428.
    """
    target_lower = target.lower().strip()
    name_lower = (chip_name or '').lower()
    desc_lower = (chip_desc or '').lower()
    stype_lower = (chip_scope_type or '').lower()

    # Tier 1: Direct substring on chip name
    if target_lower in name_lower:
        return 1.0

    # Tier 1.5: Multi-word target — all words in name
    target_words = target_lower.split()
    if len(target_words) > 1:
        if all(w in name_lower for w in target_words):
            return 0.95
        hits = sum(1 for w in target_words if w in name_lower)
        if hits >= 2:
            return 0.85

    # Tier 2: Synonym match on chip name
    synonyms = _SCOPE_SYNONYMS.get(target_lower, [target_lower])
    for syn in synonyms:
        if syn.lower() in name_lower:
            return 0.9
    # Reverse synonym lookup
    for group_key, group_syns in _SCOPE_SYNONYMS.items():
        if target_lower in [s.lower() for s in group_syns]:
            for syn in group_syns:
                if syn.lower() in name_lower:
                    return 0.8
            if group_key.lower() in name_lower:
                return 0.8

    # Tier 3: Keyword match on description
    if desc_lower:
        if target_lower in desc_lower:
            return 0.85
        for syn in synonyms:
            if syn.lower() in desc_lower:
                return 0.65

    # Tier 4: scope_type match
    if stype_lower and target_lower in stype_lower:
        return 0.7

    # Tier 5: Multi-word intersection
    target_set = set(target_lower.split())
    for text in [name_lower, desc_lower]:
        if text:
            text_words = set(w for w in text.replace('/', ' ').replace('-', ' ').split() if len(w) > 2)
            if len(target_set & text_words) >= 2:
                return 0.6

    return 0.0


def _iqr_filter(costs: np.ndarray) -> np.ndarray:
    """Remove IQR outliers from cost array."""
    if len(costs) < 4:
        return costs
    q1 = np.percentile(costs, 25)
    q3 = np.percentile(costs, 75)
    iqr = q3 - q1
    if iqr <= 0:
        return costs
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    return costs[(costs >= lo) & (costs <= hi)]


def run_composite(scope: Dict, data: DataStore) -> Dict:
    """Composite model — semantic hybrid chip matching (P2).
    Ports 5 key mechanisms from composite_estimator.py:
    1. Archetype filtering with adjacency fallback
    2. 5-tier keyword matching with synonym expansion
    3. IQR outlier removal on matched chip costs
    4. Match score weighting
    5. Magnitude gating (±1.0 log decade)
    """
    scope_items = scope.get('scope_items', [])
    if not scope_items:
        return {'can_fire': False, 'no_fire_reason': 'no_scope_items',
                'model_id': 'Composite'}

    chips_df = data.frankenstein
    if chips_df.empty:
        return {'can_fire': False, 'no_fire_reason': 'chips_not_loaded',
                'model_id': 'Composite'}

    archetype = scope.get('archetype', '')

    # --- Archetype filtering ---
    # Try exact archetype first, then adjacent, then all chips
    pool_df = chips_df.copy()
    arch_filter_used = 'none'
    if archetype:
        # frankenstein doesn't have archetype column — use semantic classifications
        sem_df = data.semantic_chips
        if not sem_df.empty and 'archetype' in sem_df.columns:
            # Get planview_ids for same archetype
            same_arch_ids = set(sem_df[sem_df['archetype'] == archetype]['planview_id'].astype(str))
            adj_archetypes = _ARCHETYPE_ADJACENCY.get(archetype, [])
            adj_ids = set(sem_df[sem_df['archetype'].isin(adj_archetypes)]['planview_id'].astype(str))

            same_mask = pool_df['planview_id'].astype(str).isin(same_arch_ids)
            adj_mask = pool_df['planview_id'].astype(str).isin(same_arch_ids | adj_ids)

            if same_mask.sum() >= 10:
                pool_df = pool_df[same_mask]
                arch_filter_used = 'same_archetype'
            elif adj_mask.sum() >= 10:
                pool_df = pool_df[adj_mask]
                arch_filter_used = 'adjacent_archetype'
            # else: use all chips

    # --- Magnitude gating: filter chips within ±1.0 log decade of project scale ---
    user_cap = scope.get('primary_capacity')
    if user_cap and user_cap > 0 and 'capacity_value' in pool_df.columns:
        cap_col = pool_df['capacity_value'].dropna()
        if len(cap_col) > 10:
            import math
            log_cap = math.log10(max(user_cap, 1))
            cap_mask = pool_df['capacity_value'].apply(
                lambda v: abs(math.log10(max(v, 0.1)) - log_cap) <= 1.0 if pd.notna(v) and v > 0 else True)
            if cap_mask.sum() >= 10:
                pool_df = pool_df[cap_mask]

    total_estimate = 0.0
    total_low = 0.0
    total_high = 0.0
    matched_items = []

    for item in scope_items:
        item_type = item.get('type', '').lower()
        item_facility = item.get('facility_type', '').lower()
        search_term = item_facility if item_facility else item_type

        if not search_term:
            matched_items.append({'scope_item': item, 'n_chips': 0,
                                  'estimate_musd': 0, 'match_tier': 'no_term'})
            continue

        # --- Score all chips against the search term ---
        scores = pool_df.apply(
            lambda r: _match_chip_score(
                search_term,
                str(r.get('scope_name', '')),
                str(r.get('description', '')),
                str(r.get('scope_type', '')),
            ), axis=1)

        # Keep chips with score > 0
        hit_mask = scores > 0
        matched = pool_df[hit_mask].copy()
        matched_scores = scores[hit_mask]

        if matched.empty:
            matched_items.append({'scope_item': item, 'n_chips': 0,
                                  'estimate_musd': 0, 'match_tier': 'no_match'})
            continue

        # Add scores column
        matched = matched.assign(match_score=matched_scores.values)

        # --- Get costs and apply IQR outlier removal ---
        cost_col = 'direct_cost_kusd'
        costs_raw = matched[cost_col].dropna().values / 1000.0
        costs_raw = costs_raw[costs_raw > 0]

        if len(costs_raw) == 0:
            matched_items.append({'scope_item': item, 'n_chips': len(matched),
                                  'estimate_musd': 0, 'match_tier': 'no_cost'})
            continue

        # IQR filter
        costs = _iqr_filter(costs_raw)
        if len(costs) == 0:
            costs = costs_raw  # fallback if IQR removes everything

        n_outliers_removed = len(costs_raw) - len(costs)
        median_cost = float(np.median(costs))
        q25 = float(np.percentile(costs, 25)) if len(costs) >= 4 else median_cost * 0.7
        q75 = float(np.percentile(costs, 75)) if len(costs) >= 4 else median_cost * 1.3

        best_score = float(matched_scores.max())
        best_tier = ('T1' if best_score >= 0.95 else 'T2' if best_score >= 0.8
                     else 'T3' if best_score >= 0.7 else 'T4' if best_score >= 0.6 else 'T5')

        total_estimate += median_cost
        total_low += q25
        total_high += q75

        # Top 5 matches by score
        top5 = matched.nlargest(5, 'match_score')

        matched_items.append({
            'scope_item': item,
            'n_chips': len(costs),
            'n_outliers_removed': n_outliers_removed,
            'estimate_musd': round(median_cost, 2),
            'range_low': round(q25, 2),
            'range_high': round(q75, 2),
            'best_match_score': round(best_score, 2),
            'match_tier': best_tier,
            'chip_names': top5['scope_name'].tolist(),
            'chip_sources': top5['project_name'].tolist(),
        })

    if total_estimate == 0:
        return {'can_fire': False, 'no_fire_reason': 'no_matching_chips',
                'model_id': 'Composite'}

    return {
        'can_fire': True,
        'model_id': 'Composite',
        'estimate_musd': round(total_estimate, 1),
        'estimate_low_musd': round(total_low, 1),
        'estimate_high_musd': round(total_high, 1),
        'matched_items': matched_items,
        'n_items': len(scope_items),
        'archetype_filter': arch_filter_used,
    }
