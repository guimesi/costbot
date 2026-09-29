"""Static tables shared by every model: routing, exclusions, equipment schema,
ISBL correlations, multipliers, EMMA/CP30 location maps, UI option lists."""
from typing import Dict, List, Optional, Any


SPREAD_GATE_RATIO = 3.0
SCREENING_FLOOR_MUSD = 20.0

# ============================================================================
# Archetype -> model routing (from cost_bot_api.py)
# ============================================================================
ARCHETYPE_MODELS = {
    'offshore_fpso':              ['Calculator_Offshore', 'Benchmark', 'SURF_User'],
    'offshore_platform':          ['Calculator_Offshore', 'Benchmark', 'SURF_User'],
    'lng_onshore':                ['Calculator_LNG', 'Benchmark'],
    'lng_offshore':               ['Calculator_LNG', 'Benchmark'],
    'lng_terminal':               ['Calculator_LNG', 'Benchmark'],
    'onshore_petchem':            ['Calculator_Onshore', 'Benchmark'],
    'integrated_petchem':         ['Calculator_Onshore', 'Benchmark'],
    'refinery_gf':                ['Calculator_Onshore', 'Benchmark'],
    'refinery_bf':                ['Calculator_Onshore', 'Benchmark'],
    'onshore_unconventional':     ['Calculator_Onshore', 'Unconventional', 'Benchmark'],
    'pipeline_mainline':          ['Calculator_Pipeline', 'Benchmark'],
    'pipeline_gathering':         ['Calculator_Pipeline', 'Benchmark'],
    'pipeline_complex':           ['Calculator_Pipeline', 'Benchmark'],
    'ccs':                        ['Calculator_Onshore', 'Benchmark'],
    'ccs_gas_processing':         ['Calculator_Onshore', 'Benchmark'],
    'oil_sands':                  ['Calculator_Onshore', 'Benchmark'],
    'onshore_conventional':       ['Calculator_Onshore', 'Benchmark'],
    'renewable_diesel':           ['Calculator_Onshore', 'Benchmark'],
    'gas_processing':             ['Calculator_Onshore', 'Benchmark'],
    'power_generation':           ['Calculator_Onshore', 'Benchmark'],
}

# Per-archetype model EXCLUSION rules (from cost_bot_api.py test review finding #3)
# Verbatim from cost_bot_api.py (reference, 2026-09-10). The first build had
# removed three of these; the real-data run of 2026-09-28 showed Benchmark
# alone underestimating FPSO and LNG by 60-98%, so the spec stands.
ARCHETYPE_EXCLUSIONS = {
    'offshore_fpso':          ['Benchmark'],            # ratio 0.058, returns pool median for mega-projects
    'refinery_bf':            ['Calculator_Onshore'],   # 7.0x overshoot on BF mods
    'onshore_unconventional': ['Benchmark'],            # anchored on wrong pool segment
    'lng_onshore':            ['Benchmark'],            # pool median meaningless for multi-billion LNG
}

# ============================================================================
# Equipment vector schema (52 dims)
# ============================================================================
EQUIPMENT_TYPES_52 = [
    'boiler', 'centrifuge', 'compressor', 'conveyor', 'cooler', 'cp_system',
    'crane', 'crusher', 'drum', 'excavator', 'exchanger', 'expander',
    'extractor', 'fan', 'filter', 'flowline', 'generator', 'haul_truck',
    'heater', 'instrument', 'jumper', 'linepipe', 'loading_arm', 'manifold',
    'meter', 'mooring', 'motor', 'panel', 'pelletizer', 'pig_launcher',
    'plet', 'pump', 'reactor', 'riser', 'screen', 'separator', 'shovel',
    'silo', 'subsea_tree', 'switchgear', 'swivel', 'tank', 'thickener',
    'tower', 'transformer', 'tree', 'turbine', 'turret', 'umbilical',
    'valve', 'vessel', 'wellhead'
]
EQ_TYPE_INDEX = {t: i for i, t in enumerate(EQUIPMENT_TYPES_52)}

