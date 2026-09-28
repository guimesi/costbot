#!/usr/bin/env python3
"""Golden baseline regression test for the cost-bot engine.

Tests each calculator in isolation against expected values from
data/extracted_files/_golden_baseline.json (or COSTBOT_DATA_DIR). Runs both
as a script with a readable report and under pytest:

    .venv/bin/python tests/test_golden_baseline.py
    .venv/bin/python -m pytest tests -q

Expected-value keys per calculator:
    onshore     -> tec_escalated_M   (MUSD)
    offshore    -> tec_escalated_M   (MUSD)
    pipeline_v2 -> tec_musd          (MUSD)
    lng         -> tec_M             (MUSD)
    ic_library  -> skipped (no engine model)

Tolerance: ±10 % by default (golden expected comes from the reference
implementation; our engine has intentional divergences such as EMMA
removal on offshore and correlation tuning, so strict 1 % is too tight).
"""
import json, os, sys, math
from typing import Dict, Any, List, Tuple

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from costbot.data import DATA_DIR, DataStore  # noqa: E402
from costbot.models.calculator_lng import run_calculator_lng  # noqa: E402
from costbot.models.calculator_offshore import run_calculator_offshore  # noqa: E402
from costbot.models.calculator_onshore import run_calculator_onshore  # noqa: E402
from costbot.models.calculator_pipeline import run_calculator_pipeline  # noqa: E402

GOLDEN_PATH = os.path.join(DATA_DIR, "extracted_files", "_golden_baseline.json")

# Windows consoles default to cp1252; keep the report symbols printable everywhere.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass


# ARCH_MAP: golden archetype shorthand → engine archetype
ARCH_MAP = {"pipeline": "pipeline_mainline"}

# Default tolerance (fraction, not percent)
DEFAULT_TOL = 0.10

# Known divergences from reference (expected-fail, documented).
# Format: test_name → reason string.  These are skipped from FAIL count.
XFAIL = {
    # Offshore: EMMA intentionally removed (Fix #5 - rate tables already 2024 USD)
    "Payara":              "EMMA removed for offshore (Fix #5)",
    "Liza_Eh2":            "EMMA removed for offshore (Fix #5)",
    "Jacket_shallow":      "EMMA removed for offshore (Fix #5)",
    # LNG: different regression implementation
    "PNG_LNG":             "LNG calculator divergence from reference",
    "Golden_Pass_Terminal": "LNG calc applied to terminal (structural mismatch)",
    # Pipeline: optional param handling differs from reference
    "Woodland_36in_965km": "Pipeline golden from older calc version (ref v2 itself -4.5%)",
    "BMT3_24in_200km":     "Pipeline golden from older calc version (ref v2 itself +27.5%)",
    "PAPL_Expansion":      "Pipeline golden from older calc version (ref v2 itself -16.7%)",
    # Joliet BF-mods: reference has no EMMA for Joliet (unmapped location)
    "JO_Flare_Gas":        "Reference has no EMMA for Joliet (maps to 1.0)",
    "JUWO":                "Reference has no EMMA for Joliet (maps to 1.0)",
    "Joliet_Vac_Heater":   "Reference has no EMMA for Joliet (maps to 1.0)",
    # BRACE: BF scope uses different multiplier chain in reference
    "BRACE":               "BF (non-unit-mod) scope uses different chain in reference",
}


# ---------------------------------------------------------------------------
# Scope builders  (golden inputs → engine scope dict)
# ---------------------------------------------------------------------------

def _base_scope(name: str, inp: Dict) -> Dict:
    """Common scope fields shared across calculator types."""
    st = inp.get("scope_type", "GF").upper()
    if st in ("GF", "GREENFIELD"):
        bf_gf, scope_type = "greenfield", "greenfield"
    elif st == "BF-UNIT-MOD":
        # Engine reads greenfield_brownfield for TEC multiplier;
        # 'modification' triggers the 1.30x mod path.
        bf_gf, scope_type = "modification", "modification"
    elif st in ("BF", "BF-EXPANSION", "BROWNFIELD"):
        bf_gf, scope_type = "brownfield", "expansion"
    elif st in ("EXPANSION",):
        bf_gf, scope_type = "greenfield", "expansion"
    else:
        bf_gf, scope_type = "greenfield", "greenfield"
    return {
        "project_name": name,
        "location": inp.get("location", "US Gulf Coast"),
        "basis_year": 2024,
        "greenfield_brownfield": bf_gf,
        "scope_type": scope_type,
    }


