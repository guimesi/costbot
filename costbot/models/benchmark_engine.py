"""Benchmark, engine variant: the first build's analogue model (commit dbe068d),
kept next to the faithful port of analogue_estimator.py v3.0.

What differs from the reference:
- a size band: the pool is filtered to +/-0.5 log10 decades around a size
  signal (explicit size, the user's size bucket, or a capacity heuristic per
  facility class), relaxed to +/-1.0 when fewer than 3 rows survive;
- a 0.5 / 0.5 cosine-size blend whenever a size signal exists;
- 6 one-hot features scaled with StandardScaler, threshold 0.3, top 20;
- P20 / P80 of the analogues as the model range (the reference forwards min / max).

The size signal never comes from the project's own pool row unless
`benchmark_size_mode == 'pool'` (evaluation only). The first build fell back
to it silently; the 2026-09-28 round-2 figures included that leak.
"""
from typing import Dict
import math
import numpy as np
import pandas as pd
from costbot.constants import resolve_country
from costbot.data import DataStore

_SIZE_TOL = 0.5
_THRESH = 0.3
_SCOPE_TO_BF = {'grassroots': 'greenfield', 'expansion': 'brownfield', 'modification': 'brownfield',
                'debottleneck': 'brownfield', 'replacement': 'brownfield'}
_COUNTRY_REGION = {
    'United States': 'north_america', 'Canada': 'north_america', 'Mexico': 'north_america',
    'United Kingdom': 'europe', 'France': 'europe', 'Netherlands': 'europe', 'the Netherlands': 'europe',
    'Belgium': 'europe', 'Germany': 'europe', 'Norway': 'europe', 'Italy': 'europe',
    'Singapore': 'asia_pacific', 'Malaysia': 'asia_pacific', 'China': 'asia_pacific', 'India': 'asia_pacific',
    'Australia': 'asia_pacific', 'Indonesia': 'asia_pacific', 'Thailand': 'asia_pacific', 'Japan': 'asia_pacific',
    'South Korea': 'asia_pacific', 'Papua New Guinea': 'asia_pacific', 'New Zealand': 'asia_pacific',
    'Qatar': 'middle_east', 'Saudi Arabia': 'middle_east', 'UAE': 'middle_east', 'United Arab Emirates': 'middle_east',
    'Oman': 'middle_east', 'Iraq': 'middle_east', 'Kuwait': 'middle_east',
    'Nigeria': 'africa', 'Angola': 'africa', 'Mozambique': 'africa', 'Equatorial Guinea': 'africa',
    'Algeria': 'africa', 'Chad': 'africa',
    'Kazakhstan': 'caspian', 'Russia': 'russia_cis',
    'Guyana': 'south_america', 'Trinidad and Tobago': 'south_america', 'Brazil': 'south_america',
    'Venezuela': 'south_america',
}
_ARCH_FACTYPE = {
    'offshore_fpso': 'offshore', 'offshore_platform': 'offshore',
    'pipeline_mainline': 'pipeline', 'pipeline_replacement': 'pipeline', 'pipeline_complex': 'pipeline',
    'pipeline_gathering': 'pipeline',
    'refinery_bf': 'refining', 'refinery_grassroots': 'refining', 'renewable_diesel': 'refining',
    'onshore_petchem': 'chemicals', 'integrated_petchem': 'chemicals',
    'lng_onshore': 'lng', 'lng_terminal': 'lng',
    'oil_sands': 'oil_sands', 'ccs': 'ccs', 'ccs_gas_processing': 'ccs',
    'gas_processing': 'gas_processing', 'onshore_conventional': 'upstream', 'onshore_unconventional': 'upstream',
    'midstream': 'infrastructure',
}
# capacity (KBPD / KTA / MTPA / km ...) to a rough TEC in $M, per facility class
_CAPACITY_TO_MUSD = {'offshore': 40, 'pipeline': 5, 'lng': 1500, 'chemicals': 2, 'refining': 10,
                     'ccs': 5, 'oil_sands': 5, 'upstream': 2}