EQUIPMENT_ALIASES = {
    'heat exchanger': 'exchanger', 'shell and tube': 'exchanger',
    'plate exchanger': 'exchanger', 'air cooler': 'cooler',
    'fin fan': 'cooler', 'fin fan cooler': 'cooler',
    'distillation column': 'tower', 'column': 'tower',
    'fractionator': 'tower', 'absorber': 'tower', 'stripper': 'tower',
    'scrubber': 'tower', 'pressure vessel': 'vessel',
    'knock-out drum': 'drum', 'ko drum': 'drum', 'flash drum': 'drum',
    'reflux drum': 'drum', 'storage tank': 'tank',
    'fired heater': 'heater', 'furnace': 'heater', 'reboiler': 'heater',
    'centrifugal pump': 'pump', 'reciprocating pump': 'pump',
    'gas turbine': 'turbine', 'steam turbine': 'turbine',
    'reciprocating compressor': 'compressor', 'centrifugal compressor': 'compressor',
    'control valve': 'valve', 'safety valve': 'valve',
    'flow meter': 'meter', 'level instrument': 'instrument',
    'transmitter': 'instrument', 'dcs': 'panel', 'control panel': 'panel',
    'mcc': 'switchgear', 'motor control center': 'switchgear',
    'power transformer': 'transformer', 'diesel generator': 'generator',
    'christmas tree': 'tree', 'xmas tree': 'tree',
    'subsea manifold': 'manifold', 'steel catenary riser': 'riser',
}

_PROCESS_EQUIPMENT = {
    'pump', 'exchanger', 'tower', 'drum', 'vessel', 'compressor',
    'heater', 'reactor', 'separator', 'tank', 'boiler', 'cooler',
    'turbine', 'generator', 'fan', 'motor', 'filter',
}

# ============================================================================
# ISBL Correlations (from onshore_calculator.py)
# ============================================================================
ISBL_CORRELATIONS = {
    'refinery_modification':   (264, 50000, 0.60, 'BPD'),
    'refinery_bf':             (264, 50000, 0.60, 'BPD'),
    'hydrotreater':            (80, 40000, 0.60, 'BPD'),
    'polypropylene':           (136, 450, 0.60, 'KTA'),
    'polyethylene':            (220, 625, 0.60, 'KTA'),
    'process_plant_generic':   (145.4, 500, 0.60, 'KTA'),
    'ethylene_complex':        (1305, 1800, 0.60, 'KTA'),
    'ethylene_cracker':        (1305, 1800, 0.60, 'KTA'),
    'chemical_expansion':      (474, 330, 0.60, 'KTA'),
    'ngl_fractionation':       (15.4, 50, 0.60, 'KBD_NGL'),
    'gas_to_chemical':         (1662, 3600, 0.60, 'KTA'),
    'renewable_diesel':        (65, 20000, 0.60, 'BPD'),
    'oil_sands_mining':        (1947, 110, 0.70, 'KBPD'),
    'ccs':                     (144.8, 2.0, 0.123, 'MTPA_CO2'),
    'ccs_gas_processing':      (144.8, 2.0, 0.123, 'MTPA_CO2'),
    'compressor_station':      (4.2, 70, 0.60, 'MMSCFD'),
    'gas_plant_cryo':          (31.7, 200, 0.60, 'MMSCFD'),
    'compressor_station_conversion': (2.9, 70, 0.30, 'MMSCFD'),
}

# Facility-type override applied by cost_bot_api before the calculator
# (FACILITY_TYPE_CORRELATION_MAP): pool / unconventional names -> correlation key.
FACILITY_TYPE_CORRELATION_MAP = {
    'central_delivery_point':          'gas_plant_cryo',
    'gas_central_delivery_point':      'gas_plant_cryo',
    'oil_central_delivery_point':      'process_plant_generic',
    'gas_compression_dehydration':     'gas_plant_cryo',
    'compressor_station':              'compressor_station',
    'cold_separation_train':           'compressor_station',
    'cryo_gas_processing':             'gas_plant_cryo',
    'train_conversion':                'compressor_station_conversion',
}

