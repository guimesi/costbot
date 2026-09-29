"""Benchmark: analogue matching, a faithful port of analogue_estimator.py v3.0
(reference, 2026-08-12) as called by cost_bot_api._run_benchmark.

What the reference does, and this module reproduces:
- Corpus = the analogue pool with nominal TEC and basis year. Categorical
  features: bf_gf (from the archetype name pattern), on/offshore, region
  (from the CP30 location), facility class (substring map on facility_type),
  process_domain and scope_type (LOW-confidence scope_type -> UNKNOWN).
  UNKNOWN dummy columns are dropped so shared ignorance never scores.
- Target vector from the scope: bf_gf from greenfield/brownfield, on/offshore
  from the archetype, region from location keywords (Guyana counts as North
  America), fac_type = the raw facility string, 2D taxonomy from
  process_domain + scope_type when given, else from the archetype map.
- Size: ONLY an explicit size_estimate_musd or a size bucket / hint
  (tiny ... mega). No capacity-to-size heuristic. With a size, the pool is
  restricted to +/-0.5 log decades (1.0 if fewer than 3 rows) and the score is
  0.6 cosine + 0.4 size proximity; without, cosine only.
- Refinery modifications with a capacity: capacity-family peers drive the
  score (adaptive 0.6/0.4, 0.5/0.5, 0.45/0.55) and very large targets drop the
  scope_type dimension.
- Threshold 0.3, at most 20 analogues; if fewer than 2, retry with
  scope_type UNKNOWN. Canaries and duplicates are always excluded.
- Analogue costs: nominal x CP30(GOM, target_year) / CP30(source location,
  basis year), source location from the pool's cp30_location (the reference
  maps country -> location; that table is empty in the package).
- Output: P50 of the adjusted costs; low/high = min/max (that is what the
  API forwards as the model range); confidence from count and spread.

Evaluation switches (scope keys, never set by the UI):
  benchmark_size_mode: 'api' (default) | 'capacity' (first build's heuristic)
                       | 'pool' (project's own pool TEC, LOOCV enrichment) | 'none'
  pool_exclude_forecast: drop tec_source/gate_stage 'forecast' rows
"""
import math
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

from costbot.data import DataStore

SIZE_TOLERANCE_LOG = 0.5
SIMILARITY_THRESHOLD = 0.3
MAX_ANALOGUES = 20
DEFAULT_ESCALATION_RATE = 0.045
_CP30_TARGET_LOCATION = 'Texas-BTN (GOM)'

# --- reference: structural exclusions and data overrides ---------------------
_CANARY_PLANVIEW_IDS = {'2093', '1084351', '1097721'}
_DUPLICATE_PLANVIEW_IDS = {'9000280'}
STRUCTURAL_EXCLUSIONS = _CANARY_PLANVIEW_IDS | _DUPLICATE_PLANVIEW_IDS
CORPUS_TEC_OVERRIDES = {'2088': 4162.0, '1099546': 6460.0, '2093': 5490.0,
                        '1084351': 7295.0, '1097721': 421.0, '9000439': 421.0}
CORPUS_METADATA_OVERRIDES = {
    '2088': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '1099546': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '2093': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '2087': {'on_off_norm': 'offshore', 'fac_type_norm': 'offshore'},
    '1084351': {'on_off_norm': 'onshore', 'fac_type_norm': 'chemicals'},
    '9000262': {'fac_type_norm': 'pipeline'},
    '1097706': {'fac_type_norm': 'pipeline'},
    '1097721': {'fac_type_norm': 'pipeline'},
    '9000439': {'on_off_norm': 'onshore', 'fac_type_norm': 'pipeline'},
}

# --- reference: categorical normalisers -------------------------------------
BF_GF_MAP = {'green': 'greenfield', 'grassroots': 'greenfield',
             'brown': 'brownfield', 'revamp': 'brownfield', 'combin': 'combination'}
ONSHORE_OFFSHORE_MAP = {'offshore': 'offshore', 'ref': 'refining', 'refin': 'refining',
                        'polymer': 'chemicals', 'olefin': 'chemicals', 'chem': 'chemicals',
                        'pipeline': 'pipeline', 'revamp': 'heavy_revamp',
                        'infrastructure': 'infrastructure', 'util': 'infrastructure', 'cogen': 'infrastructure'}
