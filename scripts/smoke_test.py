#!/usr/bin/env python3
"""Smoke test: run the 4 DEMO_SCRIPT scenarios through screen_project() without
the Streamlit UI and assert the expected models fire. Exit code 1 on failure.

    .venv/bin/python scripts/smoke_test.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import DataStore, screen_project, validate_bid, generate_html_report, resolve_country  # noqa: E402

# Windows consoles default to cp1252; keep the report symbols printable everywhere.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass



def scope_base(**kw):
    loc = kw.get('location', 'US Gulf Coast')
    s = {
        'project_name': kw.pop('project_name', 'smoke'),
        'archetype': kw.pop('archetype'),
        'process_domain': None, 'location': loc, 'country': resolve_country({'location': loc}),
        'basis_year': 2024, 'greenfield_brownfield': 'greenfield', 'scope_type': 'greenfield',
        'facility_type': None, 'primary_capacity': None, 'capacity_unit': '',
        'length_km': None, 'od_inches': 36.0, 'diameter_inches': 36.0,
        'topsides_weight_te': None, 'water_depth_m': None,
        'secondary_params': {'hull_type': 'FPSO_newbuild', 'topsides_weight_te': None, 'water_depth_m': None},
        'lng_capacity_mtpa': None, 'equipment_list': None, 'scope_items': None, 'surf_scope': None,
    }
    s.update(kw)
    return s


SCENARIOS = [
    ('1. Onshore petchem minimal',
     scope_base(archetype='onshore_petchem', facility_type='polypropylene', primary_capacity=450, capacity_unit='KTA'),
     {'Benchmark', 'Calculator_Onshore', 'OSBL_Estimate'}),
    ('2. Offshore FPSO full',
     scope_base(archetype='offshore_fpso', location='Guyana', topsides_weight_te=25000, water_depth_m=1800,
                secondary_params={'hull_type': 'FPSO_newbuild', 'topsides_weight_te': 25000, 'water_depth_m': 1800},
                equipment_list=[{'type': 'separator', 'count': 4}, {'type': 'compressor', 'count': 3},
                                {'type': 'pump', 'count': 8}, {'type': 'exchanger', 'count': 6},
                                {'type': 'vessel', 'count': 4}, {'type': 'swivel', 'count': 1}],
                surf_scope={'subsea_trees': {'generic': 12},
                            'flowlines': [{'id': f'FL{i}', 'count': 1} for i in range(6)],
                            'risers': [{'id': f'R{i}', 'count': 1} for i in range(4)],
                            'manifolds': {'generic': 2}, 'umbilicals': [{'id': f'U{i}'} for i in range(3)],
                            'water_depth_m': 1800}),
     {'Benchmark', 'Calculator_Offshore', 'EquipmentVector', 'SURF_User'}),
    ('3. Pipeline quick path',
     scope_base(archetype='pipeline_mainline', length_km=200, od_inches=24.0, diameter_inches=24.0),
     {'Benchmark', 'Calculator_Pipeline'}),
    ('4. Refinery BF modification',
     scope_base(archetype='refinery_bf', greenfield_brownfield='modification', scope_type='modification',
                facility_type='hydrotreater', primary_capacity=40000, capacity_unit='BPD',
                scope_items=[{'type': 'process_unit', 'facility_type': 'Hydrotreater'},
                             {'type': 'osbl', 'facility_type': 'Utilities'}]),
     {'Benchmark', 'Composite'}),
    ('5. Unconventional CDP',
     scope_base(archetype='onshore_unconventional', facility_type='central_delivery_point',
                primary_capacity=150, capacity_unit='MMSCFD', location='New Mexico'),
     {'Benchmark', 'Unconventional'}),
    ('6. LNG 2026 basis year (CP30 escalation)',
     dict(scope_base(archetype='lng_onshore', location='Australia', lng_capacity_mtpa=10, primary_capacity=10,
                     capacity_unit='MTPA'), basis_year=2026),
     {'Benchmark', 'Calculator_LNG'}),
]


def main():
    data = DataStore()
    failures = []
    for title, scope, expected in SCENARIOS:
        res = screen_project(scope, data)
        ens = res['ensemble']
        fired = {m for m, r in res['models'].items() if r.get('can_fire') and not r.get('excluded_by_rule')}
        excluded = {m for m, r in res['models'].items() if r.get('excluded_by_rule')}
        errors = {m: r.get('no_fire_reason') for m, r in res['models'].items()
                  if not r.get('can_fire') and 'not defined' in str(r.get('no_fire_reason', ''))}
        missing = expected - fired
        print(f"\n== {title}")
        print(f"   P50=${ens.get('best_estimate_musd')}M  range=${ens.get('range_low_musd')}-{ens.get('range_high_musd')}M  "
              f"conf={ens.get('confidence')}  included={ens.get('models_included')}")
        for m in sorted(res['models']):
            r = res['models'][m]
            if r.get('excluded_by_rule'):
                print(f"   x {m:20s} EXCLUDED ({r.get('exclusion_reason')})")
            elif r.get('can_fire'):
                print(f"   * {m:20s} ${r.get('estimate_musd'):>10,.1f}M")
            else:
                print(f"   - {m:20s} no fire: {r.get('no_fire_reason')}")
        if res.get('basis_year_note'):
            print(f"   note: {res['basis_year_note']}")
        if missing:
            failures.append(f"{title}: expected {sorted(missing)} to fire")
        if errors:
            failures.append(f"{title}: NameError in {errors}")
        if ens.get('best_estimate_musd') is None and ens.get('confidence') != 'COMPONENT_ONLY':
            failures.append(f"{title}: no ensemble estimate")
        # exercise report + bid validation paths
        html = generate_html_report(res)
        assert '<html' in html and scope['project_name'] in html or 'smoke' in html
        if ens.get('best_estimate_musd'):
            v = validate_bid(res, ens['best_estimate_musd'] * 1.05, 'TEC')
            assert v['verdict'] == 'WITHIN_RANGE', v

    # Scenario 4 must show the refinery_bf exclusion
    res4 = screen_project(SCENARIOS[3][1], data)
    if not res4['models'].get('Calculator_Onshore', {}).get('excluded_by_rule'):
        failures.append('4. Calculator_Onshore should be excluded for refinery_bf')

    # Benchmark must react to location (country -> region encoding)
    s_us = scope_base(archetype='onshore_petchem', location='US Gulf Coast')
    s_cn = scope_base(archetype='onshore_petchem', location='China')
    a = screen_project(s_us, data)['models']['Benchmark'].get('analogues', [])
    b = screen_project(s_cn, data)['models']['Benchmark'].get('analogues', [])
    if [x['planview_id'] for x in a] == [x['planview_id'] for x in b]:
        failures.append('Benchmark analogues identical for US Gulf Coast vs China (location ignored)')

    print("\n" + "=" * 70)
    if failures:
        for f in failures:
            print("FAIL:", f)
        sys.exit(1)
    print(f"SMOKE OK: {len(SCENARIOS)} scenarios, all expected models fired.")


if __name__ == '__main__':
    main()