# Alias map verbatim from onshore_calculator.py. ORDER MATTERS: the reference
# falls back to a substring match over this dict (first hit wins), then over
# ISBL_CORRELATIONS, then to process_plant_generic. Do not reorder or "tidy".
_FACILITY_ALIASES = {
    'ethylene': 'ethylene_complex', 'cracker': 'ethylene_cracker',
    'pe': 'polyethylene', 'pp': 'polypropylene',
    'hdpe': 'polyethylene', 'ldpe': 'polyethylene', 'lldpe': 'polyethylene',
    'meg': 'gas_to_chemical', 'mto': 'gas_to_chemical',
    'refinery': 'refinery_bf', 'crude_distillation': 'refinery_bf',
    'hdt': 'hydrotreater', 'fcc_cracker': 'refinery_bf', 'coker': 'refinery_bf',
    'oil_sands_sagd': 'oil_sands_mining', 'bitumen': 'oil_sands_mining',
    'polyolefins': 'ethylene_complex', 'carbon_capture': 'ccs',
    'cdu': 'crude_distillation_unit',            # IC Library CDU curve (non-circular)
    'cdu_addition': 'crude_distillation_unit',
    'gas_plant_fractionation': 'ngl_fractionation',
    'ngl_processing': 'ngl_fractionation', 'debutanizer': 'ngl_fractionation',
    'gas_plant': 'gas_plant_cryo',
    'cryogenic_plant': 'gas_plant_cryo',
    'cs_conversion': 'compressor_station_conversion',
    'engine_to_motor': 'compressor_station_conversion',
    'electricification_conversion': 'compressor_station_conversion',
    'crude_unit': 'crude_distillation_unit',
}

# IC Library Rev 6.7 heritage curves (onshore_calculator.IC_LIBRARY_FORMULAS).
# Linear, per PROCESS UNIT (a single CDU, not a refinery project). GOM 2000 $M.
IC_LIBRARY_FORMULAS = {
    'crude_distillation_unit': {
        'a_slope': 0.0662, 'b_intercept': 3.3812, 'formula_type': 'linear',
        'valid_min': 50, 'valid_max': 500, 'capacity_unit': 'KBSD',
        'source': 'IC Library Rev 6.7, cell AA9 with input I8',
        'scope_note': 'ISBL for single CDU process unit only, NOT whole-refinery project. '
                      'CDU ISBL is typically 2-4% of total refinery project ISBL.',
    },
}

# Workbook anchors from the reference's 2026-08-01 heritage audit (documentation only).
_HERITAGE_CURVE_REFERENCES = {
    'crude_distillation': 'IC Library!AA9 with input IC Library!I8: (0.0662*Q + 3.3812)*1000 for 50<=Q<=500 kB/SD',
    'fcc_cracker': 'IC Library!AA726 and IC Library!AA728 (Fluid Cracking): separate reactor-volume and feed-rate curves; no single whole-unit tuple',
    'coker': 'IC Library!AA548, AA553, AA556, AA560, AA562, AA567, AA574, AA577 (Delayed Coking): multi-section model; no single whole-unit tuple',
    'hydrocracker': 'IC Library!I463/I466/I469 plus AA473/AA477/AA481 (Hydrocracking): user-entered reactor baseyear costs plus adjustments; no single whole-unit tuple',
    'hydrotreater': 'IC Library!BD1731:BD1745 with AA1708/AA1709 (Virgin Hydrotreating): lookup/piecewise unit curves, not a single tuple',
    'hydrogen_unit': 'IC Library!AA2451, AA2455, AA2457, AA2463, AA2465, AA2467, AA2472, AA2478, AA2479 (Hydrogen Plant): multi-section model',
    'sulfur_recovery': 'IC Selection!A147/C147/D147 shows On-Hold; no implemented IC Library curve block found in workbook',
    'gas_processing': 'Closest heritage match is IC Library 7-03-010 Gas Compression; no gas plant whole-facility tuple found',
    'gas_processing_ccs': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'lng_liquefaction': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'ngl_fractionation': 'Closest heritage matches are Light ends recovery / Pumpback Reflux Fractionator / Absorber-Deethanizers; no direct NGL fractionation tuple found',
    'ethylene_cracker': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'polyethylene': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'polypropylene': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'polyolefins': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'oil_sands_mining': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'oil_sands_sagd': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7',
    'carbon_capture': 'NOT FOUND IN IC Library Rev 6.7 or Onshore CET Rev 0.7 as a whole-facility curve; only Hydrogen Plant CO2-removal section exists',
    'co2_pipeline': 'Closest heritage match is IC Selection row 206 Offsite Piping / row 207 Cross Country Pipelines; no CO2-specific tuple found',
    'power_generation': 'IC Library rows 3005-3069 (Electrical Power - Generated): technology-specific multi-section model, not a single tuple',
    'water_treatment': 'Closest heritage match is IC Library rows 4131-4142 Waste Disposal - Secondary Treatment (Biological); multivariate, not a single tuple',
    'process_plant_generic': 'Generic screening placeholder only; not traceable to IC Library',
    'refinery_modification': 'Generic screening placeholder only; not traceable to IC Library',
}

