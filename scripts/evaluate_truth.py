#!/usr/bin/env python3
"""Reproduce the accuracy claim: run every project in project_truth.csv
through screen_project() (LOOCV: the project's own pool entry is excluded by
planview_id) and report the hit rate at +/-30% per archetype.

    python scripts/evaluate_truth.py [--tolerance 0.30] [--data-dir PATH] [--csv out.csv]
                                     [--redact] [--no-normalize] [--col key=column ...]

How the real schema is handled (all choices are printed):
- The truth amount (`amount_musd`) is in `basis_year` dollars. It is brought to
  2024 with the CP30 indices the pool carries for the same project
  (`cp30_idx_2024 / cp30_idx_basis`), else with the CP30 table at the
  project's cp30_location, else left as is. `--no-normalize` skips this.
- Several rows per project (e.g. TEC and ISBL): the row whose `cost_type`
  looks like a total (tec/total/capex) wins, else the first row.
- Scope inputs (location, facility type, capacity) are not in the truth
  table; they are taken from the pool row with the same planview_id.
- Column names are auto-detected; `--col tec=<name>` etc. overrides.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from costbot.data import DataStore  # noqa: E402
from costbot.escalation import _get_cp30_index  # noqa: E402
from costbot.screening import screen_project  # noqa: E402
from costbot.constants import ARCHETYPE_MODELS, ARCHETYPE_ALIASES_POOL, resolve_country  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass

CANDIDATES = {
    'tec': ['tec_musd_actual', 'actual_tec_musd', 'tec_actual_musd', 'amount_musd', 'tec_musd_normalized_2024',
            'tec_musd_2024', 'tec_musd', 'actual_cost_musd', 'truth_tec_musd'],
    'archetype': ['archetype', 'archetype_2d', 'project_archetype'],
    'name': ['project_name', 'name', 'project'],
    'pid': ['planview_id', 'project_id', 'pid'],
    'basis_year': ['basis_year', 'cost_basis_year', 'year'],
    'cost_type': ['cost_type', 'amount_type'],
    'location': ['location', 'cp30_location', 'site_location', 'country', 'region'],
    'country': ['country', 'location'],
    'scope_type': ['scope_type', 'scope', 'greenfield_brownfield', 'bf_gf'],
    'facility_type': ['facility_type', 'facility', 'unit_type'],
    'capacity': ['primary_capacity', 'capacity_value', 'capacity'],
    'capacity_unit': ['capacity_unit', 'unit'],
    'process_domain': ['process_domain', 'domain'],
}
FUZZY = {
    'tec': [('amount', 'musd'), ('tec', 'musd'), ('actual', 'cost'), ('actual', 'tec'), ('truth', 'tec'),
            ('cost', 'musd'), ('tec',), ('capex',)],
    'archetype': [('archetype',)], 'name': [('project', 'name'), ('name',)],
    'pid': [('planview',), ('project_id',)], 'basis_year': [('basis', 'year')], 'cost_type': [('cost', 'type')],
    'location': [('cp30', 'loc'), ('location',), ('country',), ('region',)],
    'country': [('country',), ('location',)], 'scope_type': [('scope', 'type'), ('bf', 'gf')],
    'facility_type': [('facility', 'type'), ('facility',)], 'capacity': [('capacity', 'value'), ('capacity',)],
    'capacity_unit': [('capacity', 'unit')], 'process_domain': [('process', 'domain'), ('domain',)],
}
SCOPE_TO_BFGF = {'grassroots': 'greenfield', 'greenfield': 'greenfield', 'gf': 'greenfield',
                 'expansion': 'expansion', 'bf-expansion': 'expansion', 'brownfield': 'brownfield',
                 'bf': 'brownfield', 'modification': 'modification', 'bf-unit-mod': 'modification',
                 'debottleneck': 'modification', 'replacement': 'modification'}
POOL_TO_APP = {}
for _app, _pool in ARCHETYPE_ALIASES_POOL.items():
    POOL_TO_APP.setdefault(_pool, _app)


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
                if key == 'tec' and any(bad in cl for bad in ('unit', 'year', 'source', 'note', '_id', 'name', 'original')):
                    continue
                return c
    return None


def _val(row, col, default=None):
    if col is None or col not in row.index:
        return default
    v = row[col]
    if v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and not v.strip()):
        return default
    return v


def pick_row_per_project(truth, pid_col, cost_type_col):
    """One row per project. Prefer a cost_type that looks like a total."""
    if pid_col is None:
        return truth, 0
    dropped = 0
    keep = []
    for _, grp in truth.groupby(pid_col, sort=False):
        if len(grp) == 1:
            keep.append(grp.iloc[0]); continue
        chosen = None
        if cost_type_col:
            ct = grp[cost_type_col].astype(str).str.lower()
            mask = ct.str.contains('tec') | ct.str.contains('total') | ct.str.contains('capex')
            if mask.any():
                chosen = grp[mask].iloc[0]
        if chosen is None:
            chosen = grp.iloc[0]
        keep.append(chosen); dropped += len(grp) - 1
    return pd.DataFrame(keep), dropped


def normalize_to_2024(amount, basis_year, pool_row, cp30, location):
    """Return (amount_2024, method)."""
    if basis_year is None or int(basis_year) == 2024:
        return amount, 'already_2024'
    if pool_row is not None:
        pb, i0, i1 = _val(pool_row, 'basis_year'), _val(pool_row, 'cp30_idx_basis'), _val(pool_row, 'cp30_idx_2024')
        try:
            if i0 and i1 and float(i0) > 0 and (pb is None or int(pb) == int(basis_year)):
                return amount * float(i1) / float(i0), 'pool_cp30_idx'
        except (TypeError, ValueError):
            pass
    if location and not cp30.empty:
        i0 = _get_cp30_index(cp30, str(location), int(basis_year))
        i1 = _get_cp30_index(cp30, str(location), 2024)
        if i0 and i1:
            return amount * i1 / i0, 'cp30_table'
    return amount, 'not_normalized'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tolerance', type=float, default=0.30)
    ap.add_argument('--data-dir', default=None)
    ap.add_argument('--csv', default=None, help='write per-project results here')
    ap.add_argument('--redact', action='store_true', help='replace project names with archetype-N so the output can be shared')
    ap.add_argument('--no-normalize', action='store_true', help='compare against the raw truth amount, no CP30 to 2024')
    ap.add_argument('--col', action='append', default=[], metavar='KEY=COLUMN', help='override a detected column')
    ap.add_argument('--size-hint', choices=['api', 'capacity', 'bucket', 'pool', 'none'], default='api',
                    help="Benchmark size signal: api (reference: none unless the scope carries a size), "
                         "capacity (first build's capacity heuristic), bucket (the truth value's own size "
                         "bucket, i.e. a user who knows the order of magnitude), pool (project's own pool "
                         "TEC: the LOOCV enrichment), none (strip every size signal)")
    ap.add_argument('--exclude-forecast', action='store_true',
                    help='drop screening-forecast rows from the Benchmark pool (tec_source/gate_stage contains "forecast")')
    ap.add_argument('--summary-only', action='store_true', help='print the tables, not the per-project misses')
    ap.add_argument('--ensemble-mode', choices=['api', 'engine'], default='api',
                    help="api = cost_bot_api rules (default); engine = first build's priority gate, "
                         "unconventional override, geometric blend, symmetric 5x cap")
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
    print('Detected truth columns:', {k: v for k, v in cols.items() if v})
    missing = [k for k in ('tec', 'archetype') if not cols[k]]
    if missing:
        print(f"Cannot find column(s) for {missing}. Truth table columns are: {list(truth.columns)}")
        print("Re-run with e.g.  --col tec=<column name> --col archetype=<column name>"); sys.exit(2)

    for cat in ('cost_type', 'test_type', 'gate_stage', 'quality_role', 'scope_change_flag'):
        if cat in truth.columns:
            print(f"  {cat}: {truth[cat].astype(str).value_counts().to_dict()}")

    truth1, dropped = pick_row_per_project(truth, cols['pid'], cols['cost_type'])
    print(f"Rows: {len(truth)} -> {len(truth1)} projects ({dropped} secondary rows dropped)")

    pool = data.pool
    pool_by_pid = {}
    if not pool.empty and 'planview_id' in pool.columns:
        pool_by_pid = {str(k): r for k, r in pool.set_index(pool['planview_id'].astype(str)).iterrows()}

    rows, methods, ratios = [], {}, []
    counter = {}
    for _, r in truth1.iterrows():
        try:
            truth_raw = float(r[cols['tec']])
        except (TypeError, ValueError):
            continue
        if not truth_raw or truth_raw <= 0:
            continue
        pid = str(_val(r, cols['pid'], ''))
        prow = pool_by_pid.get(pid)

        archetype = str(_val(r, cols['archetype'], '') or (_val(prow, 'archetype', '') if prow is not None else '')).strip()
        if archetype not in ARCHETYPE_MODELS:
            archetype = POOL_TO_APP.get(archetype, archetype)
        scope_raw = str(_val(r, cols['scope_type'], None) or (_val(prow, 'scope_type', 'greenfield') if prow is not None else 'greenfield')).lower()
        bfgf = SCOPE_TO_BFGF.get(scope_raw, 'greenfield')
        location = _val(r, cols['location'], None) or (prow is not None and (_val(prow, 'cp30_location') or _val(prow, 'site_location') or _val(prow, 'country'))) or 'US Gulf Coast'
        country = _val(r, cols['country'], None) or (prow is not None and _val(prow, 'country')) or resolve_country({'location': str(location)})
        facility = _val(r, cols['facility_type'], None) or (prow is not None and _val(prow, 'facility_type')) or None
        cap = _val(r, cols['capacity'], None)
        if cap is None and prow is not None:
            cap = _val(prow, 'primary_capacity')
        unit = _val(r, cols['capacity_unit'], None) or (prow is not None and _val(prow, 'capacity_unit')) or ''
        domain = _val(r, cols['process_domain'], None) or (prow is not None and _val(prow, 'process_domain')) or None

        basis_year = _val(r, cols['basis_year'], None)
        if args.no_normalize:
            truth_2024, method = truth_raw, 'raw'
        else:
            truth_2024, method = normalize_to_2024(truth_raw, basis_year, prow, data.cp30, location)
        methods[method] = methods.get(method, 0) + 1
        if prow is not None and _val(prow, 'tec_musd_normalized_2024'):
            ratios.append(truth_2024 / float(prow['tec_musd_normalized_2024']))

        try:
            cap = float(cap) if cap is not None else None
        except (TypeError, ValueError):
            cap = None
        scope = {
            'project_name': str(_val(r, cols['name'], pid)), 'planview_id': pid, 'archetype': archetype,
            'process_domain': domain, 'location': str(location), 'country': str(country or ''),
            'basis_year': 2024, 'greenfield_brownfield': bfgf, 'scope_type': bfgf,
            'facility_type': (str(facility) if facility else None), 'primary_capacity': cap,
            'capacity_unit': str(unit), 'secondary_params': {},
            'benchmark_size_mode': ('api' if args.size_hint == 'bucket' else args.size_hint),
            'pool_exclude_forecast': args.exclude_forecast,
            'ensemble_mode': args.ensemble_mode,
        }
        if args.size_hint == 'bucket':
            from costbot.models.benchmark import bucket_for_musd
            scope['size_bucket'] = bucket_for_musd(truth_2024)
        if 'pipeline' in archetype and cap and str(unit).lower() in ('km', 'miles'):
            scope['length_km'] = cap * (1.609 if str(unit).lower() == 'miles' else 1.0); scope['od_inches'] = 36.0
        if 'lng' in archetype and cap and str(unit).upper() == 'MTPA':
            scope['lng_capacity_mtpa'] = cap
        if args.redact:
            counter[archetype] = counter.get(archetype, 0) + 1
            scope['project_name'] = f"{archetype}-{counter[archetype]:02d}"

        res = screen_project(scope, data)
        ens = res['ensemble']
        p50 = ens.get('best_estimate_musd')
        err = (p50 / truth_2024 - 1) if p50 else None
        fired = {m: mr['estimate_musd'] for m, mr in res['models'].items()
                 if mr.get('can_fire') and not mr.get('excluded_by_rule')
                 and not mr.get('is_component') and not mr.get('is_indirect') and mr.get('estimate_musd')}
        model_errs = {m: v / truth_2024 - 1 for m, v in fired.items()}
        bm = res['models'].get('Benchmark', {})
        size_src = (bm.get('size_signal') or {}).get('source', '') if bm.get('can_fire') else ''
        best_model = min(model_errs, key=lambda m: abs(model_errs[m])) if model_errs else None
        rows.append({
            'project': scope['project_name'], 'archetype': archetype, 'in_pool': prow is not None,
            'basis_year': basis_year, 'normalization': method,
            'truth_raw_musd': round(truth_raw, 1), 'truth_2024_musd': round(truth_2024, 1), 'p50_musd': p50,
            'ens_err_pct': round(err * 100, 1) if err is not None else None,
            'ens_hit': (abs(err) <= args.tolerance) if err is not None else False,
            'any_hit': any(abs(e) <= args.tolerance for e in model_errs.values()),
            'best_model': best_model,
            'best_err_pct': round(model_errs[best_model] * 100, 1) if best_model else None,
            'confidence': ens.get('confidence'), 'models_included': ','.join(ens.get('models_included', [])),
            'models_fired': ','.join(sorted(fired)), 'benchmark_size_source': size_src,
            'test_type': str(_val(r, 'test_type', '') if 'test_type' in truth1.columns else ''),
            'quality_role': str(_val(r, 'quality_role', '') if 'quality_role' in truth1.columns else ''),
            'facility_type': facility or '', 'capacity': cap, 'unit': unit,
        })

    if not rows:
        print('No usable truth rows.'); sys.exit(2)
    df = pd.DataFrame(rows)
    print(f"Normalization to 2024: {methods}")
    print(f"Projects found in the pool: {int(df.in_pool.sum())}/{len(df)}")
    if ratios:
        q = np.percentile(ratios, [25, 50, 75])
        print(f"Truth(2024) / pool TEC(2024) for the same project: median {q[1]:.2f}, IQR {q[0]:.2f} to {q[2]:.2f} "
              f"(near 1.00 means the two agree on what the project cost)")
    print(f"Settings: size-hint={args.size_hint}, exclude-forecast={args.exclude_forecast}, "
          f"ensemble-mode={args.ensemble_mode}, tolerance={args.tolerance}")
    print(f"Benchmark size signal used: {df.benchmark_size_source.value_counts().to_dict()}")
    only_bm = df[df.models_fired == 'Benchmark']
    print(f"Projects where Benchmark was the only TEC model: {len(only_bm)} "
          f"(hits {int(only_bm.ens_hit.sum())}); with a calculator too: {len(df) - len(only_bm)} "
          f"(hits {int(df[df.models_fired != 'Benchmark'].ens_hit.sum())})")
    for grp in ('test_type', 'quality_role'):
        if df[grp].astype(bool).any():
            parts = [f"{k}: {int(g.ens_hit.sum())}/{len(g)}" for k, g in df.groupby(grp)]
            print(f"Ensemble hits by {grp}: " + ', '.join(parts))
    tol = int(args.tolerance * 100)
    print(f"\n{'archetype':26s} {'n':>3s} {'ensemble':>10s} {'any-model':>10s} {'med|err|':>9s}")
    for arch, g in df.groupby('archetype'):
        med = g['ens_err_pct'].abs().median()
        print(f"{arch:26s} {len(g):>3d} {int(g.ens_hit.sum()):>4d} ({g.ens_hit.mean()*100:3.0f}%) "
              f"{int(g.any_hit.sum()):>4d} ({g.any_hit.mean()*100:3.0f}%) {med:>8.0f}%")
    print('-' * 64)
    print(f"{'TOTAL':26s} {len(df):>3d} {int(df.ens_hit.sum()):>4d} ({df.ens_hit.mean()*100:3.0f}%) "
          f"{int(df.any_hit.sum()):>4d} ({df.any_hit.mean()*100:3.0f}%)   at +/-{tol}%")
    no_est = df[df.p50_musd.isna()]
    if len(no_est):
        print(f"No ensemble estimate for {len(no_est)} project(s): "
              + '; '.join(f"{r.project} ({r.archetype}, facility={r.facility_type or '-'}, cap={r.capacity or '-'} {r.unit})" for r in no_est.itertuples()))
    misses = df[~df.ens_hit & df.p50_musd.notna()].sort_values('ens_err_pct', key=lambda s: s.abs(), ascending=False)
    if not misses.empty and not args.summary_only:
        print(f"\nEnsemble misses ({len(misses)}):")
        for m in misses.head(20).itertuples():
            best = f"best={m.best_model} ({m.best_err_pct:+.0f}%)" if m.best_model else 'no model'
            print(f"  {str(m.project)[:30]:30s} {m.archetype:22s} truth24=${m.truth_2024_musd:>8,.0f}M "
                  f"p50=${m.p50_musd:>8,.0f}M err={m.ens_err_pct:+6.0f}% {best} [{m.models_included}]")
    if args.csv:
        df.to_csv(args.csv, index=False); print(f"\nwrote {args.csv}")


if __name__ == '__main__':
    main()
