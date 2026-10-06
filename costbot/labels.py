"""Presentation metadata shared by the Streamlit UI and the HTML report:
human labels, model one-line specs, badge/colour conventions.

Keep numbers here in sync with docs/; they are *reported* figures from the
reference evaluation, not something this engine has reproduced.
"""

MODEL_LABELS = {
    'Benchmark': 'Benchmark (analogues)',
    'EquipmentVector': 'Equipment vector',
    'Calculator_Onshore': 'Onshore calculator',
    'Calculator_Offshore': 'Offshore calculator',
    'Calculator_Pipeline': 'Pipeline calculator',
    'Calculator_LNG': 'LNG calculator',
    'Unconventional': 'Unconventional lookup',
    'Composite': 'Composite (scope chips)',
    'SURF_User': 'SURF subsea (component)',
    'OSBL_Estimate': 'OSBL overlay (indirect)',
}


def model_label(model_id: str) -> str:
    return MODEL_LABELS.get(model_id, model_id)


ARCHETYPE_LABELS = {
    'refinery_bf': 'Refinery brownfield',
    'refinery_gf': 'Refinery greenfield',
    'onshore_petchem': 'Petrochemical (onshore)',
    'integrated_petchem': 'Integrated petrochemical',
    'offshore_fpso': 'Offshore FPSO',
    'offshore_platform': 'Offshore platform',
    'pipeline_mainline': 'Pipeline (mainline)',
    'pipeline_gathering': 'Pipeline (gathering)',
    'pipeline_complex': 'Pipeline (complex)',
    'lng_onshore': 'LNG (onshore)',
    'lng_terminal': 'LNG terminal',
    'oil_sands': 'Oil sands',
    'onshore_conventional': 'Onshore conventional',
    'onshore_unconventional': 'Onshore unconventional',
    'ccs': 'Carbon capture (CCS)',
    'ccs_gas_processing': 'CCS / gas processing',
    'renewable_diesel': 'Renewable diesel',
    'gas_processing': 'Gas processing',
    'power_generation': 'Power generation',
}


def archetype_label(archetype: str) -> str:
    return ARCHETYPE_LABELS.get(archetype, archetype or '')


# (model_id, method, badge text, badge colour, algorithm, reported accuracy, libraries)
MODEL_SPECS = [
    ('Benchmark', 'Analogue matching', 'Broad', 'blue',
     "Two selectable variants. Reference: the port of analogue_estimator v3 (cosine over category features, "
     "an optional size bucket, min/max of the analogues as range). Engine variant: the first build's model, "
     "which filters the pool to a size band from a capacity heuristic or the size bucket and blends cosine "
     "and size 50/50.",
     "Real data, 2026-09-30 (52 projects, ensemble within ±30%): 29% with no size given, either variant; "
     "with the user's rough size 63% (engine variant) or 44% (reference).",
     "numpy, pandas, scikit-learn"),
    ('EquipmentVector', 'Equipment composition', 'Best broad model', 'green',
     "52-dimension vector of equipment counts, process equipment only (valves, instruments, electrical zeroed), "
     "L2-normalised cosine similarity against 593 project vectors, similarity-weighted top 5.",
     "66% within ±30% (N=29)", "numpy"),
    ('Calculator_Onshore', 'Six-tenths scaling', 'Calculator', 'blue',
     "ISBL from a capacity correlation (IC Library curve for a CDU, power-law tuples for 18 facility types, "
     "generic fallback otherwise), EMMA location index / 202, ISBL to TEC multiplier by scope type "
     "(GF 2.58, BF-expansion 2.61, BF-unit-mod 1.30), 6% escalation, no contingency, ±50% range.",
     "79% within ±30% (N=14). Excluded for refinery brownfield (7x overshoot).", "pure Python"),
    ('Calculator_Offshore', 'Topsides weight curves', 'Calculator', 'blue',
     "Topsides weight (given or from production rate) × $/t by hull type, parametric hull, subsea and SURF "
     "allowances, transport, engineering, owner's cost, 20% contingency. EMMA disabled on purpose.",
     "50% within ±30% (N=2)", "pure Python"),
    ('Calculator_Pipeline', 'Section decomposition', 'Unverified', 'orange',
     "Linepipe material, mainline construction by diameter, HDD crossings, MLV and pump stations, metering, "
     "engineering and survey, 20% contingency, location and congestion factors.",
     "67% within ±30% (N=3), truth values disputed between sources.", "pure Python"),
    ('Calculator_LNG', 'CET subsystem regressions', 'Miscalibrated', 'red',
     "Per-train material regressions for treating, liquefaction, power, offsites and marine, times a 3.1 "
     "loading factor and a location factor.",
     "0% within ±30%. Directional only; not in November scope.", "pure Python"),
    ('Unconventional', 'Facility-type lookup', 'Archetype-specific', 'blue',
     "Median TEC of pool projects with the same facility type (CDP, cold separation train, cryo plant, pad, "
     "pipeline). Authoritative for the unconventional archetype in the ensemble.",
     "70% within ±30% (N=10)", "numpy, pandas"),
    ('Composite', 'Scope chip matching', 'Low accuracy', 'gray',
     "Each scope item is matched against the 857-chip library with a 5-tier keyword and synonym scorer, "
     "IQR outliers removed, medians summed across items.",
     "26% within ±30% overall, 50% for refinery brownfield", "pandas"),
    ('SURF_User', 'Subsea bottom-up', 'Component', 'green',
     "Trees, flowlines, risers, manifolds and umbilicals at heritage unit prices × 1.34 calibration. "
     "Reported as a separate component, never added to the total.",
     "4 of 4 within ±30% on the Guyana deepwater set", "pure Python"),
    ('OSBL_Estimate', 'Indirect cost overlay', 'Automatic', 'green',
     "Three layers on top of an ISBL: heritage percentage by scope type, IC Library parametric sub-curves "
     "(power, steam, storage, loading) and an absolute cost chain, blended.",
     "8% average error (N=4)", "pure Python"),
]

ENSEMBLE_RULES = [
    "Only total-cost models enter the ensemble: component (SURF) and indirect (OSBL) estimates are shown "
    "beside it, never in the median.",
    "Spread gate: while the highest and lowest surviving estimates differ by more than 3x, the one furthest "
    "from the median is dropped (cost_bot_api rule; no model outranks another).",
    "Best estimate = median of the survivors. Range = lowest low to highest high of the survivors' own ranges, "
    "each bound clamped to within 5x of the median.",
    "Confidence: HIGH when 3 or more survivors sit within +/-30% of the median; MEDIUM-HIGH when 2 do; MEDIUM "
    "when 2 or more survive but disagree; LOW with a single model; COMPONENT_ONLY when only SURF fired.",
    "Projects below $20M are flagged as outside the screening floor.",
]

# Role of a model estimate in the ensemble, and the colour used for it in charts
ROLE_COLORS = {
    'In ensemble': '#1F3A5F',
    'Gated out': '#9AA5B1',
    'Component': '#2A9D8F',
    'Indirect overlay': '#E9A23B',
}

CONFIDENCE_COLORS = {
    'HIGH': '#1B7F4C', 'MEDIUM-HIGH': '#1B7F4C', 'MEDIUM': '#B86E00',
    'LOW': '#B42318', 'CANNOT_ESTIMATE': '#B42318', 'COMPONENT_ONLY': '#2A9D8F',
}