_TEC_OVERRIDES = {'2088': 4162.0, '1099546': 6460.0, '2093': 5490.0, '1084351': 7295.0,
                  '1097721': 421.0, '9000439': 421.0}
_STRUCTURAL_EXCL = {'2093', '1084351', '1097721', '9000280'}
_META_OVERRIDES = {
    '2088': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '1099546': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '2093': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '2087': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '1084351': {'on_off_norm': 'onshore', 'fac_type_norm': 'chemicals'},
    '9000262': {'fac_type_norm': 'pipeline'}, '1097706': {'fac_type_norm': 'pipeline'},
    '1097721': {'fac_type_norm': 'pipeline'},
    '9000439': {'on_off_norm': 'onshore', 'fac_type_norm': 'pipeline'},
}
_CAT_FEATURES = ['bf_gf_norm', 'on_off_norm', 'region_norm', 'fac_type_norm', 'process_domain', 'scope_type']


def _prepare(pool_in: pd.DataFrame) -> Dict:
    """One-time encoding of the pool (cached on the DataStore)."""
    from sklearn.preprocessing import StandardScaler
    pool = pool_in.copy()
    pool['planview_id'] = pool['planview_id'].astype(str)
    for pid_o, tec_o in _TEC_OVERRIDES.items():
        mask = pool['planview_id'] == pid_o
        if mask.any():
            cur = pool.loc[mask, 'tec_musd_normalized_2024'].iloc[0]
            if pd.notna(cur) and cur > 0 and abs(cur / tec_o - 1) > 0.3:
                pool.loc[mask, 'tec_musd_normalized_2024'] = tec_o
    pool = pool[~pool['planview_id'].isin(_STRUCTURAL_EXCL)]
    pool = pool[pool['tec_musd_normalized_2024'].notna() & (pool['tec_musd_normalized_2024'] > 0)].copy()
    pool['bf_gf_norm'] = pool['scope_type'].map(_SCOPE_TO_BF).fillna('UNKNOWN')
    pool['on_off_norm'] = pool['archetype'].apply(lambda a: 'offshore' if 'offshore' in str(a).lower() else 'onshore')
    pool['region_norm'] = pool['country'].map(_COUNTRY_REGION).fillna('UNKNOWN') if 'country' in pool.columns else 'UNKNOWN'
    pool['fac_type_norm'] = pool['archetype'].map(_ARCH_FACTYPE).fillna('UNKNOWN')
    for pid_m, overrides in _META_OVERRIDES.items():
        mask = pool['planview_id'] == pid_m
        if mask.any():
            for field, val in overrides.items():
                pool.loc[mask, field] = val
    if 'scope_type_confidence' in pool.columns:
        low = pool['scope_type_confidence'].fillna('').astype(str).str.upper() == 'LOW'
        pool.loc[low, 'scope_type'] = 'UNKNOWN'
    pool['scope_type'] = pool['scope_type'].fillna('UNKNOWN')
    pool['process_domain'] = pool['process_domain'].fillna('UNKNOWN') if 'process_domain' in pool.columns else 'UNKNOWN'
    pool['log_tec'] = np.log10(pool['tec_musd_normalized_2024'].clip(lower=1))
    pool = pool.reset_index(drop=True)
    encoded = pd.get_dummies(pool[_CAT_FEATURES], prefix=_CAT_FEATURES)
    encoded = encoded.drop(columns=[c for c in encoded.columns if c.endswith('_UNKNOWN')], errors='ignore')
    scaler = StandardScaler()
    return {'pool': pool, 'feature_columns': list(encoded.columns),
            'scaled': scaler.fit_transform(encoded.values.astype(float)), 'scaler': scaler}