# Circularity metadata per correlation (onshore_calculator.CALIBRATION_STATUS).
# Surfaced in the model detail so nobody quotes a back-solved N=1 tuple as accuracy.
CALIBRATION_STATUS = {
    'refinery_modification': {'N': 1, 'circular': True, 'source_project': 'Fawley FAST', 'note': 'Back-solved N=1, alias of refinery_bf'},
    'refinery_bf': {'N': 1, 'circular': True, 'source_project': 'Fawley FAST', 'note': 'Back-solved N=1'},
    'hydrotreater': {'N': 1, 'circular': True, 'source_project': 'SCANfiner', 'note': 'Back-solved N=1. IC Library has piecewise curves but coefficients not extracted.'},
    'polypropylene': {'N': 1, 'circular': True, 'source_project': 'NA PP Growth', 'note': 'Back-solved N=1. NOT FOUND in IC Library.'},
    'polyethylene': {'N': 1, 'circular': True, 'source_project': 'BPEX', 'note': 'Back-solved N=1. NOT FOUND in IC Library. Pool fit failed (all 3 ind. at 500 KTA).'},
    'process_plant_generic': {'N': 0, 'circular': False, 'source_project': 'None', 'note': 'DEPRECATED: Hand-tuned fallback with no traceable source. Prefer EquipmentVector for unknown facility types.'},
    'ethylene_complex': {'N': 1, 'circular': True, 'source_project': 'GCGV', 'note': 'Back-solved N=1. NOT FOUND in IC Library. Multi-product integrated complex.'},
    'ethylene_cracker': {'N': 1, 'circular': True, 'source_project': 'GCGV', 'note': 'Alias of ethylene_complex'},
    'chemical_expansion': {'N': 1, 'circular': True, 'source_project': 'BCEP', 'note': 'Back-solved N=1. KEEP: only model that fires well for BCEP (0.94x). EV also passes (0.87x).'},
    'ngl_fractionation': {'N': 1, 'circular': True, 'source_project': 'LEED', 'note': 'Back-solved N=1. EV provides backup (0.95x). Closest IC Library: light ends / absorber-deethanizers.'},
    'gas_to_chemical': {'N': 1, 'circular': True, 'source_project': 'MGV China1', 'note': 'Back-solved N=1. Calc_Onshore does not fire for MGV in eval. Composite(1.00x) and EV(0.78x) cover it.'},
    'renewable_diesel': {'N': 1, 'circular': True, 'source_project': 'SHRED', 'note': 'Back-solved N=1. KEEP: only accurate model (1.06x). EV fails (0.64x).'},
    'oil_sands_mining': {'N': 1, 'circular': True, 'source_project': 'Kearl ITAI', 'note': 'Back-solved N=1. NOT FOUND in IC Library. Not in current eval run.'},
    'ccs': {'N': 2, 'circular': True, 'source_project': 'Rose + LaBarge', 'note': 'N=2 but unit mismatch (MTPA vs MMSCFD). KEEP: only model that fires for Rose CCS (1.16x).'},
    'ccs_gas_processing': {'N': 2, 'circular': True, 'source_project': 'Rose + LaBarge', 'note': 'Alias of ccs'},
    'compressor_station': {'N': 1, 'circular': True, 'source_project': 'Cougar CS T3', 'note': 'Back-solved N=1. Unconventional also passes (1.00x) but equally circular.'},
    'gas_plant_cryo': {'N': 2, 'circular': True, 'source_project': 'Cowboy Cryo T1/T2', 'note': 'N=2 identical trains - effectively N=1. Unconventional (0.94x) also circular.'},
    'compressor_station_conversion': {'N': 2, 'circular': True, 'source_project': 'Maverick T1/T2', 'note': 'N=2 at same capacity. Unconventional also passes but equally circular.'},
    'crude_distillation_unit': {'N': 'multi-point', 'circular': False, 'source_project': 'IC Library Rev 6.7 (engineering curve)', 'note': 'INDEPENDENT. Linear formula for single CDU, not whole-refinery project.'},
}

