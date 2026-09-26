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
ARCHETYPE_EXCLUSIONS = {
    # offshore_fpso: Benchmark exclusion REMOVED — cosine-similarity benchmark
    #   now finds relevant Guyana FPSO analogues (Hammerhead, Whiptail, Uaru etc.)
    # onshore_unconventional: Benchmark exclusion REMOVED — cosine benchmark
    #   can find relevant upstream peers when Unconventional model fails
    'refinery_bf':            ['Calculator_Onshore'],  # 7.0x overshoot on brownfield
    # 'lng_onshore':          ['Benchmark'],           # REMOVED — old pool-median was bad but cosine Benchmark finds good LNG analogues (Papua -15%)
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

_FACILITY_ALIASES = {
    'ethylene': 'ethylene_complex', 'cracker': 'ethylene_cracker',
    'pe': 'polyethylene', 'pp': 'polypropylene',
    'hdpe': 'polyethylene', 'ldpe': 'polyethylene', 'lldpe': 'polyethylene',
    'refinery': 'refinery_bf', 'crude_distillation': 'refinery_bf',
    'hdt': 'hydrotreater', 'carbon_capture': 'ccs',
    'hydrogen_plant': 'process_plant_generic',
    'crude_unit': 'refinery_bf',
    'gas_plant': 'gas_plant_cryo', 'cryogenic_plant': 'gas_plant_cryo',
    'central_delivery_point': 'gas_plant_cryo',
    'gas_compression_dehydration': 'gas_plant_cryo',
    'gas_central_delivery_point': 'gas_plant_cryo',
    'oil_central_delivery_point': 'process_plant_generic',
    # P4 additions: golden baseline coverage
    'onshore_process': 'process_plant_generic',
    'process_plant': 'process_plant_generic',
    'atmospheric_pipestill': 'refinery_bf',  # CDU = refinery core unit
    'fluid_cracking': 'refinery_bf',        # FCC = refinery core unit
    'hydrocracking': 'refinery_bf',         # HCU = refinery core unit
    'fcc': 'refinery_bf', 'fcc_cracker': 'refinery_bf',
    'coker': 'refinery_bf', 'delayed_coker': 'refinery_bf',
    'oil_sands_pad': 'oil_sands_mining', 'bitumen': 'oil_sands_mining',
    'meg': 'gas_to_chemical', 'mto': 'gas_to_chemical',
    'polyolefins': 'ethylene_complex',
    'gas_plant_fractionation': 'ngl_fractionation',
    'ngl_processing': 'ngl_fractionation',
    'cs_conversion': 'compressor_station_conversion',
}

# Unconventional model: scope_inputs facility_type -> pool facility_type
# source: ref_project_scope_inputs_v2.csv -> pool v3 onshore_unconventional
UNCONVENTIONAL_FACILITY_ALIASES = {
    'gas_compression_dehydration': 'central_delivery_point',
    'gas_central_delivery_point': 'central_delivery_point',
    'oil_central_delivery_point': 'central_delivery_point',
    'cdp': 'central_delivery_point',
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
    set(ISBL_CORRELATIONS) | set(_FACILITY_ALIASES)
    | set(UNCONVENTIONAL_FACILITY_ALIASES) | set(UNCONVENTIONAL_POOL_FACILITY_TYPES)
)

# TEC multipliers (ISBL -> TEC)
TEC_MULTIPLIERS = {
    'greenfield':   2.58,
    'brownfield':   1.30,
    'expansion':    2.61,
    'modification': 1.30,
}

# EMMA location index (from GP-10-30 4Q2025 and ref_cp30_combined_idx * 202)
# GOM 2000 = 202 (by definition). Factor = index / 202.
# source: onshore_calculator.py EMMA_LOCATION_INDEX (42 verified/estimated locations)
EMMA_LOCATION_INDEX = {
    # --- VERIFIED: CP-10-30 4Q2025 (EVM export) ---
    'GOM': 202, 'GOM 2000': 202, 'Strethcona': 486, 'Canada': 486,
    'Canada Alberta': 486, 'Strathcona': 486,
    'Illinois': 665, 'Belgium': 529, 'Antwerp': 529,
    'Singapore': 404, 'Australia': 513, 'Western Australia': 605,
    'Angola': 521, 'Qatar': 415,
    # --- ESTIMATED: ref_cp30_combined_idx * 202 (2025) ---
    'US Gulf Coast': 414, 'Texas': 414, 'Beaumont': 414,
    'Baytown': 413, 'Baton Rouge': 413, 'Louisiana': 418,
    'Texas-BMT': 414, 'Texas-BTN (GOM)': 413,
    'India': 264, 'China': 278, 'Shanghai': 278,
    'Netherlands': 415, 'Rotterdam': 415,
    'Nigeria': 389, 'Saudi Arabia': 323, 'Middle East': 323,
    'Mozambique': 366, 'UK': 456, 'United Kingdom': 456, 'Fawley': 456,
    # --- UNVERIFIED: estimated ---
    'North Sea': 435, 'Norway': 500,
    'US Midwest': 519, 'US West Coast': 550,
    'West Africa': 450, 'Guyana': 380,
    'Brazil': 400, 'Kazakhstan': 404,
    'New Mexico': 412, 'Persian': 412,
    'Equatorial Guinea': 450, 'Mexico': 380,
    'Alberta': 486, 'Joliet': 519,  # Illinois proxy
    'Papua New Guinea': 450,
    'Eastern Canada': 500,
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


# Archetype 2D taxonomy for analogue matching
_ARCHETYPE_TO_2D = {
    'offshore_fpso': ('offshore', 'grassroots'),
    'offshore_platform': ('offshore', 'grassroots'),
    'oil_sands': ('oil_sands', 'expansion'),
    'ccs_gas_processing': ('ccs', 'grassroots'),
    'ccs': ('ccs', 'grassroots'),
    'gas_processing': ('gas_processing', 'grassroots'),
    'lng_onshore': ('lng', 'grassroots'),
    'lng_terminal': ('lng', 'expansion'),
    'pipeline_mainline': ('pipeline', 'modification'),
    'pipeline_complex': ('pipeline', 'modification'),
    'pipeline_gathering': ('pipeline', 'modification'),
    'onshore_petchem': ('chemicals', 'grassroots'),
    'integrated_petchem': ('chemicals', 'grassroots'),
    'refinery_bf': ('refining', 'modification'),
    'refinery_gf': ('refining', 'grassroots'),
    'onshore_unconventional': ('upstream_unconventional', 'expansion'),
    'onshore_conventional': ('upstream_conventional', 'grassroots'),
    'renewable_diesel': ('refining', 'grassroots'),
    'power_generation': ('power', 'grassroots'),
}

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
