#!/usr/bin/env python3
"""One-shot validation: environment, tests, golden baseline, accuracy on the
loaded data package. Writes validation_report.txt next to this repo's root.

    python scripts/validate.py

Safe to share the report: project names are redacted.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
REPORT = os.path.join(ROOT, 'validation_report.txt')

STEPS = [
    ('Unit tests + golden baseline (pytest)', [PY, '-m', 'pytest', 'tests', '-q', '-p', 'no:cacheprovider']),
    ('Golden baseline report', [PY, 'tests/test_golden_baseline.py']),
    ('Engine smoke test', [PY, 'scripts/smoke_test.py']),
    ('Accuracy vs project_truth (redacted)', [PY, 'scripts/evaluate_truth.py', '--redact']),
    ('Headless UI test', [PY, 'scripts/ui_test.py']),
]


def env_block():
    lines = [f"python {sys.version.split()[0]} ({PY})", f"platform {sys.platform}"]
    for mod in ('streamlit', 'pandas', 'numpy', 'sklearn', 'altair'):
        try:
            m = __import__(mod)
            lines.append(f"{mod} {getattr(m, '__version__', '?')}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"{mod} MISSING ({e})")
    sys.path.insert(0, ROOT)
    try:
        from costbot.data import DataStore
        d = DataStore()
        pool = d.pool
        mock = (not pool.empty and 'data_source' in pool.columns and (pool['data_source'] == 'mock_generator').all())
        lines.append(f"data dir {d.data_dir}")
        lines.append(f"pool rows {len(pool)} | truth rows {len(d.truth)} | equipment vectors {len(d.equipment_vectors)} "
                     f"| chips {len(d.frankenstein)} | cp30 rows {len(d.cp30)}")
        lines.append("DATA PACKAGE: " + ("MOCK (synthetic, numbers below mean nothing)" if mock else "not mock"))
        # Column names only (no values): needed to adapt evaluate_truth.py to the real schema
        for name, df in (('project_truth', d.truth), ('pool', pool), ('cp30', d.cp30),
                         ('equipment_vectors', d.equipment_vectors), ('frankenstein', d.frankenstein),
                         ('semantic_chips', d.semantic_chips)):
            lines.append(f"{name} columns: {list(df.columns)}")
        if not d.cp30.empty and 'year' in d.cp30.columns:
            lines.append(f"cp30 years: {sorted(d.cp30['year'].dropna().unique().tolist())}")
        try:
            import json
            with open(os.path.join(d.data_dir, 'extracted_files', '_golden_baseline.json')) as f:
                g = json.load(f)
            cases = g.get('test_cases', [])
            lines.append(f"golden cases: {len(cases)} | calculators: {sorted({c.get('calculator') for c in cases})} "
                         f"| keys of first case: {sorted(cases[0].keys()) if cases else []}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"golden file: {e}")
    except Exception as e:  # noqa: BLE001
        lines.append(f"data check failed: {e}")
    return '\n'.join(lines)


def run(label, cmd):
    t0 = time.time()
    try:
        env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900,
                           encoding='utf-8', errors='replace', env=env)
        out = (p.stdout + p.stderr)
        status = 'OK' if p.returncode == 0 else f'FAILED (exit {p.returncode})'
    except subprocess.TimeoutExpired:
        out, status = '', 'TIMEOUT'
    out = '\n'.join(l for l in out.splitlines() if 'ScriptRunContext' not in l and 'use_container_width' not in l)
    return status, out, time.time() - t0


def main():
    print(f"validation started, root {ROOT}")
    sections = [f"# costbot validation report\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n## Environment\n{env_block()}\n"]
    summary = []
    for label, cmd in STEPS:
        print(f"  running: {label} ...", end='', flush=True)
        status, out, dt = run(label, cmd)
        print(f" {status} ({dt:.0f}s)")
        summary.append(f"{status:22s} {label}")
        sections.append(f"## {label}\nstatus: {status}  ({dt:.0f}s)\ncommand: {' '.join(cmd[1:])}\n\n{out.strip()}\n")
    report = sections[0] + "\n## Summary\n" + '\n'.join(summary) + "\n\n" + '\n'.join(sections[1:])
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write(report)
    print('\n'.join(summary))
    print(f"\nreport written: {REPORT}  <- send this file back")


if __name__ == '__main__':
    main()