# Unconventional model: scope_inputs facility_type -> pool facility_type
# source: ref_project_scope_inputs_v2.csv -> pool v3 onshore_unconventional
UNCONVENTIONAL_FACILITY_ALIASES = {
    'gas_compression_dehydration': 'central_delivery_point',
    'gas_central_delivery_point': 'central_delivery_point',
    'oil_central_delivery_point': 'central_delivery_point',
    'cdp': 'central_delivery_point',
    'gas_cdp': 'central_delivery_point',
    'oil_cdp': 'central_delivery_point',
    'compressor_station': 'cold_separation_train',             # CS Train -> cold separation train in pool
    'compressor_station_conversion': 'train_cryogenic',        # Maverick conversions
    'gas_plant_cryo': 'cryo_gas_processing',                  # Cowboy Cryo -> cryo in pool
    'pipeline_oil_gathering': 'pipeline',                      # PU1 420 pipeline in pool
    'pad': 'pad_facility',                                    # Pad -> Pad_facility in pool
}
UNCONVENTIONAL_POOL_FACILITY_TYPES = [
    'central_delivery_point', 'cold_separation_train', 'train_cryogenic',
    'cryo_gas_processing', 'pipeline', 'pad_facility',
]

# Every facility_type string some model understands. The UI builds its
# dropdown from this so a typo can no longer silently disable a calculator.
FACILITY_TYPE_OPTIONS = sorted(
    set(ISBL_CORRELATIONS) | set(_FACILITY_ALIASES) | set(IC_LIBRARY_FORMULAS)
    | set(FACILITY_TYPE_CORRELATION_MAP)
    | set(UNCONVENTIONAL_FACILITY_ALIASES) | set(UNCONVENTIONAL_POOL_FACILITY_TYPES)
)

# Capacity unit harmonisation (cost_bot_api.UNIT_FAMILIES). Units in the same
# family are comparable after scaling to the canonical unit; cross-family is not.
UNIT_FAMILIES = {
    'kbpd': ('oil_flow', 'KBPD', 1.0), 'kbopd': ('oil_flow', 'KBPD', 1.0), 'kbd': ('oil_flow', 'KBPD', 1.0),
    'bpd': ('oil_flow', 'KBPD', 0.001), 'mbpd': ('oil_flow', 'KBPD', 1.0),
    'mmscfd': ('gas_flow', 'MMSCFD', 1.0), 'mscfd': ('gas_flow', 'MMSCFD', 0.001), 'bcfd': ('gas_flow', 'MMSCFD', 1000.0),
    'mtpa': ('lng', 'MTPA', 1.0),
    'kta': ('mass_rate', 'KTA', 1.0), 'tpd': ('mass_rate', 'KTA', 0.365), 'ktpa': ('mass_rate', 'KTA', 1.0),
    'miles': ('pipeline_length', 'miles', 1.0), 'km': ('pipeline_length', 'miles', 0.621371),
    'mw': ('power', 'MW', 1.0), 'mw_h': ('power', 'MW', 1.0), 'mva': ('power', 'MW', 1.0),
    'inches': ('pipe_od', 'inches', 1.0), 'in': ('pipe_od', 'inches', 1.0),
    'wells': ('wells', 'wells', 1.0), 'beds': ('beds', 'beds', 1.0), 'units': ('units', 'units', 1.0),
    'acm/h': ('acm_h', 'ACM/H', 1.0), 'gpm': ('gpm', 'GPM', 1.0), 'kbbl': ('volume_kbbl', 'kbbl', 1.0),
    'kl': ('volume_kl', 'kL', 1.0),
}


