"""scripts/evaluate_harness.py: truth resolution and scorecard follow the reference harness rules."""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import evaluate_harness as eh  # noqa: E402


def _truth(rows):
    cols = ['planview_id', 'project_name', 'archetype', 'gate_stage', 'cost_type', 'amount_musd', 'test_type',
            'quality_role', 'scope_change_flag', 'basis_year']
    return pd.DataFrame(rows, columns=cols)


def test_truth_resolution_reference_rules():
    df = _truth([
        ('1', 'A', 'refinery_bf', 'FINAL', 'TEC', 100, 'predictive', 'EVALUATION', False, 2020),
        ('1', 'A', 'refinery_bf', 'G3', 'TEC', 90, 'screening_validation', 'EVALUATION', False, 2019),
        ('1', 'A', 'refinery_bf', 'G2', 'TEC', 80, 'screening_validation', 'EVALUATION', False, 2018),
        ('2', 'B', 'ccs', 'FINAL', 'TEC', 50, 'non_comparable', 'EVALUATION', False, 2024),
        ('3', 'C', 'oil_sands', 'G2', 'TEC', 30, 'screening_validation', 'INTEGRITY_CANARY', False, 2024),
        ('4', 'D', 'lng_onshore', 'FINAL', 'ISBL', 999, 'predictive', 'EVALUATION', False, 2024),
        ('5', 'E', 'onshore_petchem', 'G2', 'TEC', 10, 'other', 'REFERENCE', False, 2024),
    ])
    entries, notes = eh.resolve_truth(df)
    by = {(e['planview_id'], e['eval_type']): e for e in entries}
    # project 1: a Type B truth (FINAL) and a Type A truth (highest screening gate = G3)
    assert by[('1', 'Type_B_predictive')]['truth_musd'] == 100
    assert by[('1', 'Type_A_screening')]['truth_gate_stage'] == 'G3' and by[('1', 'Type_A_screening')]['truth_musd'] == 90
    # non_comparable FINAL is recorded under its own eval type
    assert ('2', 'Type_B_non_comparable') in by
    # canary without FINAL: highest gate, CANARY_check
    assert by[('3', 'CANARY_check')]['truth_musd'] == 30
    # ISBL rows and non-EVALUATION roles are filtered out
    assert not any(e['planview_id'] in ('4', '5') for e in entries)
    assert len(entries) == 4


def test_fallback_when_rules_do_not_apply():
    df = _truth([('9', 'Z', 'refinery_bf', 'IC4', 'TEC', 10, 'LOOCV', 'primary', False, 2024)])
    entries, notes = eh.resolve_truth(df)
    assert len(entries) == 1 and entries[0].get('fallback') is True
    assert any('1 project(s) outside the reference rules' in n for n in notes)


def test_norm_factor_and_location():
    f = {('Louisiana', 2020): 1.5, ('Louisiana', 2024): 1.8, ('Illinois', 2024): 2.0}
    assert eh.cp30_location('Joliet, IL') == 'Illinois'
    assert eh.cp30_location('somewhere') == 'Louisiana'
    assert eh.norm_factor(f, 'Louisiana', 2020) == (1.2, 'CP30_to_2024')
    assert eh.norm_factor(f, 'Illinois', 2020)[1] == 'CP30_to_2024_fallback_Louisiana'
    assert eh.norm_factor(f, 'Illinois', 2024) == (1.0, 'none_needed')
    assert eh.norm_factor({}, 'Illinois', 2020) == (1.0, 'raw')


def test_scorecard_any_model_any_truth():
    def row(pid, model, ratio, et='Type_A_screening', arch='x'):
        return {'planview_id': pid, 'archetype': arch, 'eval_type': et, 'model': model, 'can_fire': ratio is not None,
                'ratio': ratio, 'within_30pct': (abs(ratio - 1) <= 0.3) if ratio else None,
                'within_band': (0.7 <= ratio <= 1.6) if ratio else None}
    rows = [row('1', 'Benchmark', 2.0), row('1', 'Calculator_Onshore', 1.1),        # hit via the calculator
            row('2', 'Benchmark', 1.5), row('2', 'Calculator_Onshore', None),       # band only
            row('3', 'Benchmark', 3.0, et='Type_B_predictive'), row('3', 'Benchmark', 0.9),  # hit via the 2nd truth
            row('4', 'Benchmark', None)]                                            # nothing fired
    sc = eh.scorecard(rows, 't')
    assert (sc['n'], sc['fired'], sc['n30'], sc['band']) == (4, 3, 2, 3)
    assert [p for p, _ in sc['zero_viable']] == ['4']
