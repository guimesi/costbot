"""engine.py: compatibility facade over the costbot package.

Every name that used to live here is re-exported so app.py, tests and
scripts keep importing from engine. New code should import from costbot.*
directly; see CLAUDE.md.
"""
# flake8: noqa: F401

from costbot.constants import (
    SPREAD_GATE_RATIO,
    SCREENING_FLOOR_MUSD,
    ARCHETYPE_MODELS,
    ARCHETYPE_EXCLUSIONS,
    EQUIPMENT_TYPES_52,
    EQ_TYPE_INDEX,
    EQUIPMENT_ALIASES,
    _PROCESS_EQUIPMENT,
    ISBL_CORRELATIONS,
    _FACILITY_ALIASES,
    UNCONVENTIONAL_FACILITY_ALIASES,
    UNCONVENTIONAL_POOL_FACILITY_TYPES,
    FACILITY_TYPE_OPTIONS,
    TEC_MULTIPLIERS,
    EMMA_LOCATION_INDEX,
    EMMA_LOCATION_FACTORS,
    CP30_LOCATION_MAP,
    LOCATION_TO_COUNTRY,
    LOCATION_OPTIONS,
    resolve_country,
    _ARCHETYPE_TO_2D,
    ARCHETYPE_ALIASES_POOL,
)
from costbot.data import (
    DATA_DIR,
    DataStore,
)
from costbot.escalation import (
    _get_cp30_index,
    _POOL_BASED_MODELS,
    _POOL_BASE_YEAR,
    _CP30_REF_LOCATION,
    _get_cp30_escalation_factor,
    _apply_cp30_escalation,
    _resolve_location,
    _get_emma_factor,
)
from costbot.models.calculator_onshore import (
    run_calculator_onshore,
    _convert_capacity,
)
from costbot.models.calculator_pipeline import (
    run_calculator_pipeline,
)
from costbot.models.calculator_lng import (
    run_calculator_lng,
)
from costbot.models.calculator_offshore import (
    run_calculator_offshore,
)
from costbot.models.benchmark import (
    run_benchmark,
)
from costbot.models.equipment_vector import (
    _resolve_equipment_type,
    _NON_PROCESS_ZERO,
    _build_equipment_vector,
    run_equipment_vector,
)
from costbot.models.unconventional import (
    run_unconventional,
)
from costbot.models.composite import (
    _SCOPE_SYNONYMS,
    _ARCHETYPE_ADJACENCY,
    _match_chip_score,
    _iqr_filter,
    run_composite,
)
from costbot.models.surf import (
    run_surf_user,
)
from costbot.models.osbl import (
    _HERITAGE_FACTORS,
    _DEFAULT_HERITAGE_FACTOR,
    _OSBL_RATIOS,
    _IC_SPILLOVER_COEFF,
    _IC_EQUIP_TO_INSTALLED,
    _IC_EQUIP_DEFAULT,
    _IC_SCOPE_MULTIPLIERS,
    _OSBL_COMPOSITION,
    _OSBL_COMPOSITION_DEFAULT,
    _ic_purchased_power,
    _ic_substation,
    _ic_feeder_cable,
    _ic_steam_bfw,
    _ic_spheres,
    _ic_product_loading,
    _ic_eval_power,
    _ic_eval_steam,
    _ic_eval_storage,
    _ic_eval_loading,
    _IC_SYSTEM_EVALUATORS,
    _derive_ic_defaults,
    _osbl_parametric,
    _osbl_absolute_chain,
    run_osbl_estimate,
)
from costbot.ensemble import (
    _assess_confidence,
)
from costbot.screening import (
    _MODEL_FN_MAP,
    MODEL_ORDER,
    model_readiness,
    model_rows,
    screen_project,
    _get_analogues,
    validate_bid,
)
from costbot.report import (
    generate_html_report,
)
