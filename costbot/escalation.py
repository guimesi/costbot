"""CP30 time escalation and EMMA location factors."""
from typing import Dict, List, Optional, Any
import pandas as pd
from costbot.constants import CP30_LOCATION_MAP, EMMA_LOCATION_INDEX


def _get_cp30_index(cp30_df: pd.DataFrame, location: str, year: int) -> Optional[float]:
    """Look up combined_idx from the long-format CP30 table (location + year -> combined_idx)."""
    if cp30_df.empty or 'combined_idx' not in cp30_df.columns:
        return None
    # Match location (case-insensitive, substring fallback)
    loc_data = cp30_df[cp30_df['location'].str.lower() == location.lower()]
    if loc_data.empty:
        for loc_name in cp30_df['location'].unique():
            if location.lower() in loc_name.lower() or loc_name.lower() in location.lower():
                loc_data = cp30_df[cp30_df['location'] == loc_name]
                break
    if loc_data.empty:
        return None
    # Match year (exact, then closest)
    row = loc_data[loc_data['year'] == year]
    if row.empty:
        closest_year = loc_data.iloc[(loc_data['year'] - year).abs().argsort().iloc[0]]['year']
        row = loc_data[loc_data['year'] == closest_year]
    val = row.iloc[0].get('combined_idx')
    return float(val) if pd.notna(val) else None


# Pool-based models whose estimates are in 2024 USD and need time escalation
_POOL_BASED_MODELS = {'Benchmark', 'EquipmentVector', 'Unconventional', 'Composite'}
_POOL_BASE_YEAR = 2024
_CP30_REF_LOCATION = 'Texas-BTN (GOM)'


def _get_cp30_escalation_factor(cp30_df: pd.DataFrame, target_year: int,
                                base_year: int = _POOL_BASE_YEAR,
                                ref_location: str = _CP30_REF_LOCATION) -> float:
    """Return the multiplier to escalate costs from base_year to target_year
    using CP30 combined indices at the reference location (GOM).

    Pool costs are pre-normalized to GOM 2024 USD, so time escalation uses
    the GOM index ratio: idx(target) / idx(base).

    For years beyond the data range (e.g. 2026), extrapolates linearly from
    the last two available years.
    """
    if target_year == base_year:
        return 1.0
    if cp30_df.empty or 'combined_idx' not in cp30_df.columns:
        return 1.0

    idx_base = _get_cp30_index(cp30_df, ref_location, base_year)
    if not idx_base:
        return 1.0

    # Years covered for the reference location (exact match, then substring;
    # regex=False because the location name contains parentheses).
    loc_mask = cp30_df['location'].str.lower() == ref_location.lower()
    if not loc_mask.any():
        loc_mask = cp30_df['location'].str.contains(ref_location, case=False, na=False, regex=False)
    years = cp30_df.loc[loc_mask, 'year'].dropna()
    if years.empty:
        return 1.0
    max_year = int(years.max())

    if target_year <= max_year:
        idx_target = _get_cp30_index(cp30_df, ref_location, target_year)
        return idx_target / idx_base if idx_target else 1.0

    # Beyond the table: extrapolate with the last observed annual growth.
    # (_get_cp30_index would silently snap to the last year and flatten the
    # escalation, e.g. 2026 == 2025.)
    idx_prev = _get_cp30_index(cp30_df, ref_location, max_year - 1)
    idx_last = _get_cp30_index(cp30_df, ref_location, max_year)
    if idx_prev and idx_last and idx_prev > 0:
        annual_growth = idx_last / idx_prev
        idx_target = idx_last * (annual_growth ** (target_year - max_year))
        return idx_target / idx_base
    return idx_last / idx_base if idx_last else 1.0


def _apply_cp30_escalation(model_results: Dict, analogues: List,
                           escalation_factor: float, target_year: int) -> None:
    """Apply CP30 time escalation in-place to pool-based model estimates
    and analogue costs. Mutates dicts directly."""
    if abs(escalation_factor - 1.0) < 0.0001:
        return  # No escalation needed (target == base year)

    # Escalate pool-based model estimates
    for model_id, result in model_results.items():
        if model_id not in _POOL_BASED_MODELS:
            continue
        if not result.get('can_fire') or result.get('excluded_by_rule'):
            continue
        for key in ('estimate_musd', 'estimate_low_musd', 'estimate_high_musd'):
            if result.get(key):
                result[key] = round(result[key] * escalation_factor, 1)
        # Tag the result with escalation info
        result['escalated_to_year'] = target_year
        result['escalation_factor'] = round(escalation_factor, 4)
        # Escalate nested analogue/match costs
        for a in result.get('analogues', []) + result.get('top_matches', []):
            if a.get('tec_musd_2024'):
                a[f'tec_musd_{target_year}'] = round(a['tec_musd_2024'] * escalation_factor, 1)

    # Escalate top-level analogues
    for a in analogues:
        if a.get('tec_musd_2024'):
            a[f'tec_musd_{target_year}'] = round(a['tec_musd_2024'] * escalation_factor, 1)


def _resolve_location(location: str) -> str:
    if not location:
        return 'Texas-BTN (GOM)'
    key = location.lower().strip()
    return CP30_LOCATION_MAP.get(key, location)


def _get_emma_factor(location: str) -> float:
    """EMMA location adjustment factor (index / 202 = GOM 2000 basis)."""
    if not location:
        return 1.0
    loc_l = location.lower().strip()
    # Exact match
    for key, idx in EMMA_LOCATION_INDEX.items():
        if key.lower() == loc_l:
            return idx / 202.0
    # Substring match
    for key, idx in EMMA_LOCATION_INDEX.items():
        if key.lower() in loc_l or loc_l in key.lower():
            return idx / 202.0
    return 1.0
