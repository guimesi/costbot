# Developer shortcuts. Every target uses the project venv.
PY := .venv/bin/python
ST := .venv/bin/streamlit

.PHONY: install run test unit smoke ui golden mock screenshots evaluate lint

install:
	[ -d .venv ] || /opt/anaconda3/bin/python3.13 -m venv .venv
	.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt

run:
	$(ST) run app.py

test: unit smoke ui

unit:
	$(PY) -m pytest tests -q

golden:
	$(PY) tests/test_golden_baseline.py

smoke:
	$(PY) scripts/smoke_test.py

ui:
	$(PY) scripts/ui_test.py all

lint:
	$(PY) -m pyflakes costbot ui app_pages scripts tests app.py engine.py | grep -v 'imported but unused' || true

mock:
	$(PY) scripts/generate_mock_data.py

screenshots:
	$(PY) scripts/screenshot.py

evaluate:
	$(PY) scripts/evaluate_truth.py
