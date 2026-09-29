"""Calculator_Onshore parity with the reference onshore_calculator.py.

The numeric parity test imports the reference file from reference/ (gitignored,
confidential) and skips when it is absent; the rest pins the ported rules."""
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from costbot.data import DataStore  # noqa: E402
from costbot.escalation import _get_emma_index  # noqa: E402
from costbot.models.calculator_onshore import run_calculator_onshore, resolve_facility  # noqa: E402

D = DataStore('/nonexistent')


def run(**kw):
    scope = {'facility_type': 'polypropylene', 'primary_capacity': 450, 'capacity_unit': 'KTA',
             'location': 'GOM', 'greenfield_brownfield': 'greenfield'}
    scope.update(kw)
    return run_calculator_onshore(scope, D)


# ---------------------------------------------------------------- scope type / multiplier

def test_api_scope_type_rule():
    assert run()['detail']['tec_multiplier'] == 2.58
    assert run(greenfield_brownfield='brownfield')['detail']['tec_multiplier'] == 2.61
    # the API sends BF-expansion for a 'modification' scope too; only a direct
    # calculator call (calculator_scope_type) reaches the 1.30 chain
    assert run(scope_type='modification')['detail']['tec_multiplier'] == 2.61
    assert run(calculator_scope_type='BF-unit-mod')['detail']['tec_multiplier'] == 1.30


def test_unknown_scope_type_falls_back_to_gf_multiplier():
    # reference: TEC_MULTIPLIERS.get(scope_type, 2.58); the golden file's plain "BF" lands here
    assert run(calculator_scope_type='BF')['detail']['tec_multiplier'] == 2.58


def test_modification_facility_forces_unit_mod_with_warning():
    r = run(facility_type='compressor_station_conversion', primary_capacity=70, capacity_unit='MMSCFD',
            greenfield_brownfield='brownfield')
    assert r['detail']['scope_type'] == 'BF-unit-mod' and r['detail']['tec_multiplier'] == 1.30
    assert 'BF-unit-mod' in r['warning']
    # API map: train_conversion -> compressor_station_conversion
    r2 = run(facility_type='train_conversion', primary_capacity=70, capacity_unit='MMSCFD')
    assert r2['detail']['correlation_used'] == 'compressor_station_conversion'
    assert r2['detail']['tec_multiplier'] == 1.30


def test_chain_has_no_contingency():
    r = run(location='Singapore')
    d = r['detail']
    assert d['isbl_gom_M'] == pytest.approx(136.0, abs=0.01)
    assert d['emma_factor'] == pytest.approx(404 / 202, abs=1e-4)
    assert r['estimate_musd'] == pytest.approx(136.0 * 2 * 2.58 * 1.06, rel=1e-3)
    assert d['contingency_M'] == 0.0
    assert r['estimate_low_musd'] == pytest.approx(r['estimate_musd'] * 0.5, abs=0.1)
    assert r['estimate_high_musd'] == pytest.approx(r['estimate_musd'] * 1.5, abs=0.1)


# ---------------------------------------------------------------- facility resolution

def test_resolution_order():
    assert resolve_facility('polypropylene') == ('tuple', 'polypropylene', None)
    assert resolve_facility('PP')[1] == 'polypropylene'
    assert resolve_facility('Delayed Coker')[1] == 'refinery_bf'          # substring 'coker'
    assert resolve_facility('polyethylene_expansion')[1] == 'ethylene_complex'  # reference quirk: 'ethylene' hits first
    assert resolve_facility('crude_unit') == ('ic_alias', 'crude_distillation_unit', None)
    kind, key, why = resolve_facility('flux_capacitor')
    assert (kind, key) == ('tuple', 'process_plant_generic') and 'generic' in why


def test_generic_fallback_fires_with_warning():
    r = run(facility_type='flux capacitor', primary_capacity=300)
    assert r['can_fire'] and r['detail']['correlation_used'] == 'process_plant_generic'
    assert 'generic' in r['warning'] and r['detail']['tuple_verified'] is False
    assert r['detail']['calibration_status']['N'] == 0


def test_empty_facility_type_is_generic():
    r = run(facility_type='', primary_capacity=500)
    assert r['can_fire'] and r['detail']['correlation_used'] == 'process_plant_generic'


def test_ic_library_cdu_curve():
    r = run(facility_type='crude_unit', primary_capacity=200, capacity_unit='KBSD')
    assert r['detail']['is_ic_library'] and r['detail']['isbl_gom_M'] == pytest.approx(0.0662 * 200 + 3.3812, abs=0.01)
    assert r['detail']['calibration_status']['circular'] is False
    # BPD is converted to kB/SD, same answer
    r2 = run(facility_type='cdu', primary_capacity=200000, capacity_unit='BPD')
    assert r2['estimate_musd'] == r['estimate_musd']
    # outside 50..500 kB/SD via an alias: the reference raises, the API reports no fire
    r3 = run(facility_type='crude_unit', primary_capacity=600, capacity_unit='KBSD')
    assert not r3['can_fire'] and 'out_of_range' in r3['no_fire_reason']


