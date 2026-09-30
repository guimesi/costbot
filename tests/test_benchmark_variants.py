"""Benchmark: reference port vs the first build's engine variant, and the LOOCV rules."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from costbot.data import DataStore  # noqa: E402
from costbot.models.benchmark import run_benchmark, BENCHMARK_MODES  # noqa: E402
from costbot.screening import screen_project  # noqa: E402


@pytest.fixture(scope='module')
def data():
    d = DataStore()
    if d.pool.empty:
        pytest.skip('no data package')
    return d


def test_both_variants_fire_and_are_labelled(data):
    base = {'archetype': 'onshore_petchem', 'location': 'US Gulf Coast', 'basis_year': 2024}
    ref = run_benchmark({**base, 'benchmark_mode': 'reference'}, data)
    eng = run_benchmark({**base, 'benchmark_mode': 'engine'}, data)
    assert ref['can_fire'] and ref['model_variant'] == 'reference_v3'
    assert eng['can_fire'] and eng['model_variant'] == 'engine_size_band'
    assert run_benchmark(base, data)['model_variant'] == 'reference_v3'  # default
    assert set(BENCHMARK_MODES) == {'reference', 'engine'}


def test_engine_variant_uses_capacity_band_and_bucket(data):
    base = {'archetype': 'onshore_petchem', 'location': 'US Gulf Coast', 'benchmark_mode': 'engine'}
    none = run_benchmark(base, data)
    cap = run_benchmark({**base, 'primary_capacity': 450, 'capacity_unit': 'KTA'}, data)
    bucket = run_benchmark({**base, 'size_bucket': 'substantial'}, data)
    assert none['size_signal']['source'] == 'none'
    assert cap['size_signal']['source'] == 'capacity_heuristic' and cap['size_signal']['size_musd'] == 900.0
    assert bucket['size_signal']['source'] == 'size_bucket' and bucket['size_signal']['size_musd'] == 700.0
    assert cap['size_signal']['band_rows'] <= cap['size_signal']['pool_rows']


def test_engine_variant_never_reads_own_pool_row_unless_asked(data):
    pid = str(data.pool['planview_id'].iloc[0])
    arch = data.pool['archetype'].iloc[0]
    base = {'archetype': arch, 'location': 'US Gulf Coast', 'benchmark_mode': 'engine', 'planview_id': pid,
            'scope_type': 'modification'}  # a modification: the capacity heuristic is off too
    r = run_benchmark(base, data)
    assert r['size_signal']['source'] == 'none'
    assert all(a['planview_id'] != pid for a in r.get('analogues', []))
    leaky = run_benchmark({**base, 'benchmark_size_mode': 'pool'}, data)
    assert leaky['size_signal']['source'] == 'pool_tec'


def test_screen_project_reports_the_other_variant(data):
    res = screen_project({'archetype': 'onshore_petchem', 'location': 'US Gulf Coast', 'basis_year': 2024,
                          'benchmark_mode': 'engine', 'benchmark_compare': True}, data)
    assert res['models']['Benchmark']['model_variant'] == 'engine_size_band'
    alt = res['benchmark_alternate']
    assert alt['mode'] == 'reference' and alt['can_fire'] and alt['estimate_musd'] > 0
    res2 = screen_project({'archetype': 'onshore_petchem', 'location': 'US Gulf Coast', 'basis_year': 2024}, data)
    assert res2['benchmark_alternate'] is None
