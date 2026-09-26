#!/usr/bin/env python3
"""Generate a synthetic data package for local development.

The real package (streamlit_poc_package_2026-09-16.zip) is confidential and is
NOT available in this repo. This script writes files with the same names, row
counts and column names that engine.py reads, filled with deterministic random
values (seed 42). Numbers are plausible orders of magnitude, nothing more.

    .venv/bin/python scripts/generate_mock_data.py [--out data]

Never use results computed on this data to make accuracy claims.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Archetype profiles (pool archetype name -> attributes)
# Pool archetype names follow ARCHETYPE_ALIASES_POOL in engine.py.
# ---------------------------------------------------------------------------
PROFILES = {
    # name: (n_rows, process_domain, app_archetype, log10 tec range, facility types, cap unit, cap range, countries)
    'refinery_bf':            (140, 'refining',  'refinery_bf',
                               (1.5, 3.2), ['hydrotreater', 'crude_unit', 'fcc', 'coker', 'hydrocracker', 'reformer', 'alkylation'],
                               'BPD', (10_000, 120_000), ['United States', 'Canada', 'United Kingdom', 'Belgium', 'Singapore', 'Australia']),
    'onshore_petchem':        (80,  'chemicals', 'onshore_petchem',
                               (2.4, 3.5), ['polypropylene', 'polyethylene', 'ethylene_cracker', 'meg', 'process_plant_generic'],
                               'KTA', (200, 2000), ['United States', 'China', 'Singapore', 'Saudi Arabia', 'Belgium', 'Canada']),
    'offshore_fpso':          (45,  'offshore',  'offshore_fpso',
                               (3.2, 3.95), ['fpso', 'fpso', 'platform'],
                               'KBPD', (60, 250), ['Guyana', 'Brazil', 'Nigeria', 'Angola', 'Norway', 'United States']),
    'pipeline_mainline':      (50,  'pipeline',  'pipeline_mainline',
                               (2.0, 3.4), ['pipeline', 'pipeline', 'pipeline_gathering'],
                               'km', (30, 900), ['United States', 'Canada', 'Mexico', 'Australia']),
    'onshore_unconventional': (30,  'upstream_unconventional', 'onshore_unconventional',
                               (1.3, 2.6), ['central_delivery_point', 'cold_separation_train', 'train_cryogenic',
                                            'cryo_gas_processing', 'pipeline', 'pad_facility'],
                               'MMSCFD', (40, 400), ['United States', 'United States', 'Canada']),
    'gas_processing':         (40,  'gas_processing', 'gas_processing',
                               (2.0, 3.2), ['gas_plant_cryo', 'ccs', 'ngl_fractionation', 'compressor_station'],
                               'MMSCFD', (100, 1200), ['United States', 'Qatar', 'Australia', 'Canada', 'Kazakhstan']),
    'lng_onshore':            (25,  'lng',       'lng_onshore',
                               (3.5, 4.3), ['lng_train', 'lng_terminal'],
                               'MTPA', (2, 15), ['Australia', 'Papua New Guinea', 'Mozambique', 'Qatar', 'United States']),
    'oil_sands':              (25,  'oil_sands', 'oil_sands',
                               (2.7, 3.7), ['oil_sands_mining', 'oil_sands_pad', 'bitumen'],
                               'KBPD', (20, 150), ['Canada']),
    'refinery_grassroot':     (20,  'refining',  'refinery_gf',
                               (3.3, 4.0), ['refinery', 'renewable_diesel'],
                               'BPD', (100_000, 400_000), ['Singapore', 'China', 'Saudi Arabia', 'India', 'United States']),
    'onshore_conventional':   (48,  'upstream_conventional', 'onshore_conventional',
                               (2.3, 3.5), ['onshore_process', 'gas_plant', 'compressor_station'],
                               'KBPD', (20, 200), ['Kazakhstan', 'Iraq', 'United States', 'Nigeria', 'Chad']),
}
assert sum(p[0] for p in PROFILES.values()) == 503

SCOPE_TYPES = ['grassroots', 'expansion', 'modification', 'debottleneck', 'replacement']
SCOPE_WEIGHTS = {
    'refinery_bf': [0.05, 0.25, 0.50, 0.15, 0.05],
    'onshore_petchem': [0.60, 0.30, 0.10, 0.0, 0.0],
    'offshore_fpso': [0.90, 0.10, 0.0, 0.0, 0.0],
    'pipeline_mainline': [0.40, 0.20, 0.30, 0.0, 0.10],
    'onshore_unconventional': [0.30, 0.50, 0.20, 0.0, 0.0],
    'gas_processing': [0.60, 0.25, 0.15, 0.0, 0.0],
    'lng_onshore': [0.70, 0.30, 0.0, 0.0, 0.0],
    'oil_sands': [0.30, 0.50, 0.20, 0.0, 0.0],
    'refinery_grassroot': [0.90, 0.10, 0.0, 0.0, 0.0],
    'onshore_conventional': [0.60, 0.30, 0.10, 0.0, 0.0],
}

COUNTRY_TO_CP30 = {
    'United States': 'Texas-BTN (GOM)', 'Canada': 'Alberta', 'United Kingdom': 'United Kingdom',
    'Belgium': 'Belgium', 'Singapore': 'Singapore', 'Australia': 'Perth', 'China': 'Shanghai',
    'Saudi Arabia': 'Saudi Arabia', 'Guyana': 'Guyana', 'Brazil': 'Brazil', 'Nigeria': 'Nigeria',
    'Angola': 'Angola', 'Norway': 'Norway', 'Mexico': 'Mexico', 'Qatar': 'Qatar',
    'Kazakhstan': 'Kazakhstan', 'Papua New Guinea': 'Papua New Guinea', 'Mozambique': 'Mozambique',
    'India': 'India', 'Iraq': 'Saudi Arabia', 'Chad': 'Nigeria',
}

# 52-dim equipment schema (must match engine.EQUIPMENT_TYPES_52)
from engine import EQUIPMENT_TYPES_52  # noqa: E402

EQUIP_PROFILES = {  # typical counts per archetype (mean); noise added
    'refinery_bf': {'pump': 30, 'exchanger': 25, 'tower': 4, 'drum': 8, 'heater': 2, 'reactor': 2,
                    'vessel': 6, 'compressor': 2, 'valve': 120, 'instrument': 300, 'filter': 3},
    'onshore_petchem': {'reactor': 4, 'compressor': 5, 'exchanger': 40, 'tower': 8, 'pump': 60,
                        'pelletizer': 2, 'silo': 12, 'drum': 12, 'vessel': 10, 'valve': 200, 'instrument': 500},
    'offshore_fpso': {'separator': 4, 'compressor': 3, 'pump': 10, 'exchanger': 8, 'vessel': 5,
                      'swivel': 1, 'turret': 1, 'mooring': 12, 'riser': 6, 'generator': 4, 'turbine': 4,
                      'subsea_tree': 10, 'manifold': 2, 'umbilical': 3, 'valve': 80},
    'pipeline_mainline': {'linepipe': 1, 'valve': 30, 'pig_launcher': 2, 'pump': 4, 'meter': 4, 'cp_system': 1},
    'onshore_unconventional': {'separator': 6, 'compressor': 3, 'pump': 8, 'tank': 6, 'heater': 2,
                               'wellhead': 12, 'exchanger': 3, 'valve': 40, 'instrument': 60},
    'gas_processing': {'compressor': 4, 'exchanger': 15, 'tower': 4, 'separator': 5, 'pump': 15,
                       'drum': 6, 'expander': 1, 'heater': 1, 'valve': 60, 'instrument': 150},
    'lng_onshore': {'compressor': 8, 'exchanger': 30, 'turbine': 6, 'tank': 3, 'loading_arm': 4,
                    'tower': 6, 'pump': 40, 'drum': 10, 'vessel': 8, 'valve': 300, 'instrument': 800},
    'oil_sands': {'haul_truck': 20, 'shovel': 4, 'crusher': 2, 'conveyor': 6, 'thickener': 2,
                  'pump': 40, 'exchanger': 10, 'tank': 8, 'boiler': 2, 'vessel': 6},
    'refinery_grassroot': {'pump': 200, 'exchanger': 180, 'tower': 25, 'drum': 50, 'heater': 12,
                           'reactor': 10, 'vessel': 40, 'compressor': 12, 'tank': 30, 'valve': 900, 'instrument': 2500},
    'onshore_conventional': {'separator': 8, 'compressor': 4, 'pump': 20, 'exchanger': 10, 'tank': 10,
                             'heater': 3, 'wellhead': 20, 'generator': 3, 'vessel': 6, 'valve': 60},
}

CHIP_NAMES = {
    'refining': ['Crude Unit Revamp', 'Hydrotreater', 'Hydrocracker Reactor', 'FCC Modernization',
                 'Delayed Coker', 'CCR Reformer', 'Alkylation Unit', 'Hydrogen Plant', 'Furnace Replacement',
                 'Utilities Package', 'Offsites and Tank Farm', 'Flare System', 'Desalter Upgrade'],
    'chemicals': ['Olefins Cracker', 'Polyethylene Unit', 'Polypropylene Unit', 'MEG Unit',
                  'Utilities Package', 'Offsites', 'Storage Tank Farm', 'Infrastructure', 'Product Loading'],
    'offshore': ['FPSO Topsides', 'FPSO Hull', 'SURF Flowlines', 'Risers', 'Subsea Trees', 'Drilling Wells',
                 'Mooring System', 'Umbilicals'],
    'pipeline': ['Export Pipeline', 'Gathering Pipeline', 'Pump Station', 'Metering Station', 'HDD Crossing'],
    'upstream_unconventional': ['Pad Facilities', 'Central Delivery Point', 'Compression Station',
                                'Gathering Pipeline', 'Water Handling'],
    'gas_processing': ['Cryogenic Gas Plant', 'Compression', 'Dehydration', 'NGL Fractionation',
                       'CO2 Capture Facilities', 'Injection Wells', 'Utilities'],
    'lng': ['Liquefaction Train', 'LNG Storage', 'Jetty and Loading', 'Power Plant', 'Utilities', 'Infrastructure'],
    'oil_sands': ['Mining OPP', 'Extraction', 'Tailings', 'Utilities', 'Infrastructure'],
    'upstream_conventional': ['Onsites Process', 'Compression', 'Injection', 'Infrastructure', 'Storage'],
}

CP30_LOCATIONS = {  # location -> 2024 combined index (GOM = 2.05, so idx*202 ~ EMMA table)
    'Texas-BTN (GOM)': 2.05, 'Texas-West (Permian)': 2.30, 'Louisiana': 2.07, 'Illinois': 3.29,
    'US West Coast': 2.72, 'US Midwest': 2.57, 'Alberta': 2.41, 'Eastern Canada': 2.48,
    'British Columbia': 2.60, 'United Kingdom': 2.26, 'Netherlands': 2.05, 'Belgium': 2.62,
    'Norway': 2.48, 'Shanghai': 1.38, 'Singapore': 2.00, 'India': 1.31, 'Perth': 2.54,
    'Qatar': 2.05, 'Saudi Arabia': 1.60, 'Nigeria': 1.93, 'Angola': 2.58, 'Mozambique': 1.81,
    'Guyana': 1.88, 'Brazil': 1.98, 'Mexico': 1.88, 'Kazakhstan': 2.00, 'Papua New Guinea': 2.23,
}
assert len(CP30_LOCATIONS) == 27
CP30_YEARS = list(range(2014, 2026))  # 12 years -> 324 rows


def pick(seq, n=None):
    return rng.choice(seq, size=n) if n else rng.choice(seq)


def gen_pool():
    rows = []
    pid = 1_000_000
    for pool_arch, (n, domain, app_arch, lt, fts, unit, caps, countries) in PROFILES.items():
        for i in range(n):
            pid += rng.integers(1, 40)
            scope = rng.choice(SCOPE_TYPES, p=SCOPE_WEIGHTS[pool_arch])
            log_tec = rng.uniform(*lt)
            if scope in ('modification', 'debottleneck', 'replacement'):
                log_tec -= 0.4
            tec = round(10 ** log_tec, 1)
            cap = float(rng.uniform(*caps))
            cap = round(cap, 0) if cap > 20 else round(cap, 1)
            country = rng.choice(countries)
            year = int(rng.integers(2010, 2024))
            rows.append({
                'planview_id': pid,
                'project_name': f'MOCK-{pool_arch.upper()[:6]}-{i+1:03d}',
                'archetype': pool_arch,
                'process_domain': domain,
                'scope_type': scope,
                'scope_type_confidence': rng.choice(['HIGH', 'HIGH', 'MEDIUM', 'LOW'], p=[0.5, 0.2, 0.2, 0.1]),
                'facility_type': rng.choice(fts),
                'primary_capacity': cap,
                'capacity_unit': unit,
                'country': country,
                'cp30_location': COUNTRY_TO_CP30[country],
                'greenfield_brownfield': 'greenfield' if scope == 'grassroots' else 'brownfield',
                'on_off_shore': 'offshore' if 'offshore' in pool_arch else 'onshore',
                'basis_year_original': year,
                'tec_musd_original': round(tec / (1.03 ** (2024 - year)), 1),
                'tec_musd_normalized_2024': tec,
                'cost_class': rng.choice(['Class 3', 'Class 4', 'Class 5']),
                'gate': rng.choice(['IC3', 'IC4', 'IC5']),
                'status': 'complete',
                'data_source': 'mock_generator',
                'n_equipment_items': None,  # filled from vectors
                'notes': 'synthetic row',
            })
    df = pd.DataFrame(rows)
    return df


def gen_truth(pool):
    # 52 distinct projects, one duplicated (53 rows) mirroring the real table
    sample = pool.sample(52, random_state=SEED)
    rows = []
    for _, r in sample.iterrows():
        noise = rng.normal(0, 0.18)
        rows.append({
            'planview_id': r.planview_id, 'project_name': r.project_name,
            'archetype': r.archetype, 'process_domain': r.process_domain, 'scope_type': r.scope_type,
            'country': r.country, 'location': r.cp30_location,
            'facility_type': r.facility_type, 'primary_capacity': r.primary_capacity,
            'capacity_unit': r.capacity_unit,
            'tec_musd_actual': round(r.tec_musd_normalized_2024 * (1 + noise), 1),
            'tec_musd_normalized_2024': round(r.tec_musd_normalized_2024 * (1 + noise), 1),
            'basis_year': 2024, 'truth_source': 'mock', 'verified': True,
        })
    rows.append(dict(rows[0], notes='duplicate row (phase 2)'))
    return pd.DataFrame(rows)


def gen_equipment_vectors(pool):
    rows = []
    idx = {t: i for i, t in enumerate(EQUIPMENT_TYPES_52)}
    # 593 rows: every pool project + 90 extra variants
    targets = list(pool.itertuples()) + list(pool.sample(90, random_state=SEED + 1).itertuples())
    for k, r in enumerate(targets):
        prof = EQUIP_PROFILES[r.archetype]
        scale = (r.tec_musd_normalized_2024 / 10 ** np.mean(PROFILES[r.archetype][3])) ** 0.5
        raw = np.zeros(52)
        for t, mean in prof.items():
            c = max(0, int(round(rng.normal(mean * scale, mean * scale * 0.35 + 0.5))))
            raw[idx[t]] = c
        total = int(raw.sum())
        norm = float(np.linalg.norm(raw))
        vec = (raw / norm) if norm > 0 else raw
        rows.append({
            'project_id': r.planview_id, 'project_name': r.project_name,
            'archetype': r.archetype, 'country': r.country,
            'tec_musd_2024': r.tec_musd_normalized_2024,
            'total_items': total, 'n_types': int((raw > 0).sum()),
            'vector_raw': json.dumps([int(x) for x in raw]),
            'vector_norm': json.dumps([round(float(x), 6) for x in vec]),
            'source': 'mock_generator' if k < len(pool) else 'mock_variant',
        })
    return pd.DataFrame(rows)


def gen_frankenstein(pool):
    projects = pool.sample(57, random_state=SEED + 2)
    rows = []
    chip_id = 0
    while len(rows) < 857:
        for _, p in projects.iterrows():
            if len(rows) >= 857:
                break
            names = CHIP_NAMES[p.process_domain]
            name = rng.choice(names)
            share = rng.uniform(0.03, 0.35)
            chip_id += 1
            rows.append({
                'chip_id': chip_id, 'planview_id': p.planview_id, 'project_name': p.project_name,
                'scope_name': name,
                'scope_type': rng.choice(['process_unit', 'osbl', 'pipeline_segment', 'storage', 'marine', 'infrastructure'],
                                         p=[0.45, 0.2, 0.1, 0.1, 0.05, 0.1]),
                'description': f'{name} scope chip for {p.facility_type} ({p.scope_type})',
                'direct_cost_kusd': round(p.tec_musd_normalized_2024 * share * 1000 * 0.6, 0),
                'indirect_cost_kusd': round(p.tec_musd_normalized_2024 * share * 1000 * 0.4, 0),
                'total_cost_kusd': round(p.tec_musd_normalized_2024 * share * 1000, 0),
                'capacity_value': p.primary_capacity, 'capacity_unit': p.capacity_unit,
                'country': p.country, 'basis_year': 2024,
            })
    return pd.DataFrame(rows)


def gen_gate_costs(pool):
    projects = pool.sample(58, random_state=SEED + 3)
    rows = []
    cost_types = ['equipment', 'bulk_material', 'labor', 'subcontract', 'engineering', 'owner', 'contingency']
    while len(rows) < 1687:
        for _, p in projects.iterrows():
            if len(rows) >= 1687:
                break
            rows.append({
                'planview_id': p.planview_id, 'project_name': p.project_name,
                'gate': rng.choice(['IC3', 'IC4', 'IC5']),
                'scope_chip': rng.choice(CHIP_NAMES[p.process_domain]),
                'cost_type': rng.choice(cost_types),
                'indirect_flag': bool(rng.random() < 0.3),
                'cost_kusd': round(p.tec_musd_normalized_2024 * rng.uniform(0.005, 0.08) * 1000, 0),
                'currency': 'USD', 'basis_year': int(rng.integers(2012, 2025)),
            })
    return pd.DataFrame(rows)


def gen_taxonomy():
    rows = [
        ('refining', 'grassroots', 'refinery_gf', 'New refinery'),
        ('refining', 'modification', 'refinery_bf', 'Refinery brownfield / unit modification'),
        ('refining', 'expansion', 'refinery_bf', 'Refinery expansion'),
        ('chemicals', 'grassroots', 'onshore_petchem', 'New petrochemical plant'),
        ('chemicals', 'expansion', 'onshore_petchem', 'Petrochemical expansion'),
        ('offshore', 'grassroots', 'offshore_fpso', 'FPSO / platform development'),
        ('pipeline', 'grassroots', 'pipeline_mainline', 'New mainline pipeline'),
        ('pipeline', 'modification', 'pipeline_mainline', 'Pipeline replacement / mod'),
        ('lng', 'grassroots', 'lng_onshore', 'LNG liquefaction'),
        ('lng', 'expansion', 'lng_terminal', 'LNG terminal expansion'),
        ('oil_sands', 'expansion', 'oil_sands', 'Oil sands mining / SAGD'),
        ('ccs', 'grassroots', 'ccs', 'Carbon capture and storage'),
        ('gas_processing', 'grassroots', 'gas_processing', 'Gas plant'),
        ('upstream_unconventional', 'expansion', 'onshore_unconventional', 'Short-cycle unconventional'),
        ('upstream_conventional', 'grassroots', 'onshore_conventional', 'Conventional onshore field'),
        ('power', 'grassroots', 'power_generation', 'Power generation'),
        ('refining', 'grassroots', 'renewable_diesel', 'Renewable diesel'),
    ]
    return pd.DataFrame(rows, columns=['process_domain', 'scope_type', 'archetype', 'description'])


def gen_cp30():
    rows = []
    for loc, idx24 in CP30_LOCATIONS.items():
        for y in CP30_YEARS:
            growth = 1.03 if y < 2021 else 1.05
            idx = idx24 / (growth ** (2024 - y)) if y <= 2024 else idx24 * 1.03
            rows.append({'location': loc, 'year': y,
                         'location_idx': round(idx24 / 2.05, 4),
                         'time_idx': round(idx / idx24, 4),
                         'combined_idx': round(idx, 4)})
    return pd.DataFrame(rows)


def gen_country_map():
    extra = {
        'USA': 'Texas-BTN (GOM)', 'US': 'Texas-BTN (GOM)', 'Trinidad and Tobago': 'Guyana',
        'Venezuela': 'Brazil', 'Argentina': 'Brazil', 'Colombia': 'Brazil', 'Peru': 'Brazil',
        'France': 'Netherlands', 'Germany': 'Netherlands', 'Italy': 'Netherlands', 'Spain': 'Netherlands',
        'Poland': 'Netherlands', 'Denmark': 'Norway', 'Sweden': 'Norway', 'Finland': 'Norway',
        'Russia': 'Kazakhstan', 'Azerbaijan': 'Kazakhstan', 'Turkmenistan': 'Kazakhstan',
        'Uzbekistan': 'Kazakhstan', 'Turkey': 'Saudi Arabia', 'Egypt': 'Saudi Arabia',
        'Algeria': 'Nigeria', 'Libya': 'Nigeria', 'Ghana': 'Nigeria', 'Cameroon': 'Nigeria',
        'Equatorial Guinea': 'Angola', 'Gabon': 'Angola', 'Congo': 'Angola', 'South Africa': 'Angola',
        'Tanzania': 'Mozambique', 'Kenya': 'Mozambique', 'UAE': 'Qatar', 'United Arab Emirates': 'Qatar',
        'Oman': 'Qatar', 'Kuwait': 'Saudi Arabia', 'Bahrain': 'Qatar', 'Iran': 'Saudi Arabia',
        'Pakistan': 'India', 'Bangladesh': 'India', 'Sri Lanka': 'India', 'Malaysia': 'Singapore',
        'Indonesia': 'Singapore', 'Thailand': 'Singapore', 'Vietnam': 'Singapore', 'Philippines': 'Singapore',
        'Japan': 'Shanghai', 'South Korea': 'Shanghai', 'Taiwan': 'Shanghai', 'New Zealand': 'Perth',
    }
    all_map = {**COUNTRY_TO_CP30, **extra}
    rows = [{'country': c, 'cp30_location': l, 'confidence': 'mock'} for c, l in all_map.items()]
    return pd.DataFrame(rows[:67])


def gen_scope_inputs(pool):
    s = pool.sample(60, random_state=SEED + 4)
    return pd.DataFrame({
        'planview_id': s.planview_id, 'project_name': s.project_name,
        'archetype': s.archetype, 'facility_type': s.facility_type,
        'capacity_value': s.primary_capacity, 'capacity_unit': s.capacity_unit,
        'scope_type': s.scope_type.map({'grassroots': 'GF', 'expansion': 'BF-expansion',
                                        'modification': 'BF-unit-mod', 'debottleneck': 'BF-unit-mod',
                                        'replacement': 'BF'}),
        'location': s.cp30_location, 'source': 'mock',
    })


def gen_semantic_chips(frank, pool):
    pool_to_app = {k: v[2] for k, v in PROFILES.items()}
    arch_by_pid = dict(zip(pool.planview_id, pool.archetype.map(pool_to_app)))
    return pd.DataFrame({
        'chip_id': frank.chip_id, 'planview_id': frank.planview_id,
        'archetype': frank.planview_id.map(arch_by_pid),
        'classification': frank.scope_type,
        'semantic_label': frank.scope_name.str.lower().str.replace(' ', '_'),
        'confidence': np.round(rng.uniform(0.6, 0.99, len(frank)), 2),
    })


GOLDEN_CASES = [
    # name, calculator, inputs, extra top-level
    ('MOCK_PP_450KTA_USGC', 'onshore', {'facility_type': 'polypropylene', 'capacity_value': 450,
                                        'capacity_unit': 'KTA', 'location': 'US Gulf Coast', 'scope_type': 'GF'}),
    ('MOCK_PE_800KTA_SG', 'onshore', {'facility_type': 'polyethylene', 'capacity_value': 800,
                                      'capacity_unit': 'KTA', 'location': 'Singapore', 'scope_type': 'GF'}),
    ('MOCK_HDT_40KBPD_MOD', 'onshore', {'facility_type': 'hydrotreater', 'capacity_value': 40000,
                                        'capacity_unit': 'BPD', 'location': 'US Gulf Coast', 'scope_type': 'BF-unit-mod'}),
    ('MOCK_CCS_2MTPA', 'onshore', {'facility_type': 'ccs', 'capacity_value': 2.0,
                                   'capacity_unit': 'MTPA_CO2', 'location': 'US Gulf Coast', 'scope_type': 'GF'}),
    ('MOCK_ETHYLENE_1800_EXP', 'onshore', {'facility_type': 'ethylene_cracker', 'capacity_value': 1800,
                                           'capacity_unit': 'KTA', 'location': 'Canada', 'scope_type': 'BF-expansion'}),
    ('MOCK_FPSO_150KBPD_GY', 'offshore', {'production_kboed': 150, 'hull_type': 'FPSO_newbuild',
                                          'water_depth_m': 1800, 'n_wells': 12, 'surf_km': 40,
                                          'fab_location': 'asian', 'location': 'Guyana', 'scope_type': 'GF'}, {'topsides_weight_mt': 25000}),
    ('MOCK_SEMI_80KBPD_GOM', 'offshore', {'production_kboed': 80, 'hull_type': 'semi_sub',
                                          'water_depth_m': 1400, 'n_wells': 8, 'surf_km': 25,
                                          'fab_location': 'gom', 'location': 'US Gulf Coast', 'scope_type': 'GF'}, {'topsides_weight_mt': 0}),
    ('MOCK_JACKET_30KBPD', 'offshore', {'production_kboed': 30, 'hull_type': 'jacket_shallow',
                                        'water_depth_m': 90, 'n_wells': 6, 'surf_km': 5,
                                        'fab_location': 'gom', 'location': 'US Gulf Coast', 'scope_type': 'GF'}, {'topsides_weight_mt': 6000}),
    ('MOCK_OIL_24IN_200KM', 'pipeline_v2', {'length_km': 200, 'od_inches': 24, 'service': 'oil',
                                            'congestion': 'moderate', 'grade': 'X70', 'location': 'US Gulf Coast', 'scope_type': 'GF'}),
    ('MOCK_GAS_36IN_600KM_AB', 'pipeline_v2', {'length_km': 600, 'od_inches': 36, 'service': 'gas',
                                               'congestion': 'low', 'num_hdd_crossings': 6, 'avg_hdd_length_m': 800,
                                               'location': 'Alberta', 'scope_type': 'GF'}),
    ('MOCK_GATHER_12IN_60KM', 'pipeline_v2', {'length_km': 60, 'od_inches': 12, 'service': 'gas',
                                              'congestion': 'unconventional', 'location': 'Texas-West (Permian)', 'scope_type': 'GF'}),
    ('MOCK_LNG_10MTPA_AU', 'lng', {'capacity_mtpa': 10, 'num_trains': 2, 'technology': 'APX',
                                   'location': 'Australia', 'scope_type': 'GF'}),
    ('MOCK_LNG_5MTPA_USGC', 'lng', {'capacity_mtpa': 5, 'num_trains': 1, 'technology': 'C3MR',
                                    'location': 'US Gulf Coast', 'scope_type': 'GF'}),
    ('MOCK_IC_POWER_100MVA', 'ic_library', {'electrical_load_mva': 100}),
]


def gen_golden(data_dir):
    """Snapshot of the CURRENT engine output for each case. This is a regression
    guard, NOT reference truth. Expected keys mirror test_golden_baseline.py."""
    import test_golden_baseline as tgb
    from engine import DataStore
    data = DataStore(data_dir)
    cases = []
    for entry in GOLDEN_CASES:
        name, calc, inputs = entry[0], entry[1], entry[2]
        extra = entry[3] if len(entry) > 3 else {}
        tc = {'name': name, 'calculator': calc, 'inputs': inputs, **extra}
        if calc in tgb._CALC_MAP:
            scope_fn, model_fn, key = tgb._CALC_MAP[calc]
            res = model_fn(scope_fn(name, tc), data)
            if res.get('can_fire'):
                tc[key] = res['estimate_musd']
            else:
                tc['no_fire_reason'] = res.get('no_fire_reason')
        cases.append(tc)
    return {
        '_note': ('MOCK golden baseline. Expected values are a snapshot of engine.py '
                  'output at generation time (regression guard), NOT the reference '
                  'cost_bot_api.py values. Regenerate with scripts/generate_mock_data.py '
                  'after an intentional model change.'),
        'generated_by': 'scripts/generate_mock_data.py', 'seed': SEED,
        'test_cases': cases,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'data'))
    args = ap.parse_args()
    out = args.out
    os.makedirs(os.path.join(out, 'extracted_files'), exist_ok=True)

    pool = gen_pool()
    vectors = gen_equipment_vectors(pool)
    n_items = vectors.drop_duplicates('project_id').set_index('project_id')['total_items']
    pool['n_equipment_items'] = pool['planview_id'].map(n_items)
    frank = gen_frankenstein(pool)

    tables = {
        'ref_are_analogue_pool_v3.csv': pool,
        'project_truth.csv': gen_truth(pool),
        'ref_equipment_vectors.csv': vectors,
        'frankenstein.csv': frank,
        'gate_costs.csv': gen_gate_costs(pool),
        'ref_archetype_taxonomy.csv': gen_taxonomy(),
        'ref_cp30_combined_indices.csv': gen_cp30(),
        'ref_country_to_cp30_location.csv': gen_country_map(),
        'ref_project_scope_inputs_v2.csv': gen_scope_inputs(pool),
        'ref_semantic_chip_classifications.csv': gen_semantic_chips(frank, pool),
    }
    for fn, df in tables.items():
        df.to_csv(os.path.join(out, fn), index=False)
        print(f'  {fn:45s} {len(df):>5d} rows x {df.shape[1]:>2d} cols')

    golden = gen_golden(out)
    with open(os.path.join(out, 'extracted_files', '_golden_baseline.json'), 'w') as f:
        json.dump(golden, f, indent=2)
    print(f"  {'extracted_files/_golden_baseline.json':45s} {len(golden['test_cases']):>5d} cases")


if __name__ == '__main__':
    main()
