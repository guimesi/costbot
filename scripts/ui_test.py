#!/usr/bin/env python3
"""Headless UI test using streamlit.testing.v1.AppTest.

Runs app.py (st.navigation entry), fills DEMO_SCRIPT scenario 1 on the
estimator page, checks the live readiness list, exercises the list cards,
clicks Run, checks results and the stale notice, then renders every other
page and checks that nothing raised.

    .venv/bin/python scripts/ui_test.py            # current layout
    .venv/bin/python scripts/ui_test.py a          # Proposta A (or COSTBOT_UI=a)
    .venv/bin/python scripts/ui_test.py b          # Proposta B
    .venv/bin/python scripts/ui_test.py all        # every layout in turn

The three layouts share widget keys, so the same flow drives all of them;
only the readiness and result assertions differ per layout.
"""
import logging
import os
import sys

from streamlit.testing.v1 import AppTest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# AppTest runs outside a script thread; fragments log a harmless ScriptRunContext warning
logging.getLogger('streamlit.runtime.scriptrunner_utils.script_run_context').setLevel(logging.ERROR)
logging.getLogger('streamlit.runtime.state.session_state_proxy').setLevel(logging.ERROR)


def ok(at, where):
    assert not at.exception, f"{where}: {at.exception}"
    assert not at.error, f"{where}: {[e.value for e in at.error]}"


def md_text(at):
    return ' '.join(m.value for m in at.markdown)


def all_text(at):
    return md_text(at) + ' ' + ' '.join(c.value for c in at.caption)


def run_layout(ui: str) -> None:
    os.environ['COSTBOT_UI'] = ui
    at = AppTest.from_file(os.path.join(ROOT, 'app.py'), default_timeout=60)
    at.run()
    ok(at, 'first render')
    if ui == 'current':
        assert 'Model readiness' in md_text(at)
    elif ui == 'a':
        assert 'Models ready' in md_text(at)
    else:
        assert 'Scope' in all_text(at)

    # Core inputs -> live readiness without pressing Run
    at.selectbox(key='archetype').select('onshore_petchem')
    at.selectbox(key='location').select('US Gulf Coast')
    at.run()
    ok(at, 'after core inputs')
    txt = all_text(at)
    if ui == 'current':
        assert 'Benchmark (analogues) :green-badge[Ready]' in txt, txt[:400]
        assert 'Onshore calculator :gray-badge[Needs facility type + capacity]' in txt
    elif ui == 'a':
        assert ':green[●] Benchmark' in txt, txt[:600]
        assert 'Onshore calc · needs facility type + capacity' in txt, txt[:600]
    else:
        assert ':gray[○ Onshore calc]' in txt and '1 of 5 models ready' in txt, txt[:600]
    assert 'last_results' not in at.session_state

    at.selectbox(key='facility_type').select('polypropylene')
    at.number_input(key='capacity').set_value(450.0)
    at.selectbox(key='cap_unit').select('KTA')
    at.run()
    ok(at, 'after facility')
    txt = all_text(at)
    if ui == 'current':
        assert 'Onshore calculator :green-badge[Ready]' in txt
        assert 'OSBL overlay (indirect) :green-badge[Ready]' in txt
    elif ui == 'a':
        assert ':green[●] Onshore calc' in txt, txt[:600]
        assert ':green[●] OSBL overlay :gray[auto]' in txt, txt[:600]
    else:
        assert ':green[● Onshore calc]' in txt, txt[:600]

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
    at.button(key='run').click()
    at.run()
    ok(at, 'after run')
    results = at.session_state['last_results']
    ens = results['ensemble']
    assert ens.get('best_estimate_musd'), ens
    fired = {m for m, r in results['models'].items() if r.get('can_fire')}
    assert {'Benchmark', 'Calculator_Onshore', 'OSBL_Estimate', 'EquipmentVector', 'Composite'} <= fired, fired
    metrics = [m.label for m in at.metric]
    if ui == 'current':
        assert 'Best estimate (P50)' in metrics and 'Confidence' in metrics, metrics
    elif ui == 'a':
        assert 'Best estimate · P50' in metrics, metrics
        assert 'Range · P20 to P80' in all_text(at)
        assert 'Closest comparable projects' in md_text(at)
    else:
        assert any(m.startswith('P50 · TEC') for m in metrics), metrics
        assert 'How the models land' in md_text(at)
    assert not any('Inputs changed' in i.value for i in at.info), 'stale notice shown right after run'
    assert 'outdated' not in md_text(at)
    assert at.download_button, 'download button missing'

    # Changing an input after the run must show the stale state
    at.number_input(key='capacity').set_value(600.0)
    at.run()
    ok(at, 'after changing capacity')
    if ui == 'b':
        assert 'outdated' in md_text(at), 'stale badge missing'
    else:
        assert any('Inputs changed' in i.value for i in at.info), 'stale notice missing'

    # Bid check
    at.number_input(key='bid_amt').set_value(float(ens['best_estimate_musd']))
    if ui == 'b':
        at.run()  # live verdict, no button
        ok(at, 'bid check')
        assert 'Within range' in md_text(at), md_text(at)[-600:]
    else:
        at.button(key='bid_check').click().run()
        ok(at, 'bid check')
        assert any('Within range' in s.value for s in at.success), [s.value for s in at.success]

    # Other pages render
    for page in ['app_pages/models.py', 'app_pages/data.py']:
        at.switch_page(page)
        at.run()
        ok(at, page)
    at.switch_page({'current': 'app_pages/estimator.py', 'a': 'app_pages/estimator_a.py', 'b': 'app_pages/estimator_b.py'}[ui])
    at.run()
    ok(at, 'back to estimator')
    assert at.session_state['last_results'] is results

    # Reset clears inputs, lists and results
    at.button(key='reset_all').click().run()
    ok(at, 'after reset')
    assert 'last_results' not in at.session_state
    assert at.session_state['equipment_items'] == [] and at.session_state['scope_items'] == []
    assert at.selectbox(key='archetype').value is None
    assert at.selectbox(key='location').value is None
    assert any('Pick an archetype and a location' in c.value for c in at.caption)
    print(f"UI OK [{ui}]: P50=${ens['best_estimate_musd']:,.0f}M conf={ens['confidence']} fired={sorted(fired)}")


def main():
    arg = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('COSTBOT_UI', 'current')).strip().lower()
    layouts = ['current', 'a', 'b'] if arg == 'all' else [arg]
    for ui in layouts:
        run_layout(ui)


if __name__ == '__main__':
    main()
