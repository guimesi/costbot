#!/usr/bin/env python3
"""Reproduce the accuracy claim: run every project_truth.csv row through
screen_project() (LOOCV: the project's own pool entry is excluded by
planview_id) and report hit rate at +/-30% per archetype.

    .venv/bin/python scripts/evaluate_truth.py [--tolerance 0.30] [--data-dir PATH] [--csv out.csv]

The truth table's column names in the real package are not known here, so
the script auto-detects them from candidate lists and prints what it used.
On the mock package the number it prints is meaningless; on the real package
it is the number to compare with the "40/52 (77%)" in the Sep 16 email.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import (  # noqa: E402
    DataStore, screen_project, resolve_country,
    ARCHETYPE_MODELS, ARCHETYPE_ALIASES_POOL,
)

CANDIDATES = {
    'tec': ['tec_musd_actual', 'actual_tec_musd', 'tec_actual_musd', 'tec_musd_normalized_2024',
            'tec_musd_2024', 'tec_musd', 'actual_cost_musd', 'truth_tec_musd'],
    'archetype': ['archetype', 'archetype_2d', 'project_archetype'],
    'name': ['project_name', 'name', 'project'],
    'pid': ['planview_id', 'project_id', 'pid'],
    'location': ['location', 'cp30_location', 'country', 'region'],
    'country': ['country', 'location'],
    'scope_type': ['scope_type', 'scope', 'greenfield_brownfield', 'bf_gf'],
    'facility_type': ['facility_type', 'facility', 'unit_type'],
    'capacity': ['primary_capacity', 'capacity_value', 'capacity'],
    'capacity_unit': ['capacity_unit', 'unit'],
    'process_domain': ['process_domain', 'domain'],
}

SCOPE_TO_BFGF = {'grassroots': 'greenfield', 'greenfield': 'greenfield', 'gf': 'greenfield',
                 'expansion': 'expansion', 'bf-expansion': 'expansion', 'brownfield': 'brownfield',
                 'bf': 'brownfield', 'modification': 'modification', 'bf-unit-mod': 'modification',
                 'debottleneck': 'modification', 'replacement': 'modification'}

POOL_TO_APP = {}
for app_arch, pool_arch in ARCHETYPE_ALIASES_POOL.items():
    POOL_TO_APP.setdefault(pool_arch, app_arch)


# Fallback tokens: a column qualifies if its lower-cased name contains every token of one tuple
FUZZY = {
    'tec': [('tec', 'musd'), ('tec', 'm'), ('actual', 'cost'), ('actual', 'tec'), ('truth', 'tec'), ('cost', 'musd'),
            ('tec',), ('cost_m',), ('capex',)],
    'archetype': [('archetype',)],
    'name': [('project', 'name'), ('name',)],
    'pid': [('planview',), ('project_id',)],
    'location': [('cp30', 'loc'), ('location',), ('country',), ('region',)],
    'country': [('country',), ('location',)],
    'scope_type': [('scope', 'type'), ('bf', 'gf'), ('greenfield',)],
    'facility_type': [('facility', 'type'), ('facility',), ('unit', 'type')],
    'capacity': [('capacity', 'value'), ('primary', 'capacity'), ('capacity',)],
    'capacity_unit': [('capacity', 'unit'), ('unit',)],
    'process_domain': [('process', 'domain'), ('domain',)],
}


def detect(df, key, overrides=None):
    if overrides and overrides.get(key):
        return overrides[key]
    for c in CANDIDATES[key]:
        if c in df.columns:
            return c
    numeric_needed = key in ('tec', 'capacity')
    for tokens in FUZZY.get(key, []):
        for c in df.columns:
            cl = str(c).lower()
            if all(t in cl for t in tokens):
                if numeric_needed and not pd.api.types.is_numeric_dtype(df[c]):
                    continue
                if key == 'tec' and any(bad in cl for bad in ('unit', 'year', 'source', 'note', 'id', 'name')):
                    continue
                return c
    return None


def build_scope(row, cols):
    def g(key, default=None):
        c = cols.get(key)
        if c is None:
            return default
        v = row[c]
        return default if (v is None or (isinstance(v, float) and np.isnan(v))) else v

    archetype = str(g('archetype', '')).strip()
    if archetype not in ARCHETYPE_MODELS:
        archetype = POOL_TO_APP.get(archetype, archetype)
    scope_raw = str(g('scope_type', 'greenfield')).lower().strip()
    bfgf = SCOPE_TO_BFGF.get(scope_raw, 'greenfield')
    location = str(g('location', 'US Gulf Coast'))
    cap = g('capacity')
    cap = float(cap) if cap is not None else None
    unit = str(g('capacity_unit', '') or '')
    scope = {
        'project_name': str(g('name', '')),
        'planview_id': str(g('pid', '')),
        'archetype': archetype,
        'process_domain': g('process_domain'),
        'location': location,
        'country': str(g('country', '')) or resolve_country({'location': location}),
        'basis_year': 2024,
        'greenfield_brownfield': bfgf, 'scope_type': bfgf,
        'facility_type': (str(g('facility_type', '')) or None),
        'primary_capacity': cap, 'capacity_unit': unit,
        'secondary_params': {},
    }
    if 'pipeline' in archetype and cap and unit.lower() in ('km', 'miles'):
        scope['length_km'] = cap * (1.609 if unit.lower() == 'miles' else 1.0)
        scope['od_inches'] = 36.0
    if 'lng' in archetype and cap and unit.upper() == 'MTPA':
        scope['lng_capacity_mtpa'] = cap
    return scope


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tolerance', type=float, default=0.30)
    ap.add_argument('--data-dir', default=None)
    ap.add_argument('--csv', default=None, help='write per-project results here')
    ap.add_argument('--redact', action='store_true', help='replace project names with archetype-N so the output can be shared')
    ap.add_argument('--col', action='append', default=[], metavar='KEY=COLUMN',
                    help='override a detected column, e.g. --col tec=actual_tec_musd_2024 --col location=cp30_region')
    args = ap.parse_args()

    data = DataStore(args.data_dir) if args.data_dir else DataStore()
    truth = data.truth
    if truth.empty:
        print('project_truth.csv not found or empty'); sys.exit(2)

    overrides = dict(kv.split('=', 1) for kv in args.col)
    bad = [v for v in overrides.values() if v not in truth.columns]
    if bad:
        print(f"--col column(s) not in the truth table: {bad}. Columns are: {list(truth.columns)}"); sys.exit(2)
    cols = {k: detect(truth, k, overrides) for k in CANDIDATES}
    print('Detected columns:', {k: v for k, v in cols.items() if v})
    missing = [k for k in ('tec', 'archetype') if not cols[k]]
    if missing:
        print(f"Cannot find column(s) for {missing}. Truth table columns are: {list(truth.columns)}")
        print("Re-run with e.g.  --col tec=<column name> --col archetype=<column name>")
        sys.exit(2)

    rows = []
    counter = {}
    for _, r in truth.iterrows():
        truth_tec = float(r[cols['tec']])
        if not truth_tec or truth_tec <= 0:
            continue
        scope = build_scope(r, cols)
        if args.redact:
            counter[scope['archetype']] = counter.get(scope['archetype'], 0) + 1
            scope['project_name'] = f"{scope['archetype']}-{counter[scope['archetype']]:02d}"
        res = screen_project(scope, data)
        ens = res['ensemble']
        p50 = ens.get('best_estimate_musd')
        err = (p50 / truth_tec - 1) if p50 else None
        fired = {m: mr['estimate_musd'] for m, mr in res['models'].items()
                 if mr.get('can_fire') and not mr.get('excluded_by_rule')
                 and not mr.get('is_component') and not mr.get('is_indirect') and mr.get('estimate_musd')}
        model_errs = {m: v / truth_tec - 1 for m, v in fired.items()}
        best_model = min(model_errs, key=lambda m: abs(model_errs[m])) if model_errs else None
        rows.append({
            'project': scope['project_name'], 'archetype': scope['archetype'],
            'truth_musd': truth_tec, 'p50_musd': p50,
            'ens_err_pct': round(err * 100, 1) if err is not None else None,
            'ens_hit': (abs(err) <= args.tolerance) if err is not None else False,
            'any_hit': any(abs(e) <= args.tolerance for e in model_errs.values()),
            'best_model': best_model,
            'best_err_pct': round(model_errs[best_model] * 100, 1) if best_model else None,
            'confidence': ens.get('confidence'), 'models_included': ','.join(ens.get('models_included', [])),
        })

    df = pd.DataFrame(rows)
    tol = int(args.tolerance * 100)
    print(f"\n{'archetype':26s} {'n':>3s} {'ensemble':>10s} {'any-model':>10s} {'med|err|':>9s}")
    for arch, g in df.groupby('archetype'):
        med = g['ens_err_pct'].abs().median()
        print(f"{arch:26s} {len(g):>3d} {int(g.ens_hit.sum()):>4d} ({g.ens_hit.mean()*100:3.0f}%) "
              f"{int(g.any_hit.sum()):>4d} ({g.any_hit.mean()*100:3.0f}%) {med:>8.0f}%")
    print('-' * 64)
    print(f"{'TOTAL':26s} {len(df):>3d} {int(df.ens_hit.sum()):>4d} ({df.ens_hit.mean()*100:3.0f}%) "
          f"{int(df.any_hit.sum()):>4d} ({df.any_hit.mean()*100:3.0f}%)   at +/-{tol}%")

    misses = df[~df.ens_hit].sort_values('ens_err_pct', key=lambda s: s.abs(), ascending=False)
    if not misses.empty:
        print(f"\nEnsemble misses ({len(misses)}):")
        for _, m in misses.head(15).iterrows():
            print(f"  {str(m.project)[:32]:32s} {m.archetype:22s} truth=${m.truth_musd:>8,.0f}M "
                  f"p50={('$%.0fM' % m.p50_musd) if m.p50_musd else 'none':>9s} err={m.ens_err_pct if m.ens_err_pct is not None else float('nan'):+6.0f}% "
                  f"best={m.best_model} ({m.best_err_pct:+.0f}%)" if m.best_model else
                  f"  {str(m.project)[:32]:32s} {m.archetype:22s} truth=${m.truth_musd:>8,.0f}M no estimate")
    if args.csv:
        df.to_csv(args.csv, index=False); print(f"\nwrote {args.csv}")


if __name__ == '__main__':
    main()
