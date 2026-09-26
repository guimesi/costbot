"""HTML report: structure, escaping, and that it renders for every smoke scenario."""
import os
import sys
from html.parser import HTMLParser

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from costbot.data import DataStore  # noqa: E402
from costbot.report import generate_html_report  # noqa: E402
from costbot.screening import screen_project, model_rows  # noqa: E402


class _Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []
        self.void = {'meta', 'br', 'hr', 'img', 'input', 'line', 'rect', 'link'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.void:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'unbalanced </{tag}> (stack top {self.stack[-1] if self.stack else None})')
        else:
            self.stack.pop()


def _well_formed(html):
    c = _Checker()
    c.feed(html)
    return not c.errors and not c.stack, (c.errors, c.stack)


def test_report_without_data_package():
    res = screen_project({'archetype': 'onshore_petchem', 'location': 'US Gulf Coast', 'basis_year': 2024,
                          'facility_type': 'polypropylene', 'primary_capacity': 450, 'capacity_unit': 'KTA',
                          'scope_type': 'greenfield', 'project_name': 'Demo <b>PP</b> & co'},
                         DataStore('/nonexistent'))
    html = generate_html_report(res)
    ok, why = _well_formed(html)
    assert ok, why
    assert 'Demo &lt;b&gt;PP&lt;/b&gt; &amp; co' in html and '<b>PP</b>' not in html
    assert '<svg' in html and 'Onshore calculator' in html and 'OSBL overlay' in html
    assert 'Not fired' in html  # Benchmark could not fire without a pool
    assert '{_' not in html and '{ens' not in html  # no unformatted f-string leftovers


def test_report_for_every_smoke_scenario():
    data = DataStore()
    if data.pool.empty:
        pytest.skip('no data package')
    import smoke_test
    for title, scope, _ in smoke_test.SCENARIOS:
        res = screen_project(scope, data)
        html = generate_html_report(res)
        ok, why = _well_formed(html)
        assert ok, (title, why)
        for r in model_rows(res):
            assert r['role'] in html, (title, r)
        if res['ensemble'].get('best_estimate_musd'):
            assert f"P50 ${res['ensemble']['best_estimate_musd']:,.0f}M" in html, title


def test_report_shows_exclusion_and_component():
    data = DataStore()
    if data.pool.empty:
        pytest.skip('no data package')
    res = screen_project({'archetype': 'refinery_bf', 'location': 'US Gulf Coast', 'basis_year': 2024,
                          'facility_type': 'hydrotreater', 'primary_capacity': 40000, 'capacity_unit': 'BPD',
                          'scope_type': 'modification', 'greenfield_brownfield': 'modification'}, data)
    html = generate_html_report(res)
    assert 'Excluded for Refinery brownfield: Onshore calculator' in html
    assert 'class="status excluded"' in html
