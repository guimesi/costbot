#!/usr/bin/env python3
"""Reproduce the reference evaluation_harness.py scorecard with the engine's models.

    python scripts/evaluate_harness.py [--redact] [--csv out.csv] [--data-dir PATH]
                                       [--models Benchmark,Calculator_Onshore,...]

This is NOT the accuracy of the number a user sees in the app (that is
scripts/evaluate_truth.py, ensemble P50). It is the convention behind the
brief's "40/52 (77%)":

- every model runs on its own; no ensemble, no archetype exclusions, no clamp;
- a project counts as a hit when ANY model lands within +/-30% of ANY of its
  truths (a project can carry a FINAL truth and a screening-gate truth);
- CANARY and non_comparable projects are counted like the others;
- "screening band" is 0.70 <= estimate / truth <= 1.60.

Truth resolution, CP30 normalisation, model input mapping (scope_inputs_v2,
free-text secondary_params, EMMA location text) and the unit rules follow the
reference file. What cannot be reproduced is listed in the output: the
reference's Composite corrects with the truth value (`apply_oh=True`, an
"oracle ceiling" by its own comment) and its SURF runner scores four
hard-coded projects against a component truth. Neither is a model a user
could run, so neither is here.
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from costbot.constants import (ARCHETYPE_MODELS, ARCHETYPE_ALIASES_POOL, EQUIPMENT_TYPES_52,  # noqa: E402
                               ISBL_CORRELATIONS)
from costbot.data import DataStore  # noqa: E402
from costbot.models.benchmark import run_benchmark  # noqa: E402
from costbot.models.calculator_lng import run_calculator_lng  # noqa: E402
from costbot.models.calculator_offshore import run_calculator_offshore  # noqa: E402
from costbot.models.calculator_onshore import run_calculator_onshore, resolve_facility  # noqa: E402
from costbot.models.calculator_pipeline import run_calculator_pipeline  # noqa: E402
from costbot.models.composite import run_composite  # noqa: E402
from costbot.models.equipment_vector import run_equipment_vector  # noqa: E402
from costbot.models.unconventional import run_unconventional  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass

TARGET_YEAR = 2024
GATE_PRIORITY = {'FINAL': 5, 'G3': 4, 'G2G3': 3, 'G2': 2, 'G1': 1}
DEFAULT_MODELS = ['Benchmark', 'Calculator_Onshore', 'Calculator_Pipeline', 'Calculator_Offshore',
                  'Calculator_LNG', 'Unconventional', 'EquipmentVector', 'Composite']
POOL_TO_APP = {}
for _app, _pool in ARCHETYPE_ALIASES_POOL.items():
    POOL_TO_APP.setdefault(_pool, _app)

# reference CP30_LOCATION_MAP: location free text -> ref_cp30_combined_indices.location (first substring hit)
CP30_LOCATION_MAP = {
    'beaumont': 'Texas-BMT', 'baytown': 'Texas-BTN (GOM)', 'houston': 'Texas-BTN (GOM)',
    'us gulf coast': 'Louisiana', 'louisiana': 'Louisiana', 'texas': 'Texas-BTN (GOM)',
    'joliet': 'Illinois', 'illinois': 'Illinois', 'n. alberta': 'N. Alberta-Kearl', 'kearl': 'N. Alberta-Kearl',
    'canada-edm': 'Canada-Edm', 'edmonton': 'Canada-Edm', 'ontario': 'Canada-Ont', 'sarnia': 'Canada-Ont',
    'guyana': 'Louisiana', 'papua new guinea': 'Australia', 'png': 'Australia', 'mozambique': 'Mozambique',
    'singapore': 'Singapore', 'fawley': 'UK-England', 'uk': 'UK-England', 'china': 'China-IEPC',
    'australia': 'Australia', 'qatar': 'Qatar', 'nigeria': 'Nigeria', 'india': 'India', 'malaysia': 'Malaysia',
    'indonesia': 'Indonesia', 'angola': 'Angola', 'netherlands': 'Netherlands', 'belgium': 'Belgium',
    'germany': 'Germany', 'france': 'France-N', 'italy': 'Italy-N', 'kazakhstan': 'Kazakhstan', 'saudi': 'SaudiArabia',
}
# reference _PIPELINE_LOC_MAP (pipeline calculator location names)
PIPELINE_LOC_MAP = {
    'beaumont': 'Texas-BTN (GOM)', 'baytown': 'Texas-BTN (GOM)', 'houston': 'Texas-BTN (GOM)', 'texas': 'Texas-BTN (GOM)',
    'us gulf coast': 'Texas-BTN (GOM)', 'gulf coast': 'Texas-BTN (GOM)', 'louisiana': 'Louisiana', 'baton rouge': 'Louisiana',
    'alberta': 'Alberta', 'permian': 'Texas-West (Permian)', 'british columbia': 'British Columbia', 'bc': 'British Columbia',
    'appalachia': 'Appalachia', 'midwest': 'Midwest', 'northeast': 'Northeast US', 'california': 'California',
    'rocky mountain': 'Rocky Mountain', 'southeast': 'Southeast US', 'western canada': 'Western Canada',
}
# reference _UNIT_CONV in run_calculator_onshore (only these; any other mismatch = no fire)
UNIT_CONV = {('KBD', 'BPD'): 1000.0, ('KBPD', 'BPD'): 1000.0, ('KBD_NGL', 'BPD'): 1000.0,
             ('MTPA', 'MTPA_CO2'): 1.0, ('MTPA_CO2', 'MTPA'): 1.0}


def _nz(v, default=None):
    if v is None:
        return default
    if isinstance(v, float) and np.isnan(v):
        return default
    if isinstance(v, str) and not v.strip():
        return default
    return v


def _fnum(v):
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- truth resolution (reference §2)

def resolve_truth(truth: pd.DataFrame):
    """One entry per (planview_id, eval_type), as the reference does. Returns (entries, notes)."""
    notes = []
    df = truth.copy()
    if 'planview_id' not in df.columns:
        raise SystemExit(f"project_truth has no planview_id column: {list(df.columns)}")
    df['planview_id'] = df['planview_id'].astype(str)
    for c in ('gate_stage', 'test_type', 'quality_role', 'cost_type', 'archetype', 'project_name', 'process_domain', 'scope_type'):
        if c not in df.columns:
            df[c] = None
    roles = set(df['quality_role'].dropna().astype(str))
    if roles & {'EVALUATION', 'INTEGRITY_CANARY'}:
        before = len(df)
        df = df[df['quality_role'].isin(['EVALUATION', 'INTEGRITY_CANARY'])]
        notes.append(f"quality_role filter EVALUATION/INTEGRITY_CANARY: {before} -> {len(df)} rows")
    else:
        notes.append(f"quality_role has no EVALUATION rows ({sorted(roles)[:5]}); no filter applied")
    if (df['cost_type'].astype(str) == 'TEC').any():
        before = len(df)
        df = df[df['cost_type'].astype(str) == 'TEC']
        notes.append(f"cost_type == TEC: {before} -> {len(df)} rows")
    amount_col = next((c for c in ('amount_musd', 'tec_musd', 'truth_musd') if c in df.columns), None)
    if amount_col is None:
        raise SystemExit(f"no amount column in project_truth: {list(df.columns)}")

    entries, n_fallback = [], 0

    def entry(r, eval_type, gate):
        return {'planview_id': r['planview_id'], 'project_name': _nz(r.get('project_name'), r['planview_id']),
                'archetype': str(_nz(r.get('archetype'), '') or ''), 'quality_role': str(_nz(r.get('quality_role'), '') or ''),
                'eval_type': eval_type, 'truth_gate_stage': gate, 'truth_musd': float(r[amount_col]),
                'basis_year': _fnum(r.get('basis_year')),
                'truth_total_dev_musd': _fnum(r.get('truth_total_dev_musd')),
                'process_domain': _nz(r.get('process_domain')), 'scope_type': _nz(r.get('scope_type'))}

    for pid, grp in df.groupby('planview_id', sort=False):
        rows = [r for _, r in grp.iterrows() if _fnum(r[amount_col]) and float(r[amount_col]) > 0]
        if not rows:
            continue
        role = str(_nz(rows[0].get('quality_role'), '') or '')
        final_rows = [r for r in rows if str(r.get('gate_stage')) == 'FINAL']
        gate_rows = [r for r in rows if str(r.get('gate_stage')) != 'FINAL']
        made = 0
        if final_rows:
            fr = final_rows[0]
            non_comp = str(fr.get('test_type')) == 'non_comparable' or str(fr.get('scope_change_flag')).lower() == 'true'
            et = 'CANARY_check' if role == 'INTEGRITY_CANARY' else ('Type_B_non_comparable' if non_comp else 'Type_B_predictive')
            entries.append(entry(fr, et, 'FINAL')); made += 1
        sv = [r for r in gate_rows if str(r.get('test_type')) == 'screening_validation']
        if sv and role != 'INTEGRITY_CANARY':
            best = max(sv, key=lambda r: GATE_PRIORITY.get(str(r.get('gate_stage')), 0))
            entries.append(entry(best, 'Type_A_screening', str(best.get('gate_stage')))); made += 1
        if not final_rows and role == 'INTEGRITY_CANARY':
            best = max(rows, key=lambda r: GATE_PRIORITY.get(str(r.get('gate_stage')), 0))
            entries.append(entry(best, 'CANARY_check', str(best.get('gate_stage')))); made += 1
        if made == 0:
            # not covered by the reference rules (no FINAL row, no screening_validation row):
            # keep the highest gate row so the project is still tested, and say so
            best = max(rows, key=lambda r: GATE_PRIORITY.get(str(r.get('gate_stage')), 0))
            e = entry(best, 'Type_A_screening', str(best.get('gate_stage'))); e['fallback'] = True
            entries.append(e); n_fallback += 1
    notes.append(f"{len(entries)} truth entries for {len({e['planview_id'] for e in entries})} projects; "
                 f"{n_fallback} project(s) outside the reference rules kept via highest gate row")
    return entries, notes


# ---------------------------------------------------------------- CP30 normalisation (reference §3)

def cp30_factors(cp30: pd.DataFrame):
    out = {}
    if cp30.empty or not {'location', 'year', 'combined_idx'} <= set(cp30.columns):
        return out
    for _, r in cp30.dropna(subset=['combined_idx']).iterrows():
        try:
            out[(str(r['location']), int(r['year']))] = float(r['combined_idx'])
        except (TypeError, ValueError):
            pass
    return out


def cp30_location(loc_text):
    low = str(loc_text or '').lower()
    if not low:
        return 'Louisiana'
    for key, name in CP30_LOCATION_MAP.items():
        if key in low:
            return name
    return 'Louisiana'


def norm_factor(factors, location, from_year):
    if from_year is None or int(from_year) == TARGET_YEAR:
        return 1.0, 'none_needed'
    y = int(from_year)
    if (location, y) in factors and (location, TARGET_YEAR) in factors:
        return factors[(location, TARGET_YEAR)] / factors[(location, y)], 'CP30_to_2024'
    for fb in ('Louisiana', 'Texas-BTN (GOM)'):
        if (fb, y) in factors and (fb, TARGET_YEAR) in factors:
            return factors[(fb, TARGET_YEAR)] / factors[(fb, y)], f'CP30_to_2024_fallback_{fb}'
    return 1.0, 'raw'


def region_from_cp30(cp30_loc):
    s = str(cp30_loc or '')
    if not s:
        return 'North America'
    if any(k in s for k in ('Texas', 'Louisiana', 'Illinois', 'Alberta', 'Canada', 'Ont')):
        return 'North America'
    if any(k in s for k in ('UK', 'Netherlands', 'Belgium', 'Germany', 'France', 'Italy')):
        return 'Europe'
    if any(k in s for k in ('India', 'China', 'Singapore', 'Malaysia', 'Indonesia', 'Australia', 'Qatar')):
        return 'Asia Pacific'
    if any(k in s for k in ('Nigeria', 'Angola', 'Mozambique')):
        return 'Africa'
    if 'Kazakhstan' in s:
        return 'Russia'
    return 'North America'


# ---------------------------------------------------------------- per-project inputs

class Inputs:
    """scope_inputs_v2 row, pool row, location text and own vectors/chips per planview_id."""

    def __init__(self, data: DataStore):
        self.data = data
        si = data.scope_inputs
        self.scope = {}
        if not si.empty and 'planview_id' in si.columns:
            self.scope = {str(k): r for k, r in si.set_index(si['planview_id'].astype(str)).iterrows()}
        pool = data.pool
        self.pool = {}
        if not pool.empty and 'planview_id' in pool.columns:
            self.pool = {str(k): r for k, r in pool.set_index(pool['planview_id'].astype(str)).iterrows()}
        ev = data.equipment_vectors
        self.vectors = {}
        if not ev.empty:
            idc = 'project_id' if 'project_id' in ev.columns else ('planview_id' if 'planview_id' in ev.columns else None)
            if idc:
                self.vectors = {str(k): r for k, r in ev.set_index(ev[idc].astype(str)).iterrows()}
        ch = data.semantic_chips
        self.chips = {}
        if not ch.empty and 'planview_id' in ch.columns:
            for k, g in ch.groupby(ch['planview_id'].astype(str)):
                self.chips[str(k)] = g
        self.scope_cap_col = next((c for c in ('primary_capacity', 'capacity_value', 'capacity') if c in si.columns), None) if not si.empty else None
        self.scope_loc_col = next((c for c in ('location_free_text', 'location') if c in si.columns), None) if not si.empty else None

    def location_text(self, pid):
        s = self.scope.get(pid)
        if s is not None and self.scope_loc_col and _nz(s.get(self.scope_loc_col)):
            return str(s[self.scope_loc_col])
        p = self.pool.get(pid)
        if p is not None:
            for c in ('site_location', 'cp30_location', 'country'):
                if _nz(p.get(c)):
                    return str(p[c])
        return ''

    def scope_row(self, pid):
        s = self.scope.get(pid)
        if s is None:
            return None
        return {'facility_type': _nz(s.get('facility_type')),
                'primary_capacity': _fnum(s.get(self.scope_cap_col)) if self.scope_cap_col else None,
                'capacity_unit': str(_nz(s.get('capacity_unit'), '') or ''),
                'secondary_params': _nz(s.get('secondary_params'), '') or ''}


# ---------------------------------------------------------------- model runners (reference input mapping)

def _no(reason, **extra):
    return {'can_fire': False, 'no_fire_reason': reason, **extra}


def m_benchmark(t, inp, data):
    pid = t['planview_id']
    pool = inp.pool.get(pid)
    scope_r = inp.scope_row(pid)
    pd_ = _nz(t.get('process_domain')) or (pool is not None and _nz(pool.get('process_domain'))) or None
    st = _nz(t.get('scope_type')) or (pool is not None and _nz(pool.get('scope_type'))) or None
    fac = (pool is not None and _nz(pool.get('facility_type'))) or (scope_r and scope_r['facility_type']) or None
    cap, unit = None, None
    if scope_r and scope_r['primary_capacity']:
        cap, unit = scope_r['primary_capacity'], scope_r['capacity_unit']
    elif pool is not None and _fnum(pool.get('primary_capacity')):
        cap, unit = _fnum(pool.get('primary_capacity')), str(_nz(pool.get('capacity_unit'), '') or '')
    loc_text = inp.location_text(pid)
    cp30_loc = CP30_LOCATION_MAP.get(loc_text.lower().strip()) if loc_text else None
    if not cp30_loc and pool is not None:
        cp30_loc = _nz(pool.get('cp30_location'))
    stl = str(st or '').lower()
    scope = {'planview_id': pid, 'archetype': t['archetype'], 'process_domain': pd_, 'scope_type': stl or None,
             'greenfield_brownfield': 'greenfield' if stl == 'grassroots' else
             ('brownfield' if stl in ('expansion', 'modification', 'debottleneck', 'replacement') else None),
             'facility_type': fac, 'primary_capacity': cap, 'capacity_unit': unit,
             'region': region_from_cp30(cp30_loc), 'location': loc_text, 'basis_year': TARGET_YEAR,
             'benchmark_size_mode': 'api', 'pool_exclude_forecast': False}
    r = run_benchmark(scope, data)
    r['notes'] = f"features: domain={pd_}, scope={stl or '-'}, fac={fac or '-'}, cap={cap or '-'} {unit or ''}, region={scope['region']}"
    return r


def m_calculator_onshore(t, inp, data):
    arch = str(t['archetype'] or '').lower()
    if arch and any(k in arch for k in ('offshore', 'pipeline', 'lng', 'subsea', 'deepwater')):
        return _no(f'onshore_only_archetype_{arch}')
    s = inp.scope_row(t['planview_id'])
    if s is None:
        return _no('missing_scope_inputs')
    facility = s['facility_type'] or 'process_plant_generic'
    cap, unit, sec = s['primary_capacity'], s['capacity_unit'], str(s['secondary_params'])
    if cap is None:
        return _no('missing_primary_capacity')
    location = inp.location_text(t['planview_id']) or 'US Gulf Coast'
    # scope type exactly as the reference harness derives it
    sec_l, ft_l = sec.lower(), str(facility).lower()
    scope_type = 'GF'
    if any(k in sec_l for k in ('brownfield', 'revamp', 'expansion', 'existing')):
        scope_type = 'BF-expansion'
    if any(k in ft_l for k in ('debottleneck', 'modification', 'mod_')):
        scope_type = 'BF-unit-mod'
    if '_bf' in arch:
        scope_type = 'BF-expansion'
    gf = any(k in sec_l for k in ('grassroots', 'greenfield', 'new-build'))
    if gf and not re.search(r'\b(no|not|non)[- ]?(grassroots|greenfield|new.build)', sec_l):
        scope_type = 'GF'
    # unit normalisation exactly as the reference harness: a few conversions, else no fire
    kind, key, _ = resolve_facility(facility)
    expected = ISBL_CORRELATIONS[key][3] if kind == 'tuple' else None
    unit_u = unit.upper().strip()
    note = ''
    conv = UNIT_CONV.get((unit_u, expected))
    if conv is not None and conv != 1.0:
        cap, unit = cap * conv, expected
        note = f'UNIT_NORMALIZED {unit_u}->{expected} x{int(conv)}. '
    elif expected and unit_u != expected.upper() and conv is None:
        return _no(f'UNIT_MISMATCH_UNCONVERTIBLE: {unit}->{expected} for {facility}')
    r = run_calculator_onshore({'facility_type': facility, 'primary_capacity': cap, 'capacity_unit': unit,
                                'location': location, 'calculator_scope_type': scope_type}, data)
    if r.get('can_fire'):
        d = r['detail']
        r['notes'] = note + f"facility={facility}, cap={cap} {unit}, loc={location}, scope={scope_type}, corr={d['correlation_used']}, emma={d['emma_factor']}"
    return r


def m_calculator_pipeline(t, inp, data):
    arch = str(t['archetype'] or '').lower()
    if arch and 'pipeline' not in arch:
        return _no(f'pipeline_only_archetype_{arch}')
    s = inp.scope_row(t['planview_id'])
    if s is None:
        return _no('missing_scope_inputs')
    sec = str(s['secondary_params']); sl = sec.lower()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:in(?:ch(?:es)?)?|")', sec, re.IGNORECASE)
    if not m:
        return _no('missing_od_inches_in_secondary_params')
    od = float(m.group(1))
    cap, cu = s['primary_capacity'], s['capacity_unit'].lower().strip()
    if cap is None:
        return _no('missing_length_primary_capacity')
    if 'mile' in cu or cu == 'mi':
        length_km = cap * 1.60934
    elif 'km' in cu:
        length_km = cap
    elif 'ft' in cu or 'feet' in cu:
        length_km = cap * 0.0003048
    else:
        length_km = cap * 1.60934
    service = 'oil'
    if any(k in sl for k in ('gas', 'mmscf', 'natural gas', 'compressor')):
        service = 'gas'
    elif any(k in sl for k in ('ethane', 'ngl', 'propane', 'butane')):
        service = 'ngl'
    grades = re.findall(r'X(\d+)', sec, re.IGNORECASE)
    grade = f'X{max(int(g) for g in grades)}' if grades else 'X65'
    pipe_type = 'Stainless' if 'stainless' in sl else ('CRA' if ('cra' in sl or 'alloy' in sl) else 'Carbon')
    pct = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:HDD|bore|drill)', sec, re.IGNORECASE)
    pct_hdd = float(pct.group(1)) / 100.0 if pct else (0.10 if ('hdd' in sl or 'bore' in sl) else 0.0)
    congestion = 'low'
    if 'severe' in sl or 'urban' in sl:
        congestion = 'severe'
    elif 'high congestion' in sl or 'congested' in sl:
        congestion = 'high'
    elif 'medium' in sl:
        congestion = 'medium'
    location = 'Texas-BTN (GOM)'
    lt = inp.location_text(t['planview_id']).lower()
    for k, v in PIPELINE_LOC_MAP.items():
        if k in lt:
            location = v
            break
    r = run_calculator_pipeline({'archetype': t['archetype'], 'length_km': length_km, 'location': location,
                                 'secondary_params': {'od_inches': od, 'grade': grade, 'service': service,
                                                      'congestion': congestion, 'pipe_type': pipe_type, 'pct_hdd': pct_hdd}}, data)
    if r.get('can_fire'):
        r['notes'] = f"od={od}in, length={length_km:.1f}km, service={service}, grade={grade}, loc={location}, pct_hdd={pct_hdd} (pipe_type/pct_hdd not used by the engine yet)"
    return r


def m_calculator_offshore(t, inp, data):
    arch = str(t['archetype'] or '').lower()
    if 'offshore' not in arch:
        return _no(f'offshore_only_archetype_{arch}')
    s = inp.scope_row(t['planview_id'])
    if s is None:
        return _no('missing_scope_inputs')
    sec = str(s['secondary_params'])
    try:
        params = json.loads(sec) if sec.startswith('{') else {}
    except ValueError:
        params = {}
    if not params.get('topsides_weight_te'):
        return _no('missing_topsides_weight_te_in_secondary_params')
    r = run_calculator_offshore({'archetype': t['archetype'], 'secondary_params': params,
                                 'primary_capacity': s['primary_capacity'], 'location': inp.location_text(t['planview_id'])}, data)
    r['score_against'] = 'total_dev'
    if r.get('can_fire'):
        r['notes'] = f"topsides={params.get('topsides_weight_te')}te, scored against truth_total_dev_musd when present"
    return r


def m_calculator_lng(t, inp, data):
    arch = str(t['archetype'] or '').lower()
    if 'lng' not in arch:
        return _no(f'lng_only_archetype_{arch}')
    s = inp.scope_row(t['planview_id'])
    if s is None:
        return _no('missing_scope_inputs')
    mtpa = s['primary_capacity']
    if mtpa is None:
        return _no('missing_capacity_mtpa')
    m = re.search(r'(\d+)\s*train', str(s['secondary_params']), re.IGNORECASE)
    trains = int(m.group(1)) if m else max(1, round(mtpa / 5))
    location = inp.location_text(t['planview_id']) or 'png'
    r = run_calculator_lng({'lng_capacity_mtpa': mtpa, 'num_trains': trains, 'location': location}, data)
    if r.get('can_fire'):
        r['notes'] = f"capacity={mtpa}MTPA, trains={trains}, loc={location}"
    return r


def m_unconventional(t, inp, data):
    if t['archetype'] != 'onshore_unconventional':
        return _no('not_unconventional')
    pool = inp.pool.get(t['planview_id'])
    if pool is None:
        return _no('not_in_pool')
    r = run_unconventional({'facility_type': _nz(pool.get('facility_type')), 'primary_capacity': _fnum(pool.get('primary_capacity')),
                            'capacity_unit': str(_nz(pool.get('capacity_unit'), '') or ''),
                            'exclude_planview_ids': [t['planview_id']]}, data)
    if r.get('can_fire'):
        r['notes'] = f"facility_type={r.get('facility_type')}, n_peers={r.get('n_peers')}, {r.get('model_variant')}"
    return r


def _own_equipment_items(row):
    """Equipment counts from a ref_equipment_vectors row. The real package stores
    `equipment_vector_json` (dict or 52-list) plus the L2 `vector_norm`; the mock stores
    `vector_raw`. Returns ({type: count}, note) or (None, reason)."""
    for col in ('equipment_vector_json', 'vector_raw'):
        raw = _nz(row.get(col))
        if raw is None:
            continue
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        if isinstance(obj, dict):
            items = {}
            for k, v in obj.items():
                c = _fnum(v)
                if c and c > 0:
                    items[str(k)] = int(round(c))
            if items:
                return items, col
        elif isinstance(obj, list) and len(obj) == len(EQUIPMENT_TYPES_52):
            items = {EQUIPMENT_TYPES_52[i]: int(round(float(v))) for i, v in enumerate(obj) if _fnum(v) and float(v) > 0}
            if items:
                return items, col
    raw = _nz(row.get('vector_norm'))
    try:
        vec = json.loads(raw) if isinstance(raw, str) else None
    except (TypeError, ValueError):
        vec = None
    if isinstance(vec, list) and len(vec) == len(EQUIPMENT_TYPES_52):
        total = _fnum(row.get('total_items')) or 100.0
        ssum = sum(float(v) for v in vec if _fnum(v)) or 1.0
        items = {EQUIPMENT_TYPES_52[i]: max(1, int(round(float(v) / ssum * total))) for i, v in enumerate(vec) if _fnum(v) and float(v) > 0}
        if items:
            return items, 'vector_norm (counts rescaled to total_items)'
    return None, 'unparseable_vector (no equipment_vector_json / vector_raw / vector_norm)'


def m_equipment_vector(t, inp, data):
    row = inp.vectors.get(t['planview_id'])
    if row is None:
        return _no('no_equipment_vector_for_project')
    items, note = _own_equipment_items(row)
    if not items:
        return _no(note)
    r = run_equipment_vector({'equipment_list': items, 'archetype': t['archetype'], 'exclude_planview_ids': [t['planview_id']]}, data)
    if r.get('can_fire'):
        r['notes'] = f"own vector from {note}: {sum(items.values())} items, {len(items)} types, self excluded"
    return r


def m_composite(t, inp, data):
    chips = inp.chips.get(t['planview_id'])
    if chips is None or chips.empty:
        return _no('no_scope_chips_for_project')
    # real package: category / cost_category_l1 per cost row (chip_role, is_leaf); mock: semantic_label
    col = next((c for c in ('semantic_label', 'category', 'cost_category_l1', 'scope_name') if c in chips.columns), None)
    if col is None:
        return _no(f'no_chip_label_column in {list(chips.columns)[:6]}')
    if 'is_leaf' in chips.columns and chips['is_leaf'].astype(str).str.lower().eq('true').any():
        chips = chips[chips['is_leaf'].astype(str).str.lower() == 'true']
    items = [{'type': str(v).replace('_', ' ')} for v in chips[col].dropna().unique() if str(v).strip()]
    if not items:
        return _no('no_leaf_chip_labels')
    pool = inp.pool.get(t['planview_id'])
    scope_r = inp.scope_row(t['planview_id'])
    cap = (scope_r and scope_r['primary_capacity']) or (pool is not None and _fnum(pool.get('primary_capacity'))) or None
    r = run_composite({'scope_items': items, 'archetype': t['archetype'], 'primary_capacity': cap,
                       'exclude_planview_ids': [t['planview_id']]}, data)
    if r.get('can_fire'):
        r['notes'] = f"{len(items)} own chip labels matched against other projects' chips; no OH correction (the reference's uses the truth)"
    return r


SHORT = {'Benchmark': 'Bench', 'Calculator_Onshore': 'CalcOn', 'Calculator_Pipeline': 'CalcPipe',
         'Calculator_Offshore': 'CalcOff', 'Calculator_LNG': 'CalcLNG', 'Unconventional': 'Uncon',
         'EquipmentVector': 'EqVec', 'Composite': 'Comp'}
RUNNERS = {'Benchmark': m_benchmark, 'Calculator_Onshore': m_calculator_onshore, 'Calculator_Pipeline': m_calculator_pipeline,
           'Calculator_Offshore': m_calculator_offshore, 'Calculator_LNG': m_calculator_lng, 'Unconventional': m_unconventional,
           'EquipmentVector': m_equipment_vector, 'Composite': m_composite}


# ---------------------------------------------------------------- scoring (reference §1) and scorecard

def scores(est, truth):
    if not est or not truth:
        return None, None, None
    ratio = est / truth
    return ratio, abs(ratio - 1) <= 0.30, 0.70 <= ratio <= 1.60


def scorecard(rows, label):
    pids = {r['planview_id'] for r in rows}
    hit30 = {r['planview_id'] for r in rows if r['can_fire'] and r['within_30pct']}
    band = {r['planview_id'] for r in rows if r['can_fire'] and r['within_band']}
    fired = {r['planview_id'] for r in rows if r['can_fire']}
    per_arch = {}
    for r in rows:
        a = per_arch.setdefault(r['archetype'] or 'UNKNOWN', {'all': set(), 'p30': set(), 'band': set()})
        a['all'].add(r['planview_id'])
        if r['can_fire'] and r['within_30pct']:
            a['p30'].add(r['planview_id'])
        if r['can_fire'] and r['within_band']:
            a['band'].add(r['planview_id'])
    best = {}
    for r in rows:
        if r['can_fire'] and r['ratio'] is not None:
            if r['planview_id'] not in best or abs(r['ratio'] - 1) < abs(best[r['planview_id']][0] - 1):
                best[r['planview_id']] = (r['ratio'], r)
    zero = sorted(pids - band)
    return {'label': label, 'n': len(pids), 'fired': len(fired), 'n30': len(hit30), 'band': len(band),
            'per_arch': per_arch, 'zero_viable': [(p, best.get(p)) for p in zero]}


def print_scorecard(sc, names):
    n = sc['n'] or 1
    print(f"\n=== SCORECARD: {sc['label']} ===")
    print(f"  projects tested      {sc['n']}")
    print(f"  any model fired      {sc['fired']}/{sc['n']}")
    print(f"  any model +/-30%     {sc['n30']}/{sc['n']} ({sc['n30'] / n * 100:.0f}%)")
    print(f"  any model in band    {sc['band']}/{sc['n']} ({sc['band'] / n * 100:.0f}%)   (0.70 <= est/truth <= 1.60)")
    print(f"  zero-viable          {len(sc['zero_viable'])}")
    print(f"  {'archetype':26s} {'n':>3s} {'+/-30%':>8s} {'band':>6s}")
    for a in sorted(sc['per_arch']):
        v = sc['per_arch'][a]
        print(f"  {a:26s} {len(v['all']):>3d} {len(v['p30']):>4d}     {len(v['band']):>4d}")
    if sc['zero_viable']:
        print("  zero-viable (no model in band):")
        for p, b in sc['zero_viable']:
            print(f"    {names.get(p, p):32s} best ratio {b[0]:.2f} ({b[1]['model']})" if b else f"    {names.get(p, p):32s} NO_FIRE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data-dir', default=None)
    ap.add_argument('--csv', default=None)
    ap.add_argument('--redact', action='store_true', help='project names -> archetype-NN')
    ap.add_argument('--models', default=','.join(DEFAULT_MODELS))
    args = ap.parse_args()
    models = [m.strip() for m in args.models.split(',') if m.strip()]
    unknown = [m for m in models if m not in RUNNERS]
    if unknown:
        print(f"unknown model(s) {unknown}; choose from {list(RUNNERS)}"); sys.exit(2)

    data = DataStore(args.data_dir) if args.data_dir else DataStore()
    if data.truth.empty:
        print('project_truth.csv not found or empty'); sys.exit(2)
    entries, notes = resolve_truth(data.truth)
    print('Truth resolution (reference rules):')
    for n in notes:
        print('  ' + n)
    et_counts = {}
    for e in entries:
        et_counts[e['eval_type']] = et_counts.get(e['eval_type'], 0) + 1
    print('  eval types: ' + ', '.join(f"{k}={v}" for k, v in sorted(et_counts.items())))
    inp = Inputs(data)
    factors = cp30_factors(data.cp30)
    print(f"CP30 factors: {len(factors)} (location, year) pairs; scope_inputs rows: {len(inp.scope)}; "
          f"location column: {inp.scope_loc_col or 'none in scope_inputs (pool site/cp30 location used)'}; "
          f"equipment vectors: {len(inp.vectors)}; projects with chips: {len(inp.chips)}")

    names, counter = {}, {}
    rows = []
    for e in entries:
        pid = e['planview_id']
        arch = e['archetype']
        if arch not in ARCHETYPE_MODELS:
            arch = POOL_TO_APP.get(arch, arch)
        e['archetype'] = arch
        if pid not in names:
            if args.redact:
                counter[arch] = counter.get(arch, 0) + 1
                names[pid] = f"{arch}-{counter[arch]:02d}"
            else:
                names[pid] = str(e['project_name'])
        loc = cp30_location(inp.location_text(pid))
        nf, method = norm_factor(factors, loc, e['basis_year'])
        truth24 = e['truth_musd'] * nf
        tdev24 = e['truth_total_dev_musd'] * nf if e['truth_total_dev_musd'] else None
        for model in models:
            try:
                r = RUNNERS[model](e, inp, data)
            except Exception as ex:  # noqa: BLE001
                r = _no(f'error: {type(ex).__name__}: {str(ex)[:120]}')
            est = r.get('estimate_musd') if r.get('can_fire') else None
            truth_for = tdev24 if (r.get('score_against') == 'total_dev' and tdev24) else truth24
            ratio, w30, band = scores(est, truth_for)
            rows.append({'planview_id': pid, 'project': names[pid], 'archetype': arch, 'quality_role': e['quality_role'],
                         'eval_type': e['eval_type'], 'gate': e['truth_gate_stage'], 'basis_year': e['basis_year'],
                         'cp30_location': loc, 'normalization': method, 'truth_2024_musd': round(truth24, 1),
                         'model': model, 'can_fire': bool(r.get('can_fire')), 'estimate_musd': est,
                         'ratio': round(ratio, 3) if ratio else None, 'within_30pct': bool(w30) if w30 is not None else None,
                         'within_band': bool(band) if band is not None else None,
                         'no_fire_reason': None if r.get('can_fire') else str(r.get('no_fire_reason', ''))[:160],
                         'notes': str(r.get('notes', ''))[:200]})

    df = pd.DataFrame(rows)
    print(f"\nTruth normalisation: {df.drop_duplicates(['planview_id', 'eval_type'])['normalization'].value_counts().to_dict()}")
    print(f"\n{'model':20s} {'fired':>9s} {'+/-30% (of fired)':>18s} {'band':>6s}   top no-fire reasons")
    for model in models:
        g = df[df.model == model]
        fired = g[g.can_fire]
        n_pids = g.planview_id.nunique()
        f_pids = fired.planview_id.nunique()
        h30 = fired[fired.within_30pct == True].planview_id.nunique()  # noqa: E712
        hb = fired[fired.within_band == True].planview_id.nunique()  # noqa: E712
        reasons = g[~g.can_fire].no_fire_reason.fillna('').str.split(':').str[0].value_counts().head(3).to_dict()
        print(f"{model:20s} {f_pids:>4d}/{n_pids:<4d} {h30:>8d} ({(h30 / f_pids * 100) if f_pids else 0:3.0f}%) {hb:>10d}   {reasons}")

    print_scorecard(scorecard(rows, 'all projects, any model, any truth (reference convention)'), names)
    ev = [r for r in rows if r['quality_role'] == 'EVALUATION']
    if ev and len({r['planview_id'] for r in ev}) != len({r['planview_id'] for r in rows}):
        print_scorecard(scorecard(ev, 'quality_role = EVALUATION only'), names)
    for et in ('Type_B_predictive', 'Type_A_screening'):
        sub = [r for r in rows if r['eval_type'] == et]
        if sub:
            sc = scorecard(sub, et)
            print(f"\n{et}: {sc['n']} projects, any model +/-30% {sc['n30']}/{sc['n']}, band {sc['band']}/{sc['n']}")

    print("\nPer project (ratio = estimate / truth 2024; '-' = did not fire):")
    mods = models
    print(f"  {'project':30s} {'archetype':22s} {'eval':18s} {'truth':>8s} " + ' '.join(f"{SHORT.get(m, m)[:10]:>10s}" for m in mods))
    for (pid, et), g in df.groupby(['planview_id', 'eval_type'], sort=False):
        by = {r.model: r for r in g.itertuples()}
        cells = []
        for m in mods:
            r = by.get(m)
            cells.append(f"{r.ratio:>9.2f}{'*' if r.within_30pct else ' '}" if r is not None and r.can_fire else f"{'-':>10s}")
        f = g.iloc[0]
        print(f"  {str(f.project)[:30]:30s} {str(f.archetype)[:22]:22s} {str(f.eval_type)[:18]:18s} {f.truth_2024_musd:>8,.0f} " + ' '.join(cells))
    print("  (* = within +/-30%)")
    print("\nNot reproduced from the reference harness: Composite with OH correction from the truth "
          "(oracle), SURF component scoring (4 hard-coded projects), Benchmark_CalcSized, Offshore_Combined.")
    if args.csv:
        df.to_csv(args.csv, index=False); print(f"wrote {args.csv}")


if __name__ == '__main__':
    main()