def test_missing_capacity_does_not_fire():
    r = run_calculator_onshore({'facility_type': 'polypropylene'}, D)
    assert not r['can_fire'] and r['no_fire_reason'] == 'missing_capacity'


# ---------------------------------------------------------------- units (engine deviation)

def test_unit_conversion_when_known():
    assert run(facility_type='hydrotreater', primary_capacity=40, capacity_unit='KBPD')['estimate_musd'] == \
        run(facility_type='hydrotreater', primary_capacity=40000, capacity_unit='BPD')['estimate_musd']


def test_unknown_unit_uses_raw_value_with_warning():
    r = run(capacity_unit='MMSCFD')
    assert r['can_fire'] and r['estimate_musd'] == run()['estimate_musd']
    assert 'MMSCFD' in r['warning']


# ---------------------------------------------------------------- EMMA lookup (reference semantics)

@pytest.mark.parametrize('location,index', [
    ('US Gulf Coast', 414), ('GOM', 202), ('Texas-BMT', 414), ('Eastern Canada', 486),
    ('Alberta', 486), ('Joliet', 202), ('New Mexico', 202), ('Texas-BTN (GOM)', 202), ('', 202),
])
def test_emma_index_reference_lookup(location, index):
    assert _get_emma_index(location) == index


# ---------------------------------------------------------------- numeric parity with the reference file

REF = os.path.join(ROOT, 'reference', 'onshore_calculator.py')

CASES = [
    ('polypropylene', 450, 'KTA', 'US Gulf Coast', 'GF'),
    ('polyethylene', 800, 'KTA', 'Singapore', 'GF'),
    ('hydrotreater', 40000, 'BPD', 'US Gulf Coast', 'BF-unit-mod'),
    ('ccs', 2.0, 'MTPA_CO2', 'US Gulf Coast', 'GF'),
    ('ethylene_cracker', 1800, 'KTA', 'Canada', 'BF-expansion'),
    ('chemical_expansion', 1500, 'KTA', 'Baytown', 'GF'),
    ('refinery_bf', 50000, 'BPD', 'Joliet', 'BF'),
    ('refinery_bf', 50000, 'BPD', 'Baton Rouge', 'BF'),
    ('crude_unit', 200, 'KBSD', 'Fawley', 'GF'),
    ('cdu', 200000, 'BPD', 'Fawley', 'GF'),
    ('flux_capacitor', 300, 'KTA', 'Eastern Canada', 'GF'),
    ('delayed_coker', 30000, 'BPD', 'Texas-BMT', 'BF-expansion'),
    ('compressor_station_conversion', 70, 'MMSCFD', 'Texas', 'BF-expansion'),
    ('atmospheric_pipestill', 100, 'KTA', 'New Mexico', 'GF'),
    ('Gas Plant', 200, 'MMSCFD', 'Texas-BTN (GOM)', 'GF'),
    ('polyethylene_expansion', 500, 'KTA', 'Shanghai', 'GF'),
    ('hydrogen_plant', 100, 'KTA', 'Rotterdam', 'GF'),
    ('process_plant_generic', 500, 'KTA', 'GOM', 'GF'),
]


@pytest.mark.skipif(not os.path.exists(REF), reason='reference/onshore_calculator.py not present')
@pytest.mark.parametrize('ft,cap,unit,loc,st', CASES)
def test_parity_with_reference(ft, cap, unit, loc, st):
    sys.modules.setdefault('standard_result', types.SimpleNamespace(StandardResult=object))
    sys.path.insert(0, os.path.dirname(REF))
    from onshore_calculator import estimate_onshore_tec  # noqa: E402
    ref = estimate_onshore_tec(facility_type=ft, capacity_value=cap, capacity_unit=unit, location=loc, scope_type=st)
    eng = run_calculator_onshore({'facility_type': ft, 'primary_capacity': cap, 'capacity_unit': unit,
                                  'location': loc, 'calculator_scope_type': st}, D)
    assert eng['can_fire']
    assert eng['estimate_musd'] == pytest.approx(ref['tec_escalated_M'], rel=1e-6)
    assert eng['detail']['correlation_used'] == ref['correlation_used']
    assert eng['detail']['emma_location_index'] == ref['emma_location_index']
    assert eng['detail']['tec_multiplier'] == ref['tec_multiplier']