def normalize_capacity(value, unit):
    """(value in canonical unit, canonical unit, family) or None (cost_bot_api._normalize_capacity)."""
    if value is None or unit is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value <= 0 or value != value:
        return None
    entry = UNIT_FAMILIES.get(str(unit).strip().lower().replace(' ', '_').replace('-', '_'))
    if entry is None:
        return None
    family, canonical, factor = entry
    return (value * factor, canonical, family)


def capacity_match_score(user_norm, analogue_value, analogue_unit) -> float:
    """max(0, 1 - |ln(analogue/user)|) within the same unit family, else 0 (cost_bot_api)."""
    import math
    if user_norm is None:
        return 0.0
    a = normalize_capacity(analogue_value, analogue_unit)
    if a is None or a[2] != user_norm[2] or user_norm[0] <= 0 or a[0] <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(math.log(a[0] / user_norm[0])))


# TEC multipliers (ISBL -> TEC), keys exactly as onshore_calculator.TEC_MULTIPLIERS.
# Anything else (e.g. the golden file's plain "BF") falls back to 2.58 in the
# reference (`TEC_MULTIPLIERS.get(scope_type, 2.58)`); the engine does the same.
# Calibrated on truth TEC that already includes contingency: never add contingency on top.
TEC_MULTIPLIERS = {
    'GF':           2.58,
    'BF-expansion': 2.61,
    'BF-unit-mod':  1.30,
}

# EMMA location index, CP-10-30 TEC composite, BASEYEAR (Baton Rouge 1977) = 100,
# GOM 2000 = 202. Factor = index / 202. Verbatim from onshore_calculator.py
# (VERIFIED 4Q2025 export, ESTIMATED from ref_cp30 * 202, UNVERIFIED estimates).
# ORDER MATTERS: the reference resolves an unknown location by the first key
# that is a substring of it (or vice versa); anything unmatched is 202 (factor 1.0),
# e.g. "Joliet" and "New Mexico". Keep the table as the reference has it.
EMMA_LOCATION_INDEX = {
    # --- VERIFIED: CP-10-30 4Q2025 (BVM export) ---
    'GOM': 202, 'GOM 2000': 202,
    'Canada Alberta': 486, 'Strathcona': 486, 'Canada': 486,
    'Illinois': 665, 'Belgium': 529, 'Antwerp': 529,
    'Singapore': 404, 'Australia': 513, 'Western Australia': 605,
    'Angola': 521, 'Qatar': 415,
    # --- ESTIMATED: ref_cp30_combined_indices combined_idx * 202 (2025) ---
    'US Gulf Coast': 414, 'Texas': 414, 'Beaumont': 414,
    'Baytown': 413, 'Baton Rouge': 413, 'Louisiana': 418,
    'India': 264, 'China': 278,
    'Netherlands': 415, 'Rotterdam': 415,
    'Nigeria': 389, 'Saudi Arabia': 323, 'Middle East': 323,
    'Mozambique': 366, 'UK': 456, 'Fawley': 456,
    # --- UNVERIFIED: no primary source ---
    'North Sea': 435, 'Norway': 500,
    'US Midwest': 519, 'US West Coast': 550,
    'West Africa': 450, 'Guyana': 380,
    'Brazil': 400, 'Kazakhstan': 404,
}

# Backward-compatible factor dict (index / 202)
EMMA_LOCATION_FACTORS = {k: v / 202.0 for k, v in EMMA_LOCATION_INDEX.items()}

