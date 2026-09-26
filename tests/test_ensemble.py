"""Unit tests for the ensemble rules the README specifies, independent of data.

    .venv/bin/python -m pytest tests -q
"""
import math
import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import (  # noqa: E402
    _assess_confidence, SPREAD_GATE_RATIO, validate_bid,
    _get_cp30_escalation_factor, _build_equipment_vector, EQ_TYPE_INDEX,
    resolve_country, run_calculator_onshore, DataStore, screen_project,
)


def m(model_id, est, lo=None, hi=None):
    return {'model_id': model_id, 'can_fire': True, 'estimate_musd': est,
            'estimate_low_musd': lo if lo is not None else est * 0.8,
            'estimate_high_musd': hi if hi is not None else est * 1.2}


# ---------------------------------------------------------------- tiers

def test_no_models_cannot_estimate():
    r = _assess_confidence([])
    assert r['confidence'] == 'CANNOT_ESTIMATE' and r['best_estimate_musd'] is None


def test_three_agreeing_models_high():
    r = _assess_confidence([m('Benchmark', 100), m('Calculator_Onshore', 110), m('EquipmentVector', 95)])
    assert r['confidence'] == 'HIGH'
    assert r['best_estimate_musd'] == 100
    assert r['models_agree_30pct'] == 3


def test_two_models_within_30pct_medium_high():
    r = _assess_confidence([m('Benchmark', 100), m('EquipmentVector', 120)])
    assert r['confidence'] == 'MEDIUM-HIGH'


def test_two_models_disagree_medium():
    # ratio 2.5 < 3x gate, but each is 43% away from the median 175
    r = _assess_confidence([m('Benchmark', 100), m('EquipmentVector', 250)])
    assert r['confidence'] == 'MEDIUM'


def test_single_model_low():
    r = _assess_confidence([m('Benchmark', 100)])
    assert r['confidence'] == 'LOW' and r['models_included'] == ['Benchmark']


# ---------------------------------------------------------------- spread gate

def test_spread_gate_removes_lowest_priority_first():
    # Benchmark (priority 1) vs Calculator (priority 3), ratio 10x > 3x gate
    r = _assess_confidence([m('Benchmark', 1000), m('Calculator_Onshore', 100)])
    assert r['spread_gated'] is True
    assert r['models_included'] == ['Calculator_Onshore']
    assert r['models_gated_out'][0][0] == 'Benchmark'
    assert r['confidence'] == 'LOW'


def test_spread_gate_same_priority_removes_furthest_from_median():
    r = _assess_confidence([m('Benchmark', 100), m('EquipmentVector', 110), m('Composite', 1000)])
    assert [g[0] for g in r['models_gated_out']] == ['Composite']
    assert r['best_estimate_musd'] == 105


def test_spread_gate_ratio_is_three():
    assert SPREAD_GATE_RATIO == 3.0
    r = _assess_confidence([m('Benchmark', 100), m('EquipmentVector', 299)])
    assert not r['spread_gated']


# ---------------------------------------------------------------- blends

def test_geometric_blend_calc_onshore_vs_benchmark():
    r = _assess_confidence([m('Calculator_Onshore', 100), m('Benchmark', 200)])
    assert r['models_included'] == ['GeometricBlend']
    assert r['best_estimate_musd'] == pytest.approx(math.sqrt(100 * 200), abs=0.1)


def test_geometric_blend_not_applied_when_close():
    r = _assess_confidence([m('Calculator_Onshore', 100), m('Benchmark', 140)])
    assert 'GeometricBlend' not in r['models_included']
    assert r['best_estimate_musd'] == 120


def test_unconventional_override():
    r = _assess_confidence([m('Benchmark', 300), m('Calculator_Onshore', 150), m('Unconventional', 80)],
                           archetype='onshore_unconventional')
    assert r['models_included'] == ['Unconventional']
    assert r['best_estimate_musd'] == 80
    assert r['confidence'] == 'MEDIUM'


def test_unconventional_not_authoritative_elsewhere():
    r = _assess_confidence([m('Benchmark', 100), m('Unconventional', 120)], archetype='gas_processing')
    assert set(r['models_included']) == {'Benchmark', 'Unconventional'}


# ---------------------------------------------------------------- range cap

def test_range_capped_at_5x():
    r = _assess_confidence([m('Benchmark', 100, lo=10, hi=1000), m('EquipmentVector', 100, lo=10, hi=1000)])
    assert r['range_capped'] is True
    assert r['range_high_musd'] / r['range_low_musd'] == pytest.approx(5.0, rel=1e-3)
    assert math.sqrt(r['range_low_musd'] * r['range_high_musd']) == pytest.approx(100, rel=1e-2)


def test_range_not_capped_when_narrow():
    r = _assess_confidence([m('Benchmark', 100, lo=60, hi=150)])
    assert not r.get('range_capped')
    assert (r['range_low_musd'], r['range_high_musd']) == (60, 150)


# ---------------------------------------------------------------- bid validation

def _results(p50=100, lo=70, hi=150):
    return {'ensemble': {'best_estimate_musd': p50, 'range_low_musd': lo, 'range_high_musd': hi}}