FACILITIES_TYPE_MAP = ONSHORE_OFFSHORE_MAP

# reference _ARCHETYPE_TO_2D (analogue_estimator.py v3.0)
ARCHETYPE_TO_2D = {
    'offshore_fpso': ('offshore', 'grassroots'), 'offshore_fpso_subsea': ('offshore', 'modification'),
    'offshore_gbs': ('offshore', 'grassroots'), 'offshore_platform': ('offshore', 'grassroots'),
    'offshore_jacket': ('offshore', 'grassroots'), 'offshore_subsea': ('offshore', 'modification'),
    'oil_sands': ('oil_sands', 'expansion'), 'sagd': ('oil_sands', 'expansion'),
    'ccs_gas_processing': ('ccs', 'grassroots'), 'gas_processing_ccs': ('ccs', 'grassroots'),
    'ccs': ('ccs', 'grassroots'), 'gas_processing': ('gas_processing', 'grassroots'),
    'lng': ('lng', 'grassroots'), 'lng_onshore': ('lng', 'grassroots'), 'lng_terminal': ('lng', 'expansion'),
    'lng_fling': ('lng', 'grassroots'), 'lng_train': ('lng', 'grassroots'), 'lng_expansion': ('lng', 'expansion'),
    'pipeline': ('pipeline', 'modification'), 'pipeline_complex': ('pipeline', 'modification'),
    'pipeline_mainline': ('pipeline', 'modification'), 'pipeline_replacement': ('pipeline', 'modification'),
    'pipeline_offshore': ('pipeline', 'modification'), 'pipeline_gathering': ('pipeline', 'modification'),
    'chemicals': ('chemicals', 'grassroots'), 'onshore_petchem': ('chemicals', 'grassroots'),
    'integrated_petchem': ('chemicals', 'grassroots'), 'petchem': ('chemicals', 'grassroots'),
    'integrated_complex_china': ('chemicals', 'grassroots'),
    'refinery_bf': ('refining', 'modification'), 'refinery': ('refining', 'modification'),
    'refinery_grassroots': ('refining', 'grassroots'), 'refinery_gf': ('refining', 'grassroots'),
    'process_plant_refinery_hc': ('refining', 'modification'), 'process_plant_refinery_ht': ('refining', 'modification'),
    'renewable_diesel': ('refining', 'modification'), 'cogen': ('refining', 'modification'),
    'onshore_conventional': ('upstream_conventional', 'expansion'), 'conventional': ('upstream_conventional', 'expansion'),
}

# UI scope-type vocabulary -> pool scope_type vocabulary
_UI_SCOPE_TO_POOL = {'greenfield': 'grassroots', 'grassroots': 'grassroots', 'expansion': 'expansion',
                     'modification': 'modification', 'debottleneck': 'debottleneck', 'replacement': 'replacement'}

# reference SIZE_BUCKETS (8 tiers)
SIZE_BUCKETS = {
    'tiny': {'representative_musd': 15.0, 'range_musd': (5.0, 30.0),
             'aliases': ['tiny', 'very_small', 'pilot', 'study', 'tie_in', 'instrument_upgrade']},
    'small': {'representative_musd': 50.0, 'range_musd': (30.0, 75.0),
              'aliases': ['small', 'minor', 'equipment_swap', 'heater', 'furnace', 'flare', 'valve']},
    'moderate': {'representative_musd': 125.0, 'range_musd': (75.0, 200.0),
                 'aliases': ['moderate', 'modest', 'compliance', 'environmental', 'reliability', 'targeted']},
    'medium': {'representative_musd': 325.0, 'range_musd': (200.0, 500.0),
               'aliases': ['medium', 'mid', 'revamp', 'debottleneck', 'brownfield_mod', 'pipeline_segment']},
    'substantial': {'representative_musd': 700.0, 'range_musd': (500.0, 1000.0),
                    'aliases': ['substantial', 'significant', 'new_unit', 'train', 'cracker', 'ccs']},
    'large': {'representative_musd': 1500.0, 'range_musd': (1000.0, 2500.0),
              'aliases': ['large', 'major', 'big', 'expansion', 'complex', 'integrated']},
    'very_large': {'representative_musd': 3500.0, 'range_musd': (2500.0, 5000.0),
                   'aliases': ['very_large', 'world_scale', 'mega_offshore', 'lng', 'fpso', 'field_development']},
    'mega': {'representative_musd': 7000.0, 'range_musd': (5000.0, 15000.0),
             'aliases': ['mega', 'megaproject', 'multi_billion', 'full_field', 'deepwater_hub', 'integrated_complex']},
}
SIZE_BUCKET_ORDER = list(SIZE_BUCKETS)