def _encode_target(target: Dict, feature_columns, scaler):
    vec = np.zeros(len(feature_columns))
    for i, col in enumerate(feature_columns):
        for key, val in target.items():
            if col == f"{key}_{val}":
                vec[i] = 1.0
    return scaler.transform(vec.reshape(1, -1))


def run_benchmark_engine(scope: Dict, data: DataStore) -> Dict:
    from sklearn.metrics.pairwise import cosine_similarity
    from costbot.models.benchmark import resolve_2d_taxonomy, resolve_size_signal, _target_features_from_scope

    if data.pool.empty:
        return {'can_fire': False, 'no_fire_reason': 'pool_not_loaded', 'model_id': 'Benchmark'}
    prep = data.derived('benchmark_engine_corpus', lambda: _prepare(data.pool))
    pool_all, feature_columns, scaled_all, scaler = prep['pool'], prep['feature_columns'], prep['scaled'], prep['scaler']

    archetype = str(scope.get('archetype') or '')
    tf = _target_features_from_scope(scope)
    target_pd, target_st = resolve_2d_taxonomy(tf)
    target_fac = _ARCH_FACTYPE.get(archetype, 'UNKNOWN')
    target = {'bf_gf_norm': _SCOPE_TO_BF.get(target_st, 'UNKNOWN'),
              'on_off_norm': 'offshore' if 'offshore' in archetype.lower() else 'onshore',
              'region_norm': _COUNTRY_REGION.get(resolve_country(scope), 'north_america'),
              'fac_type_norm': target_fac, 'process_domain': target_pd, 'scope_type': target_st}

    # --- pool rows: LOOCV self, evaluation exclusions, optional forecast filter ---
    target_pid = str(scope.get('planview_id') or '')
    excl = {str(x) for x in (scope.get('exclude_planview_ids') or [])}
    if target_pid:
        excl.add(target_pid)
    keep = ~pool_all['planview_id'].isin(excl).values if excl else np.ones(len(pool_all), dtype=bool)
    pool_filter_note = None
    if scope.get('pool_exclude_forecast'):
        col = 'tec_source' if 'tec_source' in pool_all.columns else ('gate_stage' if 'gate_stage' in pool_all.columns else None)
        if col:
            fmask = ~pool_all[col].astype(str).str.contains('forecast', case=False, na=False).values
            pool_filter_note = f'forecast rows excluded: {int((~fmask).sum())} of {len(pool_all)}'
            keep &= fmask
    if not keep.any():
        return {'can_fire': False, 'no_fire_reason': 'no_valid_pool', 'model_id': 'Benchmark'}
    pool = pool_all[keep].reset_index(drop=True)
    scaled = scaled_all[keep]

    # --- size signal: explicit or bucket, else capacity heuristic; pool TEC only on request ---
    mode = scope.get('benchmark_size_mode', 'api')
    user_size, size_source = None, None
    if mode != 'none':
        info = resolve_size_signal(tf)
        if info:
            user_size, size_source = float(info['representative_musd']), info['source']
    if user_size is None and mode == 'pool' and target_pid:
        own = pool_all[pool_all['planview_id'] == target_pid]
        if len(own):
            user_size, size_source = float(own['tec_musd_normalized_2024'].iloc[0]), 'pool_tec'
    if user_size is None and mode not in ('none', 'pool'):
        cap, unit = scope.get('primary_capacity'), (scope.get('capacity_unit') or '').upper()
        is_mod = target_st in ('modification', 'debottleneck', 'replacement')  # unit capacity does not size a mod
        try:
            cap = float(cap) if cap is not None else None
        except (TypeError, ValueError):
            cap = None
        if cap and cap > 0 and not is_mod:
            if unit in ('BPD', 'BPSD'):
                cap /= 1000.0
            user_size, size_source = cap * _CAPACITY_TO_MUSD.get(target_fac, 2.0), 'capacity_heuristic'

    if user_size and user_size > 0:
        tlog = math.log10(max(user_size, 1))
        size_mask = np.abs(pool['log_tec'].values - tlog) <= _SIZE_TOL
        if size_mask.sum() < 3:
            size_mask = np.abs(pool['log_tec'].values - tlog) <= 1.0
    else:
        size_mask = np.ones(len(pool), dtype=bool)
    valid_idx = np.where(size_mask)[0]
    if len(valid_idx) == 0:
        valid_idx = np.arange(len(pool))

    def _rank(target_dict):
        cos = cosine_similarity(_encode_target(target_dict, feature_columns, scaler), scaled[valid_idx]).flatten()
        if user_size and user_size > 0:
            dists = np.abs(pool.iloc[valid_idx]['log_tec'].values - tlog)
            combined = 0.5 * cos + 0.5 * (1.0 - np.clip(dists / _SIZE_TOL, 0, 1))
        else:
            combined = cos
        order = np.argsort(combined)[::-1]
        return combined, [i for i in order if combined[i] >= _THRESH][:20]

    combined, qualifying = _rank(target)
    fallback = False
    if len(qualifying) < 2:
        fallback = True
        combined, qualifying = _rank({**target, 'scope_type': '__UNUSED_RELAX__'})
    if not qualifying:
        return {'can_fire': False, 'no_fire_reason': f'no_analogue_for_{archetype}', 'model_id': 'Benchmark',
                'model_variant': 'engine_size_band',
                'size_signal': {'source': size_source or 'none', 'size_musd': user_size, 'pool_filter': pool_filter_note}}

    analogues = []
    for q in qualifying:
        row = pool.iloc[valid_idx[q]]
        analogues.append({'planview_id': str(row['planview_id']), 'project_name': row.get('project_name', ''),
                          'archetype': row.get('archetype', ''), 'tec_musd_2024': float(row['tec_musd_normalized_2024']),
                          'adjusted_cost_musd': float(row['tec_musd_normalized_2024']),
                          'process_domain': row.get('process_domain', ''), 'scope_type': row.get('scope_type', ''),
                          'country': row.get('country', ''), 'similarity_score': round(float(combined[q]), 3)})
    costs = np.array([a['tec_musd_2024'] for a in analogues])
    n = len(costs)
    spread = (costs.max() / costs.min()) if costs.min() > 0 else float('inf')
    confidence = 'high' if (n >= 4 and spread < 3.0) else ('medium' if (n >= 2 and spread < 5.0) else 'low')
    return {
        'can_fire': True, 'model_id': 'Benchmark', 'model_variant': 'engine_size_band',
        'estimate_musd': round(float(np.percentile(costs, 50)), 1),
        'estimate_low_musd': round(float(np.percentile(costs, 20)), 1),
        'estimate_high_musd': round(float(np.percentile(costs, 80)), 1),
        'p20': round(float(np.percentile(costs, 20)), 1), 'p80': round(float(np.percentile(costs, 80)), 1),
        'n_analogues': n, 'n_qualifying': n, 'confidence': confidence, 'spread_ratio': round(float(spread), 2),
        'fallback_triggered': fallback, 'analogues': analogues[:10],
        'size_signal': {'source': size_source or 'none', 'size_musd': round(float(user_size), 1) if user_size else None,
                        'band_rows': int(len(valid_idx)), 'pool_rows': int(len(pool)), 'pool_filter': pool_filter_note},
        'detail': {'variant': 'engine: size band +/-0.5 decade, 0.5/0.5 cosine-size blend',
                   'process_domain': target_pd, 'scope_type': target_st, 'region': target['region_norm'],
                   'facility_class': target_fac, 'size_source': size_source or 'none',
                   'size_musd': round(float(user_size), 1) if user_size else None,
                   'rows_in_size_band': int(len(valid_idx)), 'n_analogues': n, 'spread_ratio': round(float(spread), 2)},
    }
