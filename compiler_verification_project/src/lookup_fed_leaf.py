#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import (  # noqa: E402
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    affine_to_proj,
    deterministic_scalars,
    load_json,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_path,
)
from verifier import exec_netlist  # noqa: E402

LOOKUP_FED_LEAF_ORDER = (
    5,
    3,
    4,
    6,
    8,
    0,
    1,
    2,
    9,
    10,
    13,
    15,
    16,
    17,
    7,
    11,
    12,
    14,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    35,
    36,
)
LOOKUP_FED_ARITHMETIC_SLOTS = ['qx', 'qy', 'qz', 'lx', 'ly', 't0', 't1']
LOOKUP_FED_CONTROL_SLOTS = ['f_lookup_inf']


def _base_leaf() -> Dict[str, Any]:
    return load_json(PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json')


def build_lookup_fed_leaf(leaf: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    base_leaf = json.loads(json.dumps(leaf if leaf is not None else _base_leaf()))
    inst_map = {int(instruction['pc']): dict(instruction) for instruction in base_leaf['instructions']}
    instructions = []
    for new_pc, old_pc in enumerate(LOOKUP_FED_LEAF_ORDER):
        instruction = inst_map[old_pc]
        instruction['pc'] = new_pc
        if old_pc == 3:
            instruction['dst'] = 'lookup_x'
        elif old_pc == 4:
            instruction['dst'] = 'lookup_y'
        elif old_pc == 5:
            instruction['dst'] = 'lookup_meta'
        elif old_pc == 6:
            instruction['src'] = {'flags': 'lookup_meta', 'bit': 0}
        elif old_pc == 7:
            instruction['src'] = ['qx', 'lookup_x']
        elif old_pc == 8:
            instruction['src'] = ['lookup_x', 'lookup_y']
        elif old_pc == 9:
            instruction['src'] = ['lookup_x', 'qz']
        elif old_pc == 14:
            instruction['src'] = ['qy', 'lookup_y']
        elif old_pc == 15:
            instruction['src'] = ['lookup_y', 'qz']
        elif old_pc == 36:
            instruction['src'] = {'flags': 'lookup_meta', 'bit': 0}
        instructions.append(instruction)
    return {
        key: value
        for key, value in {
            **base_leaf,
            'schema': 'compiler-project-lookup-fed-leaf-v1',
            'arithmetic_slots': list(LOOKUP_FED_ARITHMETIC_SLOTS),
            'lookup_interface_slots': ['lookup_x', 'lookup_y', 'lookup_meta'],
            'instructions': instructions,
            'notes': [
                'This compiler-project leaf keeps the checked point-add semantics but pushes the initial lookup outputs onto an explicit lookup-fed interface.',
                'The leaf body is reordered under exact dependency constraints so the persistent arithmetic register file drops to seven field slots while the no-op control path keeps a single live control bit.',
            ],
        }.items()
    }


def build_lookup_fed_leaf_equivalence(case_count: int = 64) -> Dict[str, Any]:
    base_leaf = _base_leaf()
    lookup_fed_leaf = build_lookup_fed_leaf(base_leaf)
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    seed = bytes.fromhex(sha256_path(PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'))
    scalars = deterministic_scalars(seed + b'compiler-project-lookup-fed-leaf', case_count * 2, SECP_N)
    summary = {
        'total': 0,
        'pass': 0,
        'categories': {
            'random': {'total': 0, 'pass': 0},
            'accumulator_infinity': {'total': 0, 'pass': 0},
            'lookup_infinity': {'total': 0, 'pass': 0},
        },
    }
    for case_index in range(case_count):
        category = 'random'
        accumulator_scalar = scalars[2 * case_index]
        lookup_scalar = scalars[2 * case_index + 1]
        if case_index % 8 == 0:
            category = 'accumulator_infinity'
            accumulator_scalar = 0
        elif case_index % 8 == 1:
            category = 'lookup_infinity'
            lookup_scalar = 0
        accumulator = mul_fixed_window(accumulator_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(lookup_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        proj = affine_to_proj(accumulator, SECP_P)
        expected = proj_to_affine(exec_netlist(base_leaf['instructions'], SECP_P, proj, lookup, 0 if lookup is None else 1), SECP_P)
        observed = proj_to_affine(exec_netlist(lookup_fed_leaf['instructions'], SECP_P, proj, lookup, 0 if lookup is None else 1), SECP_P)
        passed = int(expected == observed)
        summary['total'] += 1
        summary['pass'] += passed
        summary['categories'][category]['total'] += 1
        summary['categories'][category]['pass'] += passed
    return {
        'schema': 'compiler-project-lookup-fed-leaf-equivalence-v1',
        'lookup_fed_leaf_order': list(LOOKUP_FED_LEAF_ORDER),
        'lookup_interface_slots': ['lookup_x', 'lookup_y', 'lookup_meta'],
        'summary': summary,
    }


__all__ = [
    'LOOKUP_FED_ARITHMETIC_SLOTS',
    'LOOKUP_FED_CONTROL_SLOTS',
    'LOOKUP_FED_LEAF_ORDER',
    'build_lookup_fed_leaf',
    'build_lookup_fed_leaf_equivalence',
]