# CP30 location aliases
CP30_LOCATION_MAP = {
    'usgc': 'Texas-BTN (GOM)', 'us gulf coast': 'Texas-BTN (GOM)',
    'usw': 'US West Coast', 'us west coast': 'US West Coast',
    'can': 'Alberta', 'canada': 'Alberta',
    'uk': 'United Kingdom', 'united kingdom': 'United Kingdom',
    'cn': 'Shanghai', 'china': 'Shanghai',
    'sg': 'Singapore', 'singapore': 'Singapore',
    'au': 'Perth', 'australia': 'Perth',
    'br': 'Brazil', 'brazil': 'Brazil',
    'gy': 'Guyana', 'guyana': 'Guyana',
    'ng': 'Nigeria', 'nigeria': 'Nigeria',
    'qa': 'Qatar', 'qatar': 'Qatar',
}

# UI location label -> country name (keys of _COUNTRY_REGION in run_benchmark).
# Benchmark encodes region from country; without this the app never sent a
# country and every estimate silently assumed north_america.
LOCATION_TO_COUNTRY = {
    'us gulf coast': 'United States', 'us west coast': 'United States',
    'us midwest': 'United States', 'new mexico': 'United States',
    'texas': 'United States', 'louisiana': 'United States',
    'texas-btn (gom)': 'United States', 'gom': 'United States',
    'canada': 'Canada', 'alberta': 'Canada', 'eastern canada': 'Canada',
    'united kingdom': 'United Kingdom', 'uk': 'United Kingdom',
    'china': 'China', 'shanghai': 'China',
    'singapore': 'Singapore', 'australia': 'Australia',
    'western australia': 'Australia', 'perth': 'Australia',
    'brazil': 'Brazil', 'guyana': 'Guyana', 'nigeria': 'Nigeria',
    'qatar': 'Qatar', 'mexico': 'Mexico', 'mozambique': 'Mozambique',
    'angola': 'Angola', 'norway': 'Norway', 'netherlands': 'Netherlands',
    'belgium': 'Belgium', 'india': 'India', 'saudi arabia': 'Saudi Arabia',
    'kazakhstan': 'Kazakhstan', 'papua new guinea': 'Papua New Guinea',
}


# Labels offered in the UI location dropdown. Each must resolve to a country.
LOCATION_OPTIONS = [
    'US Gulf Coast', 'US West Coast', 'US Midwest', 'New Mexico', 'Canada',
    'United Kingdom', 'Netherlands', 'Belgium', 'Norway', 'China', 'Singapore',
    'India', 'Australia', 'Saudi Arabia', 'Qatar', 'Nigeria', 'Angola',
    'Mozambique', 'Guyana', 'Brazil', 'Mexico', 'Kazakhstan', 'Papua New Guinea',
]
assert all(l.lower() in LOCATION_TO_COUNTRY for l in LOCATION_OPTIONS), 'LOCATION_OPTIONS out of sync'


def resolve_country(scope: Dict) -> str:
    """Country for region encoding: explicit scope['country'] wins, else derived
    from scope['location'] via LOCATION_TO_COUNTRY, else ''."""
    explicit = scope.get('country')
    if explicit:
        return str(explicit)
    loc = (scope.get('location') or '').lower().strip()
    return LOCATION_TO_COUNTRY.get(loc, '')


ARCHETYPE_ALIASES_POOL = {
    'offshore_fpso': 'offshore_fpso', 'offshore_platform': 'offshore_fpso',
    'oil_sands': 'oil_sands',
    'ccs_gas_processing': 'gas_processing', 'ccs': 'gas_processing',
    'gas_processing': 'gas_processing',
    'lng_onshore': 'lng_onshore', 'lng_terminal': 'lng_onshore',
    'pipeline_mainline': 'pipeline_mainline', 'pipeline_complex': 'pipeline_mainline',
    'pipeline_gathering': 'pipeline_mainline',
    'onshore_petchem': 'onshore_petchem', 'integrated_petchem': 'onshore_petchem',
    'refinery_bf': 'refinery_bf', 'refinery_gf': 'refinery_grassroot',
    'onshore_unconventional': 'onshore_unconventional',
    'onshore_conventional': 'onshore_conventional',
    'renewable_diesel': 'onshore_petchem',
    'power_generation': 'onshore_conventional',
}
