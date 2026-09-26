#!/usr/bin/env python3
"""Headless UI test using streamlit.testing.v1.AppTest.
Runs app.py, fills DEMO_SCRIPT scenario 1, clicks Run, checks for exceptions.

    .venv/bin/python scripts/ui_test.py
"""
import os
import sys

from streamlit.testing.v1 import AppTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    at = AppTest.from_file(os.path.join(ROOT, 'app.py'), default_timeout=60)
    at.run()
    assert not at.exception, f"exception on first render: {at.exception}"
    assert not at.error, f"error elements on first render: {[e.value for e in at.error]}"

    at.selectbox(key='archetype').select('onshore_petchem')
    at.selectbox(key='location').select('US Gulf Coast')
    at.selectbox(key='bf_gf').select('greenfield')
    at.run()
    assert not at.exception, at.exception

    at.text_input(key='facility_type').input('polypropylene')
    at.number_input(key='capacity').set_value(450.0)
    at.selectbox(key='cap_unit').select('KTA')
    at.run()
    assert not at.exception, at.exception

    run_btn = [b for b in at.button if b.label == 'Run Screening Estimate']
    assert run_btn, 'Run button not found'
    run_btn[0].click()
    at.run()
    assert not at.exception, f"exception after run: {at.exception}"
    assert not at.error, f"error elements after run: {[e.value for e in at.error]}"

    results = at.session_state['last_results']
    ens = results['ensemble']
    assert ens.get('best_estimate_musd'), ens
    fired = {m for m, r in results['models'].items() if r.get('can_fire')}
    assert {'Benchmark', 'Calculator_Onshore', 'OSBL_Estimate'} <= fired, fired

    metrics = [m.label for m in at.metric]
    assert 'Best Estimate (P50)' in metrics, metrics
    markdown_text = ' '.join(m.value for m in at.markdown)
    assert 'Model Readiness' in markdown_text
    print(f"UI OK: P50=${ens['best_estimate_musd']:,.0f}M conf={ens['confidence']} fired={sorted(fired)}")


if __name__ == '__main__':
    main()
