"""Ensemble rules: spread gate, priority, geometric blend, unconventional override, 5x cap, tiers."""
from typing import Dict, List, Optional, Any
import math
import numpy as np
from costbot.constants import SPREAD_GATE_RATIO


# ============================================================================
# Ensemble Confidence Assessment (from cost_bot_api.py)
# ============================================================================

def _assess_confidence(model_results: List[Dict], archetype: str = '', mode: str = 'api') -> Dict:
    """Spread-gated ensemble.

    mode='api' (default) reproduces cost_bot_api._assess_confidence exactly:
    remove the model furthest from the median until spread <= 3x, median of
    survivors, range from survivors' ranges clamped to [median/5, median*5].

    mode='engine' keeps the first build's variations: priority-aware removal
    (calculators outrank analogue models), Unconventional override for its
    archetype, geometric blend of Calculator_Onshore + Benchmark when >1.5x
    apart, and a symmetric 5x cap (high/low <= 5). Kept for evaluation only.
    """
    engine_mode = (mode == 'engine')
    fired = [m for m in model_results if m.get('can_fire')]
    if not fired:
        return {
            'confidence': 'CANNOT_ESTIMATE',
            'range_low_musd': None, 'range_high_musd': None,
            'best_estimate_musd': None,
            'models_fired': 0, 'models_included': [],
            'models_gated_out': [], 'spread_gated': False,
            'reasoning': 'No models could produce an estimate for this project.',
        }

    estimates_with_id = [(m['estimate_musd'], m.get('model_id', '?'))
                         for m in fired if m.get('estimate_musd')]
    if not estimates_with_id:
        return {
            'confidence': 'CANNOT_ESTIMATE',
            'range_low_musd': None, 'range_high_musd': None,
            'best_estimate_musd': None,
            'models_fired': len(fired), 'models_included': [],
            'models_gated_out': [], 'spread_gated': False,
            'reasoning': 'Models fired but no usable estimates produced.',
        }

    # --- Model priority (higher = more specific / input-driven) ---
    _CALC_MODELS = {'Calculator_Onshore', 'Calculator_Offshore', 'Calculator_Pipeline', 'Calculator_LNG'}
    def _priority(model_id):
        if archetype == 'onshore_unconventional' and model_id == 'Unconventional':
            return 5  # Purpose-built for this archetype
        if model_id in _CALC_MODELS:
            return 3  # Physics/capacity-driven
        if model_id == 'Unconventional':
            return 2
        return 1      # Benchmark, EquipmentVector, Composite

    survivors = list(estimates_with_id)
    gated_out = []
    while len(survivors) >= 2:
        vals = [s[0] for s in survivors]
        lo, hi = min(vals), max(vals)
        if hi / lo <= SPREAD_GATE_RATIO:
            break
        # Priority-aware removal: remove the LOWEST priority model first.
        # Among equal priority, remove the one furthest from median.
        med = float(np.median(vals))
        min_prio = min(_priority(s[1]) for s in survivors) if engine_mode else 0
        low_prio_idxs = ([i for i in range(len(survivors)) if _priority(survivors[i][1]) == min_prio]
                         if engine_mode else list(range(len(survivors))))
        if len(low_prio_idxs) < len(survivors):
            # Remove the lowest-priority model furthest from median
            worst_idx = max(low_prio_idxs, key=lambda i: abs(survivors[i][0] - med))
        else:
            # All same priority: fall back to furthest from median
            worst_idx = max(range(len(survivors)), key=lambda i: abs(survivors[i][0] - med))
        removed = survivors.pop(worst_idx)
        gated_out.append((removed[0], removed[1],
                          f"spread {hi/lo:.1f}x exceeds {SPREAD_GATE_RATIO:.0f}x gate"))

    # --- For unconventional archetype, prefer the Unconventional model estimate ---
    unconv_override = False
    if engine_mode and archetype == 'onshore_unconventional':
        unconv_est = [s for s in survivors if s[1] == 'Unconventional']
        if unconv_est:
            # Use Unconventional directly - it is the authoritative model
            survivors = unconv_est
            unconv_override = True

    # --- 2-model geometric mean: Calc_Onshore + Benchmark disagreement ---
    # When exactly 2 TEC models survive (Calculator_Onshore + Benchmark) and
    # they disagree by >1.5x, the arithmetic median is pulled by whichever is
    # larger. Geometric mean (log-space midpoint) is more robust - it penalizes
    # the outsized model. Validated: no regressions on GCGV, MGV, Strathcona,
    # NA PP where Calculator is correct. Fixes CRISP (311->218).
    if engine_mode and len(survivors) == 2 and not unconv_override:
        s_models = {s[1] for s in survivors}
        if 'Calculator_Onshore' in s_models and 'Benchmark' in s_models:
            s_vals = [s[0] for s in survivors]
            ratio_2m = max(s_vals) / min(s_vals)
            if ratio_2m > 1.5:
                geo = (s_vals[0] * s_vals[1]) ** 0.5
                survivors = [(geo, 'GeometricBlend')]

    included_ids = [s[1] for s in survivors]
    estimates = [s[0] for s in survivors]
    n = len(estimates)

    if n == 0:
        return {
            'confidence': 'CANNOT_ESTIMATE',
            'range_low_musd': None, 'range_high_musd': None,
            'best_estimate_musd': None,
            'models_fired': len(estimates_with_id),
            'models_gated_out': [(g[1], round(g[0], 1), g[2]) for g in gated_out],
            'spread_gated': True,
            'reasoning': 'All models gated out due to extreme spread.',
        }

    median_est = float(np.median(estimates))
    within_30 = sum(1 for e in estimates if abs(e / median_est - 1.0) <= 0.30)

    surviving_models = [m for m in fired if m.get('model_id') in included_ids and m.get('estimate_musd')]
    lows = [m.get('estimate_low_musd') for m in surviving_models if m.get('estimate_low_musd')]
    highs = [m.get('estimate_high_musd') for m in surviving_models if m.get('estimate_high_musd')]
    if lows and highs:
        range_low = min(lows)
        range_high = max(highs)
    else:
        range_low = median_est * 0.5
        range_high = median_est * 1.5

    range_capped = False
    if engine_mode:
        # first build: high/low ratio <= 5, symmetric in log-space around the median
        if range_low > 0 and range_high / range_low > 5.0:
            half_log = math.log(5.0) / 2.0
            range_low = median_est / math.exp(half_log)
            range_high = median_est * math.exp(half_log)
            range_capped = True
    elif median_est > 0:
        # cost_bot_api Fix 1: clamp each bound to median/5 .. median*5
        if range_low < median_est / 5.0:
            range_low, range_capped = median_est / 5.0, True
        if range_high > median_est * 5.0:
            range_high, range_capped = median_est * 5.0, True

    if unconv_override:
        tier = 'MEDIUM'
        reasoning = 'Unconventional model is authoritative for this archetype.'
    elif n >= 3 and within_30 >= 3:
        tier = 'HIGH'
        reasoning = f'{within_30} of {n} models agree within +/-30%.'
    elif n >= 2 and within_30 >= 2:
        tier = 'MEDIUM-HIGH'
        reasoning = f'{within_30} of {n} models agree within +/-30%.'
    elif n >= 2:
        tier = 'MEDIUM'
        reasoning = f'{n} models fired but spread exceeds 30%.'
    elif len(gated_out) > 0:
        tier = 'LOW'
        reasoning = f"1 model survives after spread gate (removed: {', '.join(g[1] for g in gated_out)})."
    else:
        tier = 'LOW'
        reasoning = f'Only {n} model(s) produced an estimate.'

    return {
        'confidence': tier,
        'range_low_musd': round(range_low, 1),
        'range_high_musd': round(range_high, 1),
        'best_estimate_musd': round(median_est, 1),
        'models_fired': len(estimates_with_id),
        'models_included': included_ids,
        'models_gated_out': [(g[1], round(g[0], 1), g[2]) for g in gated_out],
        'spread_gated': len(gated_out) > 0,
        'range_capped': range_capped,
        'models_agree_30pct': within_30,
        'reasoning': reasoning,
    }