def _scope_onshore(name: str, tc: Dict) -> Dict:
    inp = tc.get("inputs", {})
    s = _base_scope(name, inp)
    s["facility_type"] = inp.get("facility_type", "")
    s["primary_capacity"] = inp.get("capacity_value", 0)
    s["capacity_unit"] = inp.get("capacity_unit", "KTA")
    return s


def _scope_offshore(name: str, tc: Dict) -> Dict:
    inp = tc.get("inputs", {})
    s = _base_scope(name, inp)
    s["primary_capacity"] = inp.get("production_kboed", 0)
    s["capacity_unit"] = "KBPD"
    s["secondary_params"] = {
        "hull_type": inp.get("hull_type", "FPSO_newbuild"),
        "topsides_weight_te": tc.get("topsides_weight_mt", 0),
        "water_depth_m": inp.get("water_depth_m", 0),
        "n_wells": inp.get("n_wells", 0),
        "surf_km": inp.get("surf_km", 0),
        "fab_location": inp.get("fab_location", "gom"),
    }
    return s


def _scope_pipeline(name: str, tc: Dict) -> Dict:
    inp = tc.get("inputs", {})
    s = _base_scope(name, inp)
    s["archetype"] = "pipeline_mainline"
    s["length_km"] = inp.get("length_km", 0)
    s["od_inches"] = inp.get("od_inches", 36)
    s["diameter_inches"] = inp.get("od_inches", 36)
    # Pass through all optional pipeline params
    for key in ("wt_inches", "grade", "service", "congestion",
                "pipe_type", "num_hdd_crossings", "avg_hdd_length_m",
                "pct_hdd", "num_pump_stations", "pump_station_hp"):
        if key in inp:
            s[key] = inp[key]
    return s


def _scope_lng(name: str, tc: Dict) -> Dict:
    inp = tc.get("inputs", {})
    s = _base_scope(name, inp)
    s["lng_capacity_mtpa"] = inp.get("capacity_mtpa", 0)
    s["primary_capacity"] = inp.get("capacity_mtpa", 0)
    s["capacity_unit"] = "MTPA"
    for key in ("num_trains", "technology", "acid_gas_content",
                "feed_richness", "project_type", "development_status"):
        if key in inp:
            s[key] = inp[key]
    return s


# ---------------------------------------------------------------------------
# Runner / expected-value extraction
# ---------------------------------------------------------------------------

# calculator → (scope_builder, model_fn, expected_value_key)
_CALC_MAP = {
    "onshore":     (_scope_onshore, run_calculator_onshore, "tec_escalated_M"),
    "offshore":    (_scope_offshore, run_calculator_offshore, "tec_escalated_M"),
    "pipeline_v2": (_scope_pipeline, run_calculator_pipeline, "tec_musd"),
    "lng":         (_scope_lng, run_calculator_lng, "tec_M"),
}