def bucket_for_musd(value: float) -> str:
    """Bucket name for a dollar value (reference back-mapping thresholds)."""
    v = float(value)
    for name, hi in (('tiny', 30), ('small', 75), ('moderate', 200), ('medium', 500),
                     ('substantial', 1000), ('large', 2500), ('very_large', 5000)):
        if v < hi:
            return name
    return 'mega'


def _normalize_size_text(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ''
    return str(value).strip().lower().replace('-', '_').replace(' ', '_')


def _bucket_from_hint(size_hint, target_features=None):
    hint = _normalize_size_text(size_hint)
    if not hint:
        return None
    for bucket, meta in SIZE_BUCKETS.items():
        if hint in meta['aliases']:
            return bucket
    tokens = set(t for t in hint.replace('/', '_').split('_') if t)
    scores = {bucket: 0 for bucket in SIZE_BUCKETS}
    for bucket, meta in SIZE_BUCKETS.items():
        for alias in meta['aliases']:
            alias_tokens = set(alias.split('_'))
            if alias in hint or (alias_tokens and alias_tokens.issubset(tokens)):
                scores[bucket] += 1
    tf = target_features or {}
    fac_type = _normalize_size_text(tf.get('fac_type'))
    bus_line = _normalize_size_text(tf.get('business_line'))
    on_off = _normalize_size_text(tf.get('onshore_offshore'))
    if any(x in hint for x in ('deepwater_hub', 'full_field', 'multi_billion', 'mega')):
        scores['mega'] += 3
    if any(x in hint for x in ('fpso', 'lng', 'world_scale', 'field_development')):
        scores['very_large'] += 3
    if any(x in hint for x in ('large', 'major', 'big', 'expansion', 'integrated')):
        scores['large'] += 2
    if any(x in hint for x in ('new_unit', 'train', 'cracker', 'ccs', 'significant')):
        scores['substantial'] += 2
    if any(x in hint for x in ('revamp', 'debottleneck', 'pipeline', 'mid')):
        scores['medium'] += 2
    if any(x in hint for x in ('compliance', 'reliability', 'environmental', 'modest', 'boiler', 'crusher')):
        scores['moderate'] += 2
    if any(x in hint for x in ('small', 'minor', 'swap', 'heater', 'furnace', 'flare')):
        scores['small'] += 2
    if any(x in hint for x in ('pilot', 'tie_in', 'study', 'instrument', 'very_small')):
        scores['tiny'] += 2
    if 'offshore' in fac_type or ('upstream' in bus_line and 'offshore' in on_off):
        scores['large'] += 1
        scores['very_large'] += 1
    if any(x in fac_type for x in ('pipeline', 'infrastructure')):
        scores['medium'] += 1
    if 'refining' in fac_type and any(x in hint for x in ('large', 'major', 'big')):
        scores['large'] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def resolve_size_signal(target_features: Dict) -> Optional[Dict]:
    """Explicit size_estimate_musd, else size_bucket, else a size hint phrase (reference)."""
    if not target_features:
        return None
    explicit = target_features.get('size_estimate_musd')
    if explicit is not None and not (isinstance(explicit, float) and np.isnan(explicit)):
        try:
            v = float(explicit)
            if v > 0:
                b = bucket_for_musd(v)
                return {'representative_musd': v, 'bucket': b, 'range_musd': SIZE_BUCKETS[b]['range_musd'],
                        'source': 'explicit_numeric'}
        except (TypeError, ValueError):
            pass
    bucket_hint = _normalize_size_text(target_features.get('size_bucket'))
    if bucket_hint:
        b = _bucket_from_hint(bucket_hint, target_features)
        if b:
            m = SIZE_BUCKETS[b]
            return {'representative_musd': m['representative_musd'], 'bucket': b,
                    'range_musd': m['range_musd'], 'source': 'size_bucket'}
    for key in ('size_hint', 'size_description', 'size_phrase'):
        hint = target_features.get(key)
        if hint:
            b = _bucket_from_hint(hint, target_features)
            if b:
                m = SIZE_BUCKETS[b]
                return {'representative_musd': m['representative_musd'], 'bucket': b,
                        'range_musd': m['range_musd'], 'source': key}
    return None


def normalize_categorical(value, mapping, default='UNKNOWN'):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    v = str(value).lower()
    for key, normalized in mapping.items():
        if key in v:
            return normalized
    return default


def normalize_region(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 'UNKNOWN'
    val = str(value)
    if val in ('Americas', 'North America', 'South America'):
        return 'north_america'
    if 'Europe' in val:
        return 'europe'
    if 'Asia' in val:
        return 'asia_pacific'
    if 'Middle East' in val:
        return 'middle_east'
    if 'Africa' in val:
        return 'africa'
    if 'Russia' in val or 'CIS' in val:
        return 'russia_cis'
    return val.lower().replace(' ', '_')


def region_from_cp30_location(loc) -> str:
    """The CASE expression of the reference load_corpus SQL."""
    s = str(loc or '')
    if s.startswith(('Texas', 'Louisiana', 'Canada', 'N. Alberta')):
        return 'North America'
    if s.startswith('UK'):
        return 'Europe'
    if s.startswith('India'):
        return 'Asia Pacific'
    return 'North America'


def bf_gf_from_archetype(arch) -> str:
    a = str(arch or '')
    if a.endswith('_bf') or 'replacement' in a:
        return 'Brownfield'
    if 'grassroots' in a or a.endswith('_gf'):
        return 'Greenfield'
    return 'Unknown'


def api_region_from_location(location) -> Optional[str]:
    """cost_bot_api._run_benchmark keyword mapping (Guyana/Brazil count as North America)."""
    loc = (location or '').lower()
    if any(k in loc for k in ('texas', 'louisiana', 'gulf', 'permian', 'baytown', 'beaumont', 'us', 'canada', 'alberta')):
        return 'North America'
    if any(k in loc for k in ('uk', 'netherlands', 'europe', 'belgium', 'germany', 'france')):
        return 'Europe'
    if any(k in loc for k in ('guyana', 'brazil', 'suriname')):
        return 'North America'
    if any(k in loc for k in ('mozambique', 'nigeria', 'angola')):
        return 'Africa'
    if any(k in loc for k in ('australia', 'png', 'singapore', 'malaysia', 'india', 'china', 'qatar')):
        return 'Asia Pacific'
    return None


def resolve_2d_taxonomy(target_features: Dict):
    pd_ = target_features.get('process_domain')
    st = target_features.get('scope_type')
    if pd_ and st and pd_ != 'UNKNOWN' and st != 'UNKNOWN':
        return (pd_, st)
    raw = target_features.get('archetype')
    if raw is not None:
        key = str(raw).strip().lower()
        if key in ARCHETYPE_TO_2D:
            return ARCHETYPE_TO_2D[key]
    return ('UNKNOWN', 'UNKNOWN')


# --- CP30 normalisation (reference cp30_normalize / _get_cp30_index) --------

def _cp30_index(cp30: pd.DataFrame, location: str, year: int) -> Optional[float]:
    loc = cp30[cp30['location'] == location]
    if loc.empty:
        return None
    ymin, ymax = int(loc['year'].min()), int(loc['year'].max())
    if ymin <= year <= ymax:
        row = loc[loc['year'] == year]
        if not row.empty:
            return float(row['combined_idx'].iloc[0])
        s = loc.sort_values('year')
        return float(np.interp(year, s['year'], s['combined_idx']))
    if year < ymin:
        early = loc[loc['year'] <= 2019].sort_values('year')
        idx_min = float(loc[loc['year'] == ymin]['combined_idx'].iloc[0])
        if len(early) >= 2:
            i0, i1 = float(early['combined_idx'].iloc[0]), float(early['combined_idx'].iloc[-1])
            yrs = int(early['year'].iloc[-1]) - int(early['year'].iloc[0])
            if yrs > 0 and i0 > 0:
                cagr = (i1 / i0) ** (1.0 / yrs) - 1
                return idx_min / ((1 + cagr) ** (ymin - year))
        return idx_min / ((1 + DEFAULT_ESCALATION_RATE) ** (ymin - year))
    return float(loc[loc['year'] == ymax]['combined_idx'].iloc[0])  # flat beyond the table


def _adjust_cost(raw: float, source_loc, fid_year, target_year: int, cp30: pd.DataFrame):
    """(adjusted_cost, method). Reference: raw x idx(GOM, target) / idx(source, fid)."""
    if fid_year is None or (isinstance(fid_year, float) and np.isnan(fid_year)):
        return raw, 'no_fid_year'
    fid_year = int(fid_year)
    if cp30 is None or cp30.empty or 'combined_idx' not in cp30.columns or not source_loc:
        return raw * (1 + DEFAULT_ESCALATION_RATE) ** (target_year - fid_year), 'flat_rate_fallback'
    si = _cp30_index(cp30, str(source_loc), fid_year)
    ti = _cp30_index(cp30, _CP30_TARGET_LOCATION, target_year)
    if not si or not ti:
        return raw * (1 + DEFAULT_ESCALATION_RATE) ** (target_year - fid_year), 'flat_rate_fallback'
    return raw * (ti / si), 'cp30'


# --- corpus preparation (cached on the DataStore) ----------------------------

def _prepare_corpus(pool: pd.DataFrame) -> Dict[str, Any]:
    from sklearn.preprocessing import StandardScaler
    df = pool.copy()
    df['planview_id'] = df['planview_id'].astype(str)
    # nominal TEC + basis year as in the reference SQL; fall back to the normalised column
    has_nominal = 'tec_musd_nominal' in df.columns and 'basis_year' in df.columns
    df['final_tec_musd'] = pd.to_numeric(df['tec_musd_nominal'] if has_nominal else df['tec_musd_normalized_2024'], errors='coerce')
    df['fid_year'] = pd.to_numeric(df['basis_year'], errors='coerce') if has_nominal else 2024
    df['source_loc'] = df['cp30_location'] if 'cp30_location' in df.columns else None
    df = df[df['final_tec_musd'].notna() & (df['final_tec_musd'] > 0)].copy()

    arch = df['archetype'].fillna('').astype(str)
    df['bf_gf_norm'] = arch.map(bf_gf_from_archetype).map(lambda x: normalize_categorical(x, BF_GF_MAP))
    df['on_off_norm'] = arch.map(lambda a: 'offshore' if a.lower().startswith('offshore') else 'onshore') \
                            .map(lambda x: normalize_categorical(x, ONSHORE_OFFSHORE_MAP))
    df['region_norm'] = df['source_loc'].map(region_from_cp30_location).map(normalize_region)
    fac_col = df['facility_type'] if 'facility_type' in df.columns else pd.Series([None] * len(df), index=df.index)
    df['fac_type_norm'] = fac_col.map(lambda x: normalize_categorical(x, FACILITIES_TYPE_MAP))
    df['log_tec'] = np.log10(df['final_tec_musd'].clip(lower=1))

    # validated data overrides (stale TEC, wrong metadata)
    for pid, tec in CORPUS_TEC_OVERRIDES.items():
        m = df['planview_id'] == pid
        if m.any():
            cur = float(df.loc[m, 'final_tec_musd'].iloc[0])
            if abs(cur / tec - 1) > 0.30:
                df.loc[m, 'final_tec_musd'] = tec
                df.loc[m, 'log_tec'] = np.log10(tec)
    for pid, ov in CORPUS_METADATA_OVERRIDES.items():
        m = df['planview_id'] == pid
        if m.any():
            for f, v in ov.items():
                df.loc[m, f] = v

    if 'process_domain' in df.columns:
        df['process_domain'] = df['process_domain'].fillna('UNKNOWN')
    else:
        df['process_domain'] = arch.map(lambda a: ARCHETYPE_TO_2D.get(a.lower(), ('UNKNOWN', 'UNKNOWN'))[0])
    if 'scope_type' in df.columns:
        if 'scope_type_confidence' in df.columns:
            low = df['scope_type_confidence'].fillna('').astype(str).str.upper() == 'LOW'
            df.loc[low, 'scope_type'] = 'UNKNOWN'
        df['scope_type'] = df['scope_type'].fillna('UNKNOWN')
    else:
        df['scope_type'] = arch.map(lambda a: ARCHETYPE_TO_2D.get(a.lower(), ('UNKNOWN', 'UNKNOWN'))[1])

    cat = ['bf_gf_norm', 'on_off_norm', 'region_norm', 'fac_type_norm', 'process_domain', 'scope_type']
    encoded = pd.get_dummies(df[cat], prefix=cat)
    encoded = encoded.drop(columns=[c for c in encoded.columns if c.endswith('_UNKNOWN')], errors='ignore')
    # gate_facilities / gate_execution enrichment is not in the package: constant zeros,
    # which StandardScaler neutralises, exactly as an empty join would in the reference.
    for c in ('has_pipeline', 'has_offshore_fac', 'has_epc', 'has_direct_hire', 'n_facilities'):
        encoded[c] = 0
    feature_columns = list(encoded.columns)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(encoded.values.astype(float))
    df = df.reset_index(drop=True)
    return {'corpus': df, 'feature_columns': feature_columns, 'scaler': scaler, 'scaled_matrix': scaled}


def _encode_target(target_dict: Dict, feature_columns: List[str], scaler) -> np.ndarray:
    vec = np.zeros(len(feature_columns))
    for i, col in enumerate(feature_columns):
        for key, val in target_dict.items():
            if col == f'{key}_{val}':
                vec[i] = 1.0
    return scaler.transform(vec.reshape(1, -1))


def _target_features_from_scope(scope: Dict) -> Dict:
    """cost_bot_api._run_benchmark target_features, with the UI's scope-type words
    translated to the pool vocabulary."""
    tf = {'archetype': scope.get('archetype', 'UNKNOWN')}
    if scope.get('process_domain'):
        tf['process_domain'] = scope['process_domain']
    st = (scope.get('scope_type') or '').lower()
    if st in _UI_SCOPE_TO_POOL:
        tf['scope_type'] = _UI_SCOPE_TO_POOL[st]
    bf = (scope.get('greenfield_brownfield') or '').lower()
    if 'green' in bf or 'grass' in bf:
        tf['bf_gf'] = 'greenfield'
    elif 'brown' in bf:
        tf['bf_gf'] = 'brownfield'
    elif st in ('expansion', 'modification', 'debottleneck', 'replacement'):
        tf['bf_gf'] = 'brownfield'
    tf['onshore_offshore'] = 'offshore' if str(scope.get('archetype', '')).startswith('offshore') else 'onshore'
    if scope.get('facility_type'):
        tf['fac_type'] = scope['facility_type']
    if scope.get('primary_capacity'):
        tf['primary_capacity'] = scope['primary_capacity']
        tf['capacity_unit'] = scope.get('capacity_unit')
    region = scope.get('region') or api_region_from_location(scope.get('location'))
    if region:
        tf['region'] = region
    for k in ('size_estimate_musd', 'size_bucket', 'size_hint', 'size_description', 'size_phrase'):
        if scope.get(k) is not None:
            tf[k] = scope[k]
    return tf


def run_benchmark(scope: Dict, data: DataStore) -> Dict:
    from sklearn.metrics.pairwise import cosine_similarity
    from costbot.constants import normalize_capacity, capacity_match_score

    pool = data.pool
    if pool.empty:
        return {'can_fire': False, 'no_fire_reason': 'pool_not_loaded', 'model_id': 'Benchmark'}
    prep = data.derived('benchmark_corpus', lambda: _prepare_corpus(pool))
    corpus, feature_columns, scaler, scaled_matrix = (prep['corpus'], prep['feature_columns'],
                                                      prep['scaler'], prep['scaled_matrix'])
    cp30 = data.cp30
    target_year = int(scope.get('benchmark_target_year', 2024))

    tf = _target_features_from_scope(scope)
    mode = scope.get('benchmark_size_mode', 'api')
    target_pid = str(scope.get('planview_id') or '')

    # --- size signal ---------------------------------------------------------
    size_source = None
    size_info = None if mode == 'none' else resolve_size_signal(tf)
    if size_info:
        size_source = size_info['source']
    size_est = size_info['representative_musd'] if size_info else None
    if size_est is None and mode == 'pool' and target_pid:
        own = corpus[corpus['planview_id'] == target_pid]
        if len(own) and 'tec_musd_normalized_2024' in own.columns and pd.notna(own['tec_musd_normalized_2024'].iloc[0]):
            size_est, size_source = float(own['tec_musd_normalized_2024'].iloc[0]), 'pool_tec'
    if size_est is None and mode == 'capacity':
        # first build's heuristic (not in the reference); kept for evaluation only
        cap, unit = scope.get('primary_capacity'), (scope.get('capacity_unit') or '').upper()
        pd_, st = resolve_2d_taxonomy(tf)
        if cap and float(cap) > 0 and st not in ('modification', 'debottleneck', 'replacement'):
            v = float(cap) / (1000.0 if unit in ('BPD', 'BPSD') else 1.0)
            factor = {'offshore': 40, 'pipeline': 5, 'lng': 1500, 'chemicals': 2, 'refining': 10,
                      'ccs': 5, 'oil_sands': 5, 'upstream_conventional': 2, 'upstream_unconventional': 2}.get(pd_, 2.0)
            size_est, size_source = v * factor, 'capacity_heuristic'

    # --- exclusions: structural, LOOCV self, optional forecast rows ----------
    excl = set(STRUCTURAL_EXCLUSIONS)
    if target_pid:
        excl.add(target_pid)
    id_mask = ~corpus['planview_id'].isin(excl).values
    pool_filter_note = None
    if scope.get('pool_exclude_forecast'):
        col = 'tec_source' if 'tec_source' in corpus.columns else ('gate_stage' if 'gate_stage' in corpus.columns else None)
        if col:
            fmask = ~corpus[col].astype(str).str.contains('forecast', case=False, na=False).values
            pool_filter_note = f'forecast rows excluded: {int((~fmask).sum())} of {len(corpus)}'
            id_mask &= fmask

    target_pd, target_st = resolve_2d_taxonomy(tf)
    target_cap = normalize_capacity(tf.get('primary_capacity'), tf.get('capacity_unit'))
    target_region = normalize_region(tf.get('region', 'UNKNOWN')) if tf.get('region') else 'UNKNOWN'

    def find(scope_type_for_vector: str):
        # size-gated scope_type for very large refinery modifications
        st_vec = scope_type_for_vector
        if (target_pd == 'refining' and target_st == 'modification' and target_cap is not None
                and 'primary_capacity' in corpus.columns and 'capacity_unit' in corpus.columns):
            same = corpus[(corpus['process_domain'].astype(str).str.lower() == 'refining')
                          & (corpus['scope_type'].astype(str).str.lower() == 'modification')]
            caps = [n[0] for n in (normalize_capacity(c, u) for c, u in zip(same['primary_capacity'], same['capacity_unit']))
                    if n is not None and n[2] == target_cap[2]]
            if len(caps) >= 10 and target_cap[0] > float(np.percentile(caps, 95)):
                st_vec = 'UNKNOWN'
        target_dict = {'bf_gf_norm': tf.get('bf_gf', 'UNKNOWN'), 'on_off_norm': tf.get('onshore_offshore', 'UNKNOWN'),
                       'region_norm': target_region, 'fac_type_norm': tf.get('fac_type', 'UNKNOWN'),
                       'process_domain': target_pd, 'scope_type': st_vec}
        t_scaled = _encode_target(target_dict, feature_columns, scaler)

        log_tec = corpus['log_tec'].values
        if size_est and size_est > 0:
            tlog = math.log10(max(size_est, 1))
            size_mask = np.abs(log_tec - tlog) <= SIZE_TOLERANCE_LOG
        else:
            tlog = None
            size_mask = np.ones(len(corpus), dtype=bool)
        valid = np.where(size_mask & id_mask)[0]
        if len(valid) < 3 and size_est:
            size_mask = np.abs(log_tec - tlog) <= 1.0
            valid = np.where(size_mask & id_mask)[0]
        if len(valid) == 0:
            return [], 'cosine'
        cos = cosine_similarity(t_scaled, scaled_matrix[valid]).flatten()

        method = 'cosine'
        if (target_cap is not None and target_pd == 'refining' and target_st == 'modification'
                and 'primary_capacity' in corpus.columns and 'capacity_unit' in corpus.columns):
            sub = corpus.iloc[valid]
            cap_sims = np.array([capacity_match_score(target_cap, c, u)
                                 for c, u in zip(sub['primary_capacity'].values, sub['capacity_unit'].values)])
            same_family_n = int((cap_sims > 0).sum())
            exact_n = int(((sub['scope_type'].astype(str).str.lower() == target_st)
                           & (sub['process_domain'].astype(str).str.lower() == target_pd)).sum())
            if same_family_n >= 3:
                if exact_n > 50:
                    comp = cap_sims > 0
                    if int(comp.sum()) >= 3:
                        valid, cos, cap_sims = valid[comp], cos[comp], cap_sims[comp]
                    combined, method = 0.45 * cos + 0.55 * cap_sims, 'cosine+capacity 0.45/0.55 gated'
                elif exact_n > 10:
                    combined, method = 0.50 * cos + 0.50 * cap_sims, 'cosine+capacity 0.5/0.5'
                else:
                    combined, method = 0.60 * cos + 0.40 * cap_sims, 'cosine+capacity 0.6/0.4'
            elif size_est and size_est > 0:
                combined, method = 0.6 * cos + 0.4 * (1.0 - np.abs(log_tec[valid] - tlog) / SIZE_TOLERANCE_LOG), 'cosine+size 0.6/0.4'
            else:
                combined = cos
        elif size_est and size_est > 0:
            combined, method = 0.6 * cos + 0.4 * (1.0 - np.abs(log_tec[valid] - tlog) / SIZE_TOLERANCE_LOG), 'cosine+size 0.6/0.4'
        else:
            combined = cos

        order = np.argsort(combined)[::-1]
        qualifying = [i for i in order if combined[i] >= SIMILARITY_THRESHOLD][:MAX_ANALOGUES]
        out = []
        for i in qualifying:
            row = corpus.iloc[valid[i]]
            adj, norm_method = _adjust_cost(float(row['final_tec_musd']), row.get('source_loc'),
                                            row.get('fid_year'), target_year, cp30)
            out.append({'planview_id': row['planview_id'], 'project_name': row.get('project_name', ''),
                        'archetype': row.get('archetype', ''), 'similarity_score': round(float(combined[i]), 3),
                        'raw_cost_musd': round(float(row['final_tec_musd']), 1), 'tec_musd_2024': round(float(adj), 1),
                        'adjusted_cost_musd': round(float(adj), 1), 'fid_year': (int(row['fid_year']) if pd.notna(row['fid_year']) else None),
                        'country': row.get('country', ''), 'region': row.get('region_norm', ''),
                        'process_domain': row.get('process_domain', ''), 'scope_type': row.get('scope_type', ''),
                        'norm_method': norm_method})
        return out, method

    analogues, method = find(target_st)
    n_tight = len(analogues)
    fallback = False
    if len(analogues) < 2:
        fallback = True
        analogues, method = find('UNKNOWN')
    if not analogues:
        return {'can_fire': False, 'no_fire_reason': 'no_analogues_found', 'model_id': 'Benchmark',
                'size_signal': {'source': size_source or 'none', 'size_musd': size_est, 'pool_filter': pool_filter_note}}

    costs = np.array([a['adjusted_cost_musd'] for a in analogues], dtype=float)
    n = len(costs)
    lo, hi = float(costs.min()), float(costs.max())
    spread = hi / lo if lo > 0 else float('inf')
    if n >= 4 and spread < 3.0:
        confidence = 'high'
    elif n >= 2 and spread < 5.0:
        confidence = 'medium'
    else:
        confidence = 'low'

    return {
        'can_fire': True, 'model_id': 'Benchmark',
        'estimate_musd': round(float(np.percentile(costs, 50)), 1),
        # the API forwards cost_range_low/high (min/max of the analogues) as the model range
        'estimate_low_musd': round(lo, 1), 'estimate_high_musd': round(hi, 1),
        'p20': round(float(np.percentile(costs, 20)), 1), 'p80': round(float(np.percentile(costs, 80)), 1),
        'n_analogues': n, 'n_qualifying': n, 'confidence': confidence, 'spread_ratio': round(spread, 2),
        'fallback_triggered': fallback, 'n_tight_matches': n_tight,
        'analogues': analogues[:10],
        'size_signal': {'source': size_source or 'none', 'size_musd': round(float(size_est), 1) if size_est else None,
                        'bucket': size_info['bucket'] if size_info else None,
                        'pool_rows': int(id_mask.sum()), 'pool_filter': pool_filter_note},
        'detail': {'process_domain': target_pd, 'scope_type': target_st, 'region': target_region,
                   'bf_gf': tf.get('bf_gf', 'UNKNOWN'), 'fac_type': tf.get('fac_type', 'UNKNOWN'),
                   'scoring': method, 'size_source': size_source or 'none', 'fallback_scope_type_relaxed': fallback,
                   'target_year': target_year, 'cost_basis': f'GOM {target_year} via CP30'},
    }
