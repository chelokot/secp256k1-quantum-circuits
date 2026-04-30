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
INTERFACE_BORROWED_ARITHMETIC_SLOTS = ['qx', 'qy', 'qz', 'lx', 'ly', 't1']
INTERFACE_BORROWED_SCRATCH_SLOTS = ['lookup_x']


def _base_leaf() -> Dict[str, Any]:
    return load_json(PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json')


def _lookup_fed_instruction(old_pc: int, instruction: Dict[str, Any]) -> Dict[str, Any]:
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
    return instruction


def _replace_register(value: Any, old: str, new: str) -> Any:
    if value == old:
        return new
    if isinstance(value, list):
        return [new if item == old else item for item in value]
    return value


def _borrow_lookup_x_for_t0(instruction: Dict[str, Any]) -> Dict[str, Any]:
    if instruction.get('dst') == 't0':
        instruction['dst'] = 'lookup_x'
    if 'src' in instruction:
        instruction['src'] = _replace_register(instruction['src'], 't0', 'lookup_x')
    return instruction


def build_lookup_fed_leaf(leaf: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    base_leaf = json.loads(json.dumps(leaf if leaf is not None else _base_leaf()))
    inst_map = {int(instruction['pc']): dict(instruction) for instruction in base_leaf['instructions']}
    instructions = []
    for new_pc, old_pc in enumerate(LOOKUP_FED_LEAF_ORDER):
        instruction = inst_map[old_pc]
        instruction['pc'] = new_pc
        instructions.append(_lookup_fed_instruction(old_pc, instruction))
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


def build_interface_borrowed_leaf(leaf: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    borrowed = build_lookup_fed_leaf(leaf)
    instructions = []
    for instruction in borrowed['instructions']:
        instructions.append(_borrow_lookup_x_for_t0(dict(instruction)))
    return {
        **borrowed,
        'schema': 'compiler-project-interface-borrowed-leaf-v1',
        'arithmetic_slots': list(INTERFACE_BORROWED_ARITHMETIC_SLOTS),
        'borrowed_lookup_interface_slots': list(INTERFACE_BORROWED_SCRATCH_SLOTS),
        'instructions': instructions,
        'notes': [
            'This compiler-project leaf keeps the lookup-fed point-add semantics and borrows lookup_x as a scratch field slot after its final coordinate read.',
            'The borrowed lookup_x wire carries the two t0 live ranges, so the persistent arithmetic register file drops to six field slots without changing arithmetic or lookup non-Clifford counts.',
            'The contract is valid only when the lookup interface keeps lookup_x available until the point-add leaf releases it; the semantic and ZKP attestations execute that exact register reuse.',
        ],
        'interface_resource_contract': {
            'schema': 'compiler-project-interface-resource-contract-v1',
            'field_lanes': [
                {
                    'register': 'lookup_x',
                    'owner': 'lookup_workspace_qubits',
                    'role': 'borrowed_coordinate_lane',
                    'coordinate_last_use_pc': 14,
                    'scratch_first_write_pc': 14,
                    'scratch_last_use_pc': 35,
                    'counting_rule': 'same physical lookup-output lane; no additional arithmetic-field slot is allocated',
                },
                {
                    'register': 'lookup_y',
                    'owner': 'lookup_workspace_qubits',
                    'role': 'readonly_coordinate_lane',
                    'coordinate_last_use_pc': 17,
                    'scratch_first_write_pc': None,
                    'scratch_last_use_pc': None,
                    'counting_rule': 'lookup-output lane is read by the executable leaf and not reused as arithmetic scratch',
                },
            ],
        },
    }


def _equivalence_case_scalars(case_count: int) -> List[tuple[str, int, int]]:
    per_category = max(1, case_count // 5)
    seed = bytes.fromhex(sha256_path(PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'))
    scalars = deterministic_scalars(seed + b'compiler-project-leaf-interface-equivalence', per_category * 10, SECP_N)
    cases: List[tuple[str, int, int]] = []
    for case_index in range(per_category):
        random_a = scalars[2 * case_index]
        random_b = scalars[2 * case_index + 1]
        edge = scalars[2 * per_category + case_index]
        cases.append(('random', random_a, random_b))
        cases.append(('doubling', edge, edge))
        cases.append(('inverse', edge, (-edge) % SECP_N))
        cases.append(('accumulator_infinity', 0, random_b))
        cases.append(('lookup_infinity', random_a, 0))
    return cases


def _build_leaf_equivalence(candidate_leaf: Mapping[str, Any], schema: str, case_count: int) -> Dict[str, Any]:
    base_leaf = _base_leaf()
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    summary = {
        'total': 0,
        'pass': 0,
        'categories': {
            'random': {'total': 0, 'pass': 0},
            'doubling': {'total': 0, 'pass': 0},
            'inverse': {'total': 0, 'pass': 0},
            'accumulator_infinity': {'total': 0, 'pass': 0},
            'lookup_infinity': {'total': 0, 'pass': 0},
        },
    }
    for category, accumulator_scalar, lookup_scalar in _equivalence_case_scalars(case_count):
        accumulator = mul_fixed_window(accumulator_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(lookup_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        proj = affine_to_proj(accumulator, SECP_P)
        expected = proj_to_affine(exec_netlist(base_leaf['instructions'], SECP_P, proj, lookup, 0 if lookup is None else 1), SECP_P)
        observed = proj_to_affine(exec_netlist(candidate_leaf['instructions'], SECP_P, proj, lookup, 0 if lookup is None else 1), SECP_P)
        passed = int(expected == observed)
        summary['total'] += 1
        summary['pass'] += passed
        summary['categories'][category]['total'] += 1
        summary['categories'][category]['pass'] += passed
    return {
        'schema': schema,
        'lookup_fed_leaf_order': list(LOOKUP_FED_LEAF_ORDER),
        'lookup_interface_slots': list(candidate_leaf['lookup_interface_slots']),
        'arithmetic_slots': list(candidate_leaf['arithmetic_slots']),
        'summary': summary,
    }


def build_lookup_fed_leaf_equivalence(case_count: int = 80) -> Dict[str, Any]:
    return _build_leaf_equivalence(
        candidate_leaf=build_lookup_fed_leaf(_base_leaf()),
        schema='compiler-project-lookup-fed-leaf-equivalence-v2',
        case_count=case_count,
    )


def build_interface_borrowed_leaf_equivalence(case_count: int = 80) -> Dict[str, Any]:
    return _build_leaf_equivalence(
        candidate_leaf=build_interface_borrowed_leaf(_base_leaf()),
        schema='compiler-project-interface-borrowed-leaf-equivalence-v1',
        case_count=case_count,
    )


__all__ = [
    'LOOKUP_FED_ARITHMETIC_SLOTS',
    'LOOKUP_FED_CONTROL_SLOTS',
    'LOOKUP_FED_LEAF_ORDER',
    'INTERFACE_BORROWED_ARITHMETIC_SLOTS',
    'INTERFACE_BORROWED_SCRATCH_SLOTS',
    'build_interface_borrowed_leaf',
    'build_interface_borrowed_leaf_equivalence',
    'build_lookup_fed_leaf',
    'build_lookup_fed_leaf_equivalence',
]