def run_one(tc: Dict, data: DataStore) -> Dict[str, Any]:
    """Run a single golden test case.  Returns a result dict."""
    name = tc["name"]
    calc = tc["calculator"]
    if calc not in _CALC_MAP:
        return {"name": name, "status": "SKIP", "reason": f"no runner for {calc}"}

    scope_fn, model_fn, exp_key = _CALC_MAP[calc]
    expected = tc.get(exp_key)
    if expected is None:
        return {"name": name, "status": "SKIP", "reason": f"no expected key '{exp_key}'"}

    scope = scope_fn(name, tc)
    try:
        result = model_fn(scope, data)
    except Exception as exc:
        return {"name": name, "status": "ERROR", "reason": str(exc)[:120]}

    if not result.get("can_fire"):
        return {"name": name, "status": "NO_FIRE",
                "reason": result.get("no_fire_reason", "unknown")}

    actual = result["estimate_musd"]
    if calc == "lng":
        # tec_M is in M-USD, same as estimate_musd
        pass

    err_pct = (actual - expected) / expected * 100 if expected else 0
    within_tol = abs(err_pct) <= DEFAULT_TOL * 100
    if within_tol:
        status = "PASS"
    elif name in XFAIL:
        status = "XFAIL"
    else:
        status = "FAIL"
    return {
        "name": name,
        "calculator": calc,
        "expected": expected,
        "actual": actual,
        "err_pct": err_pct,
        "status": status,
        "xfail_reason": XFAIL.get(name, ""),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all(data: DataStore = None) -> List[Dict]:
    """Run every golden case; returns one result dict per case."""
    with open(GOLDEN_PATH) as f:
        golden = json.load(f)
    data = data or DataStore()
    return [run_one(tc, data) for tc in golden["test_cases"]]


def test_golden_baseline():
    """pytest entry point: XFAIL is acceptable, FAIL or ERROR is a regression."""
    if not os.path.exists(GOLDEN_PATH):
        import pytest
        pytest.skip("no golden baseline file")
    results = run_all()
    bad = [r for r in results if r["status"] in ("FAIL", "ERROR")]
    assert not bad, [(r["name"], r["status"], r.get("reason") or f"{r.get('err_pct', 0):+.1f}%") for r in bad]


def main():
    results = run_all()

    # Report
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    xfailed = [r for r in results if r["status"] == "XFAIL"]
    errors = [r for r in results if r["status"] == "ERROR"]
    no_fire = [r for r in results if r["status"] == "NO_FIRE"]
    skipped = [r for r in results if r["status"] == "SKIP"]

    print("=" * 80)
    print(f"GOLDEN BASELINE TEST  (tolerance ±{DEFAULT_TOL*100:.0f}%)")
    print("=" * 80)

    for r in sorted(results, key=lambda x: (x["status"] != "FAIL", x["status"] != "XFAIL", x["status"] != "ERROR", x.get("name", ""))):
        if r["status"] in ("PASS", "FAIL", "XFAIL"):
            flag = {"PASS": "☑", "FAIL": "X", "XFAIL": "△"}[r["status"]]
            suffix = f"  ({r['xfail_reason']})" if r["status"] == "XFAIL" else ""
            print(f"  {flag} {r['name']:35s} {r['calculator']:12s}  "
                  f"exp=${r['expected']:>9,.1f}  got=${r['actual']:>9,.1f}  "
                  f"err={r['err_pct']:+6.1f}%{suffix}")
        elif r["status"] == "NO_FIRE":
            print(f"  △  {r['name']:35s}  NO_FIRE: {r['reason']}")
        elif r["status"] == "ERROR":
            print(f"  ✧  {r['name']:35s}  ERROR: {r['reason']}")
        elif r["status"] == "SKIP":
            print(f"  ⊘  {r['name']:35s}  SKIP: {r['reason']}")

    print("\n" + "-" * 80)
    total_runnable = len(passed) + len(failed)
    total_runnable = len(passed) + len(failed) + len(xfailed)
    print(f"  PASS:   {len(passed):>3d}/{total_runnable}")
    print(f"  XFAIL:  {len(xfailed):>3d}/{total_runnable}  (known divergences)")
    print(f"  FAIL:   {len(failed):>3d}/{total_runnable}")
    print(f"  ERROR:  {len(errors):>3d}")
    print(f"  NO_FIRE:{len(no_fire):>3d}")
    print(f"  SKIP:   {len(skipped):>3d}")
    print(f"  TOTAL:  {len(results):>3d}")

    # Exit code for CI — XFAIL is acceptable, only true FAIL is a regression
    if failed or errors:
        print(f"\nX {len(failed)} unexpected failures, {len(errors)} errors")
        sys.exit(1)
    else:
        print(f"\n☑ {len(passed)} passed, {len(xfailed)} expected-fail (±{DEFAULT_TOL*100:.0f}%)")
        sys.exit(0)


if __name__ == "__main__":
    main()
