#!/usr/bin/env python3
"""Headless UI test using streamlit.testing.v1.AppTest.

Runs app.py (st.navigation entry), fills DEMO_SCRIPT scenario 1 on the
estimator page, checks the live readiness list, exercises the list cards,
clicks Run, checks results and the stale notice, then renders every other
page and checks that nothing raised.

    .venv/bin/python scripts/ui_test.py
"""
import os

from streamlit.testing.v1 import AppTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def ok(at, where):
    assert not at.exception, f"{where}: {at.exception}"
    assert not at.error, f"{where}: {[e.value for e in at.error]}"


def md_text(at):
    return ' '.join(m.value for m in at.markdown)


def main():
    at = AppTest.from_file(os.path.join(ROOT, 'app.py'), default_timeout=60)
    at.run()
    ok(at, 'first render')
    assert 'Model readiness' in md_text(at)

    # Core inputs -> live readiness without pressing Run
    at.selectbox(key='archetype').select('onshore_petchem')
    at.selectbox(key='location').select('US Gulf Coast')
    at.run()
    ok(at, 'after core inputs')
    txt = md_text(at)
    assert 'Benchmark (analogues) :green-badge[Ready]' in txt, txt[:400]
    assert 'Onshore calculator :gray-badge[Needs facility type + capacity]' in txt
    assert 'last_results' not in at.session_state

    at.selectbox(key='facility_type').select('polypropylene')
    at.number_input(key='capacity').set_value(450.0)
    at.selectbox(key='cap_unit').select('KTA')
    at.run()
    ok(at, 'after facility')
    txt = md_text(at)
    assert 'Onshore calculator :green-badge[Ready]' in txt
    assert 'OSBL overlay (indirect) :green-badge[Ready]' in txt

    # Card: equipment (fragment, callbacks, merge on duplicate type)
    at.selectbox(key='eq_type').select('pump')
    at.number_input(key='eq_count').set_value(8)
    at.button(key='eq_add').click().run()
    ok(at, 'add equipment')
    at.selectbox(key='eq_type').select('pump')
    at.button(key='eq_add').click().run()
    assert at.session_state['equipment_items'] == [{'type': 'pump', 'count': 16}]
    at.selectbox(key='eq_type').select('exchanger')
    at.button(key='eq_add').click().run()
    at.button(key='eqrm_0').click().run()
    assert [e['type'] for e in at.session_state['equipment_items']] == ['exchanger']

    # Card: scope items
    at.text_input(key='si_facility').input('Utilities')
    at.button(key='si_add').click().run()
    assert at.session_state['scope_items'] == [{'type': 'process_unit', 'facility_type': 'Utilities'}]
    assert at.session_state['si_facility'] == ''

    # Run
    run_btn = [b for b in at.button if b.label == 'Run screening estimate']
    assert run_btn, 'Run button not found'
    run_btn[0].click()
    at.run()
    ok(at, 'after run')
    results = at.session_state['last_results']
    ens = results['ensemble']
    assert ens.get('best_estimate_musd'), ens
    fired = {m for m, r in results['models'].items() if r.get('can_fire')}
    assert {'Benchmark', 'Calculator_Onshore', 'OSBL_Estimate', 'EquipmentVector', 'Composite'} <= fired, fired
    metrics = [m.label for m in at.metric]
    assert 'Best estimate (P50)' in metrics and 'Confidence' in metrics, metrics
    assert not any('Inputs changed' in i.value for i in at.info), 'stale notice shown right after run'
    assert at.download_button, 'download button missing'

    # Changing an input after the run must show the stale notice
    at.number_input(key='capacity').set_value(600.0)
    at.run()
    ok(at, 'after changing capacity')
    assert any('Inputs changed' in i.value for i in at.info), 'stale notice missing'

    # Bid check
    at.number_input(key='bid_amt').set_value(float(ens['best_estimate_musd']))
    at.button(key='bid_check').click().run()
    ok(at, 'bid check')
    assert any('Within range' in s.value for s in at.success), [s.value for s in at.success]

    # Other pages render
    for page in ['app_pages/models.py', 'app_pages/data.py']:
        at.switch_page(page)
        at.run()
        ok(at, page)
    at.switch_page('app_pages/estimator.py')
    at.run()
    ok(at, 'back to estimator')
    assert at.session_state['last_results'] is results
    print(f"UI OK: P50=${ens['best_estimate_musd']:,.0f}M conf={ens['confidence']} fired={sorted(fired)}")


if __name__ == '__main__':
    main()
