#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

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
STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS = ['qx', 'qy', 'qz', 'lx', 't0', 't1']
STREAMED_LOOKUP_TAIL_CONTROL_SLOTS = ['f_lookup_inf']


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


def build_streamed_lookup_tail_leaf(leaf: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    base_leaf = json.loads(json.dumps(leaf if leaf is not None else _base_leaf()))
    instructions = [
        {'pc': 0, 'op': 'load_input', 'dst': 'qx', 'src': 'Q.X', 'comment': 'Accumulator X enters the arithmetic register file.'},
        {'pc': 1, 'op': 'load_input', 'dst': 'qy', 'src': 'Q.Y', 'comment': 'Accumulator Y enters the arithmetic register file.'},
        {'pc': 2, 'op': 'load_input', 'dst': 'qz', 'src': 'Q.Z', 'comment': 'Accumulator Z enters the arithmetic register file.'},
        {'pc': 3, 'op': 'lookup_meta', 'dst': 'lookup_meta', 'src': {'table': 'T.meta', 'key': 'k'}, 'comment': 'Metadata bit0 marks the neutral lookup entry.'},
        {'pc': 4, 'op': 'bool_from_flag', 'dst': 'f_lookup_inf', 'src': {'flags': 'lookup_meta', 'bit': 0}, 'comment': 'Boundary no-op predicate for the k = 0 lookup entry.'},
        {'pc': 5, 'op': 'field_mul_lookup_x', 'dst': 't0', 'src': 'qx', 'comment': 'A = X1 * x2 using the streamed table x-coordinate.'},
        {'pc': 6, 'op': 'field_mul_lookup_x', 'dst': 'lx', 'src': 'qz', 'comment': 'x2Z1 using the streamed table x-coordinate.'},
        {'pc': 7, 'op': 'field_add', 'dst': 'lx', 'src': ['lx', 'qx'], 'comment': 'C input before 3b scaling: X1 + x2Z1.'},
        {'pc': 8, 'op': 'field_add', 'dst': 'qx', 'src': ['qx', 'qy'], 'comment': 'G = X1 + Y1.'},
        {'pc': 9, 'op': 'field_mul_lookup_sum', 'dst': 't1', 'src': 'qx', 'comment': 'H = (x2 + y2)(X1 + Y1) using streamed table constants.'},
        {'pc': 10, 'op': 'mul_const', 'dst': 'lx', 'src': 'lx', 'const': 21, 'comment': 'C = 3b(X1 + x2Z1).'},
        {'pc': 11, 'op': 'field_mul_lookup_y', 'dst': 'qx', 'src': 'qy', 'comment': 'I = Y1 * y2 using the streamed table y-coordinate.'},
        {'pc': 12, 'op': 'field_sub_sum', 'dst': 't1', 'src': ['t1', 't0', 'qx'], 'comment': 'K = H - A - I.'},
        {'pc': 13, 'op': 'field_triple', 'dst': 't0', 'src': 't0', 'comment': 'L = 3A.'},
        {
            'pc': 14,
            'op': 'complete_a0_streamed_tail',
            'dst': ['qx', 'qy', 'qz'],
            'src': {'c': 'lx', 'k': 't1', 'l': 't0', 'i': 'qx', 'y': 'qy', 'z': 'qz'},
            'comment': 'Multi-output streamed tail derives E, F, M, N internally and writes X3, Y3, Z3.',
        },
    ]
    return {
        key: value
        for key, value in {
            **base_leaf,
            'schema': 'compiler-project-streamed-lookup-tail-leaf-v1',
            'variant': 'a0_complete_mixed_streamed_lookup_tail_secp256k1',
            'arithmetic_slots': list(STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS),
            'lookup_interface_slots': ['lookup_meta'],
            'lookup_constant_sources': ['lookup_x', 'lookup_y', 'lookup_x_plus_y'],
            'lookup_infinity_policy': 'boundary_noop',
            'tail_macro': {
                'opcode': 'complete_a0_streamed_tail',
                'inputs': ['C', 'K', 'L', 'I', 'Y', 'Z'],
                'outputs': ['X3', 'Y3', 'Z3'],
                'non_clifford_lowering': 'one streamed yZ multiplication, one fixed 21Z multiplication, three internal add/sub kernels, six output multipliers, and three output add/sub kernels',
            },
            'instructions': instructions,
            'notes': [
                'This executable leaf contract keeps lookup x/y as table-fed constants consumed by arithmetic kernels rather than field-sized lookup output wires.',
                'The neutral lookup entry is a boundary no-op: the hot leaf is executed only for nonzero lookup entries, and the boundary keeps the accumulator unchanged for k = 0.',
                'The complete_a0_streamed_tail macro is a multi-output lowering of the complete-add tail from six live field values and is counted with all internal yZ, F, E/M/N, product, and output-combine work.',
            ],
        }.items()
    }


def execute_streamed_lookup_tail_leaf(
    leaf: Mapping[str, Any],
    p: int,
    q_proj: tuple[int, int, int],
    table_entry: Optional[tuple[int, int]],
    key: int,
) -> tuple[int, int, int]:
    if table_entry is None:
        return q_proj
    return exec_netlist(list(leaf['instructions']), p, q_proj, table_entry, key)


def execute_leaf_contract(
    leaf: Mapping[str, Any],
    p: int,
    q_proj: tuple[int, int, int],
    table_entry: Optional[tuple[int, int]],
    key: int,
) -> tuple[int, int, int]:
    if leaf.get('lookup_infinity_policy') == 'boundary_noop':
        return execute_streamed_lookup_tail_leaf(leaf, p, q_proj, table_entry, key)
    return exec_netlist(list(leaf['instructions']), p, q_proj, table_entry, key)


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
        observed = proj_to_affine(execute_leaf_contract(candidate_leaf, SECP_P, proj, lookup, 0 if lookup is None else 1), SECP_P)
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


def build_streamed_lookup_tail_leaf_equivalence(case_count: int = 80) -> Dict[str, Any]:
    return _build_leaf_equivalence(
        candidate_leaf=build_streamed_lookup_tail_leaf(_base_leaf()),
        schema='compiler-project-streamed-lookup-tail-leaf-equivalence-v1',
        case_count=case_count,
    )


__all__ = [
    'LOOKUP_FED_ARITHMETIC_SLOTS',
    'LOOKUP_FED_CONTROL_SLOTS',
    'LOOKUP_FED_LEAF_ORDER',
    'STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS',
    'STREAMED_LOOKUP_TAIL_CONTROL_SLOTS',
    'build_lookup_fed_leaf',
    'build_lookup_fed_leaf_equivalence',
    'build_streamed_lookup_tail_leaf',
    'build_streamed_lookup_tail_leaf_equivalence',
    'execute_leaf_contract',
    'execute_streamed_lookup_tail_leaf',
]