@pytest.mark.parametrize('bid,verdict', [(100, 'WITHIN_RANGE'), (70, 'WITHIN_RANGE'),
                                         (151, 'ABOVE_RANGE'), (69, 'BELOW_RANGE')])
def test_validate_bid_verdicts(bid, verdict):
    assert validate_bid(_results(), bid, 'TEC')['verdict'] == verdict


def test_validate_bid_epc_lumpsum_adjusts():
    r = validate_bid(_results(), 117.5, 'EPC_lumpsum')
    assert r['adjusted_bid_musd'] == 100


def test_validate_bid_without_estimate():
    assert validate_bid({'ensemble': {}}, 100)['verdict'] == 'CANNOT_ASSESS'


# ---------------------------------------------------------------- CP30 escalation

def _cp30():
    return pd.DataFrame([{'location': 'Texas-BTN (GOM)', 'year': y, 'combined_idx': 2.0 * 1.05 ** (y - 2024)}
                         for y in range(2020, 2026)])


def test_cp30_same_year_is_one():
    assert _get_cp30_escalation_factor(_cp30(), 2024) == 1.0


def test_cp30_in_range_ratio():
    assert _get_cp30_escalation_factor(_cp30(), 2025) == pytest.approx(1.05)


def test_cp30_extrapolates_beyond_last_year():
    assert _get_cp30_escalation_factor(_cp30(), 2027) == pytest.approx(1.05 ** 3, rel=1e-6)


def test_cp30_empty_table_is_one():
    assert _get_cp30_escalation_factor(pd.DataFrame(), 2026) == 1.0


# ---------------------------------------------------------------- equipment vector

def test_equipment_vector_zeroes_non_process_and_normalizes():
    vec, resolved, unresolved, total, process = _build_equipment_vector(
        {'pump': 3, 'heat exchanger': 4, 'control valve': 100, 'flux capacitor': 1})
    assert unresolved == ['flux capacitor']
    assert resolved == {'pump': 3, 'exchanger': 4, 'valve': 100}
    assert vec[EQ_TYPE_INDEX['valve']] == 0.0
    assert abs(sum(vec ** 2) - 1.0) < 1e-9
    assert total == 107 and process == 7


# ---------------------------------------------------------------- location

@pytest.mark.parametrize('loc,country', [('US Gulf Coast', 'United States'), ('china', 'China'),
                                         ('Guyana', 'Guyana'), ('Atlantis', '')])
def test_resolve_country_from_location(loc, country):
    assert resolve_country({'location': loc}) == country


def test_resolve_country_explicit_wins():
    assert resolve_country({'location': 'US Gulf Coast', 'country': 'Canada'}) == 'Canada'


# ---------------------------------------------------------------- calculator basics (no data needed)

def test_onshore_six_tenths_scaling():
    d = DataStore('/nonexistent')
    a = run_calculator_onshore({'facility_type': 'polypropylene', 'primary_capacity': 450,
                                'capacity_unit': 'KTA', 'location': 'GOM', 'scope_type': 'greenfield'}, d)
    b = run_calculator_onshore({'facility_type': 'polypropylene', 'primary_capacity': 900,
                                'capacity_unit': 'KTA', 'location': 'GOM', 'scope_type': 'greenfield'}, d)
    assert a['can_fire'] and b['can_fire']
    assert b['detail']['isbl_gom_M'] / a['detail']['isbl_gom_M'] == pytest.approx(2 ** 0.6, rel=1e-3)
    assert a['detail']['emma_factor'] == 1.0  # GOM is the EMMA base


def test_onshore_unit_mismatch_does_not_fire():
    r = run_calculator_onshore({'facility_type': 'polypropylene', 'primary_capacity': 450,
                                'capacity_unit': 'MMSCFD', 'location': 'GOM'}, DataStore('/nonexistent'))
    assert not r['can_fire'] and 'unit_mismatch' in r['no_fire_reason']


# ---------------------------------------------------------------- component-only (needs mock data)

def test_component_only_when_only_surf_fires():
    data = DataStore()
    if data.pool.empty:
        pytest.skip('no data package')
    scope = {'archetype': 'offshore_fpso', 'location': 'Guyana', 'basis_year': 2024,
             'surf_scope': {'subsea_trees': {'g': 6}, 'flowlines': [{'id': 'a'}], 'risers': [], 'water_depth_m': 1500}}
    # Force Benchmark off by using an archetype the pool alias maps but with an empty pool copy
    res = screen_project(scope, DataStore('/nonexistent'))
    assert res['ensemble']['confidence'] == 'COMPONENT_ONLY'
    assert 'SURF' in res['ensemble']['component_estimates']


def test_screening_floor_note():
    res = screen_project({'archetype': 'onshore_unconventional', 'location': 'GOM', 'basis_year': 2024,
                          'facility_type': 'compressor_station', 'primary_capacity': 5, 'capacity_unit': 'MMSCFD',
                          'scope_type': 'greenfield'}, DataStore('/nonexistent'))
    assert res['ensemble']['best_estimate_musd'] < 20
    assert res['screening_floor_note']
