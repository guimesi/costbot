#!/usr/bin/env python3
"""Headless UI test using streamlit.testing.v1.AppTest.
Runs app.py (st.navigation entry), fills DEMO_SCRIPT scenario 1 on the
estimator page, exercises the list cards, clicks Run, then renders every other
page and checks that nothing raised.

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

    at.selectbox(key='facility_type_choice').select('polypropylene')
    at.number_input(key='capacity').set_value(450.0)
    at.selectbox(key='cap_unit').select('KTA')
    at.run()
    assert not at.exception, at.exception

    # Card 2 fragment: add two equipment items, remove one (callbacks, no rerun call)
    at.selectbox(key='eq_type').select('pump')
    at.number_input(key='eq_count').set_value(8)
    at.button(key='eq_add').click().run()
    assert not at.exception, at.exception
    at.selectbox(key='eq_type').select('exchanger')
    at.button(key='eq_add').click().run()
    assert [e['type'] for e in at.session_state['equipment_items']] == ['pump', 'exchanger']
    at.button(key='eqrm_0').click().run()
    assert [e['type'] for e in at.session_state['equipment_items']] == ['exchanger']

    # Card 5 fragment: add a scope item, input is cleared after add
    at.text_input(key='si_facility').input('Utilities')
    at.button(key='si_add').click().run()
    assert at.session_state['scope_items'] == [{'type': 'process_unit', 'facility_type': 'Utilities'}]
    assert at.session_state['si_facility'] == ''

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
    assert {'Benchmark', 'Calculator_Onshore', 'OSBL_Estimate', 'EquipmentVector', 'Composite'} <= fired, fired

    # Every other page must render without exceptions or error elements
    for page in ['app_pages/data_package.py', 'app_pages/code_inventory.py',
                 'app_pages/dependencies.py', 'app_pages/model_specs.py']:
        at.switch_page(page)
        at.run()
        assert not at.exception, (page, at.exception)
        assert not at.error, (page, [e.value for e in at.error])
    at.switch_page('app_pages/estimator.py')
    at.run()
    results = at.session_state['last_results']  # survives page switches

    metrics = [m.label for m in at.metric]
    assert 'Best Estimate (P50)' in metrics, metrics
    markdown_text = ' '.join(m.value for m in at.markdown)
    assert 'Model Readiness' in markdown_text
    print(f"UI OK: P50=${ens['best_estimate_musd']:,.0f}M conf={ens['confidence']} fired={sorted(fired)}")


if __name__ == '__main__':
    main()
