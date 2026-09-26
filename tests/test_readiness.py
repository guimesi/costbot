"""model_readiness() must agree with what screen_project() actually fires."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from costbot.data import DataStore  # noqa: E402
from costbot.screening import model_readiness, screen_project, MODEL_ORDER  # noqa: E402


def by_id(rows):
    return {r['model_id']: r for r in rows}


def test_empty_scope_nothing_routed():
    r = by_id(model_readiness({}))
    assert all(v['status'] == 'not_routed' for v in r.values())


def test_onshore_petchem_minimal():
    r = by_id(model_readiness({'archetype': 'onshore_petchem', 'location': 'US Gulf Coast'}))
    assert r['Benchmark']['status'] == 'ready'
    assert r['Calculator_Onshore']['status'] == 'needs' and 'facility' in r['Calculator_Onshore']['needs']
    assert r['EquipmentVector']['status'] == 'needs'
    assert r['Composite']['status'] == 'needs'
    assert r['OSBL_Estimate']['status'] == 'auto'
    for mid in ('Calculator_Offshore', 'Calculator_Pipeline', 'Calculator_LNG', 'SURF_User', 'Unconventional'):
        assert r[mid]['status'] == 'not_routed', mid


def test_unknown_facility_type_is_explained():
    r = by_id(model_readiness({'archetype': 'onshore_petchem', 'facility_type': 'flux capacitor', 'primary_capacity': 10}))
    assert r['Calculator_Onshore']['status'] == 'needs'
    assert 'flux capacitor' in r['Calculator_Onshore']['needs']


def test_refinery_bf_exclusion_visible():
    r = by_id(model_readiness({'archetype': 'refinery_bf', 'facility_type': 'hydrotreater', 'primary_capacity': 40000}))
    assert r['Calculator_Onshore']['status'] == 'excluded'
    assert r['OSBL_Estimate']['status'] == 'auto'  # excluded calculator gives no ISBL


def test_osbl_ready_when_onshore_ready():
    r = by_id(model_readiness({'archetype': 'onshore_petchem', 'facility_type': 'polypropylene', 'primary_capacity': 450}))
    assert r['Calculator_Onshore']['status'] == 'ready' and r['OSBL_Estimate']['status'] == 'ready'


def test_offshore_surf_and_osbl():
    r = by_id(model_readiness({'archetype': 'offshore_fpso'}))
    assert r['SURF_User']['status'] == 'needs' and r['OSBL_Estimate']['status'] == 'not_routed'
    r = by_id(model_readiness({'archetype': 'offshore_fpso', 'surf_scope': {'subsea_trees': {'g': 4}}}))
    assert r['SURF_User']['status'] == 'ready'
    assert r['Calculator_Offshore']['status'] == 'needs'


def test_order_is_stable():
    assert [r['model_id'] for r in model_readiness({'archetype': 'refinery_bf'})] == MODEL_ORDER


def test_prediction_matches_engine_on_smoke_scenarios():
    data = DataStore()
    if data.pool.empty:
        pytest.skip('no data package')
    import smoke_test  # scripts/smoke_test.py
    for title, scope, _expected in smoke_test.SCENARIOS:
        predicted = {r['model_id'] for r in model_readiness(scope, data) if r['status'] == 'ready'}
        res = screen_project(scope, data)
        fired = {m for m, r in res['models'].items() if r.get('can_fire') and not r.get('excluded_by_rule')}
        assert predicted == fired, (title, predicted ^ fired)
