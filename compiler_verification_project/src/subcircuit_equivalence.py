#!/usr/bin/env python3

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping

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
    load_json,
    precompute_window_tables,
    mul_fixed_window,
    sha256_path,
)
from lookup_fed_leaf import (  # noqa: E402
    build_lookup_fed_leaf,
    build_lookup_fed_leaf_equivalence,
)
from lookup_lowering import lowered_lookup_semantic_summary  # noqa: E402
from verifier import exec_netlist_with_state_trace, make_audit_cases  # noqa: E402


LEAF_TRACE_SAMPLE_COUNTS = {
    'random': 32,
    'doubling': 16,
    'inverse': 16,
    'accumulator_infinity': 16,
    'lookup_infinity': 16,
}


def _leaf_path() -> Path:
    return PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'


def _cleanup_summary_path() -> Path:
    return PROJECT_ROOT / 'artifacts' / 'verification' / 'extended' / 'coherent_cleanup_summary.json'


def _selected_leaf_trace_cases() -> List[Dict[str, Any]]:
    cases = make_audit_cases(sha256_path(_leaf_path()))
    selected: List[Dict[str, Any]] = []
    per_category_index: Dict[str, int] = defaultdict(int)
    per_category_limit = dict(LEAF_TRACE_SAMPLE_COUNTS)
    for category, a_scalar, b_scalar in cases:
        if per_category_index[category] >= per_category_limit[category]:
            continue
        per_category_index[category] += 1
        selected.append(
            {
                'case_id': f'{category}_{per_category_index[category] - 1:03d}',
                'category': category,
                'a_scalar': int(a_scalar),
                'b_scalar': int(b_scalar),
            }
        )
        if all(per_category_index[name] == per_category_limit[name] for name in per_category_limit):
            break
    return selected


def _flag_bit(before: Mapping[str, Any], src: Mapping[str, Any]) -> int:
    return int((int(before[src['flags']]) >> int(src['bit'])) & 1)


def _expected_instruction_result(before: Mapping[str, Any], ins: Mapping[str, Any], p: int) -> int:
    opcode = str(ins['op'])
    if opcode == 'bool_from_flag':
        return _flag_bit(before, ins['src'])
    if opcode == 'clear_bool_from_flag':
        return int(before[ins['dst']]) ^ _flag_bit(before, ins['src'])
    if opcode == 'field_mul':
        left, right = ins['src']
        return (int(before[left]) * int(before[right])) % p
    if opcode == 'field_add':
        left, right = ins['src']
        return (int(before[left]) + int(before[right])) % p
    if opcode == 'field_sub':
        left, right = ins['src']
        return (int(before[left]) - int(before[right])) % p
    if opcode == 'mul_const':
        return (int(ins['const']) * int(before[ins['src']])) % p
    if opcode == 'select_field_if_flag':
        keep_src, update_src = ins['src']
        return int(before[keep_src]) if int(before[ins['flag']]) else int(before[update_src])
    raise KeyError(f'unsupported traced opcode: {opcode}')


def _bit_ripple_add(width: int, left: int, right: int) -> int:
    carry = 0
    out = 0
    for bit_index in range(width):
        left_bit = (left >> bit_index) & 1
        right_bit = (right >> bit_index) & 1
        sum_bit = left_bit ^ right_bit ^ carry
        carry = (left_bit & right_bit) | (left_bit & carry) | (right_bit & carry)
        out |= sum_bit << bit_index
    return out & ((1 << width) - 1)


def _bit_ripple_sub(width: int, left: int, right: int) -> int:
    borrow = 0
    out = 0
    for bit_index in range(width):
        left_bit = (left >> bit_index) & 1
        right_bit = (right >> bit_index) & 1
        diff_bit = left_bit ^ right_bit ^ borrow
        borrow = ((1 - left_bit) & (right_bit | borrow)) | (right_bit & borrow)
        out |= diff_bit << bit_index
    return out & ((1 << width) - 1)


def _bit_schoolbook_mul(width: int, left: int, right: int) -> int:
    mask = (1 << width) - 1
    accumulator = 0
    for bit_index in range(width):
        if (right >> bit_index) & 1:
            accumulator = (accumulator + ((left << bit_index) & mask)) & mask
    return accumulator


def _bit_select(old_value: int, new_value: int, flag: int) -> int:
    return old_value if flag else new_value


def _reduced_width_family_shape_witnesses() -> Dict[str, Any]:
    widths = [3, 4, 5, 6]
    rows = []
    for width in widths:
        mask = (1 << width) - 1
        add_total = 0
        add_pass = 0
        sub_total = 0
        sub_pass = 0
        mul_total = 0
        mul_pass = 0
        const_total = 0
        const_pass = 0
        select_total = 0
        select_pass = 0
        for left in range(1 << width):
            const_total += 1
            const_pass += int(_bit_schoolbook_mul(width, left, 21 & mask) == ((21 * left) & mask))
            for right in range(1 << width):
                add_total += 1
                add_pass += int(_bit_ripple_add(width, left, right) == ((left + right) & mask))
                sub_total += 1
                sub_pass += int(_bit_ripple_sub(width, left, right) == ((left - right) & mask))
                mul_total += 1
                mul_pass += int(_bit_schoolbook_mul(width, left, right) == ((left * right) & mask))
                for flag in (0, 1):
                    select_total += 1
                    select_pass += int(_bit_select(left, right, flag) == (left if flag else right))
        rows.append(
            {
                'field_bits': width,
                'field_add': {'total': add_total, 'pass': add_pass},
                'field_sub': {'total': sub_total, 'pass': sub_pass},
                'field_mul': {'total': mul_total, 'pass': mul_pass},
                'mul_const': {'total': const_total, 'pass': const_pass},
                'select_field_if_flag': {'total': select_total, 'pass': select_pass},
            }
        )
    return {
        'model': 'reduced-width ring witnesses over modulo-2^n arithmetic for the named adder, subtractor, multiplier, fixed-constant multiply, and select families',
        'widths': rows,
    }


def _arithmetic_opcode_equivalence(
    arithmetic_lowerings: Mapping[str, Any],
    leaf: Mapping[str, Any],
    leaf_source_artifact: str,
) -> Dict[str, Any]:
    selected_cases = _selected_leaf_trace_cases()
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    traced_opcodes = {
        'bool_from_flag',
        'clear_bool_from_flag',
        'field_mul',
        'field_add',
        'field_sub',
        'mul_const',
        'select_field_if_flag',
    }
    trace_pcs = {int(ins['pc']) for ins in leaf['instructions'] if ins['op'] in traced_opcodes}
    per_pc_stats: Dict[int, Dict[str, Any]] = {
        int(ins['pc']): {
            'pc': int(ins['pc']),
            'opcode': str(ins['op']),
            'dst': ins.get('dst'),
            'total': 0,
            'pass': 0,
        }
        for ins in leaf['instructions']
        if ins['op'] in traced_opcodes
    }
    per_opcode_stats: Dict[str, Dict[str, int]] = {
        opcode: {'total': 0, 'pass': 0}
        for opcode in traced_opcodes
    }
    cleanup_zero_total = 0
    cleanup_zero_pass = 0
    infinity_select_total = 0
    infinity_select_pass = 0
    bool_flag_one_cases = 0
    bool_flag_zero_cases = 0
    for case in selected_cases:
        accumulator = mul_fixed_window(case['a_scalar'], tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(case['b_scalar'], tables, SECP_P, SECP_B, width=8, order=SECP_N)
        key = 0 if lookup is None else 1
        _, trace = exec_netlist_with_state_trace(
            leaf['instructions'],
            SECP_P,
            affine_to_proj(accumulator, SECP_P),
            lookup,
            key,
            trace_pcs,
        )
        for pc, row in trace.items():
            instruction = row['instruction']
            before = row['before']
            after = row['after']
            opcode = str(instruction['op'])
            expected = _expected_instruction_result(before, instruction, SECP_P)
            passed = int(int(after[instruction['dst']]) == int(expected))
            per_pc_stats[pc]['total'] += 1
            per_pc_stats[pc]['pass'] += passed
            per_opcode_stats[opcode]['total'] += 1
            per_opcode_stats[opcode]['pass'] += passed
            if opcode == 'bool_from_flag':
                bool_flag_one_cases += int(expected == 1)
                bool_flag_zero_cases += int(expected == 0)
            if opcode == 'clear_bool_from_flag':
                cleanup_zero_total += 1
                cleanup_zero_pass += int(int(after[instruction['dst']]) == 0)
            if opcode == 'select_field_if_flag' and int(before[instruction['flag']]) == 1:
                infinity_select_total += 1
                keep_src = instruction['src'][0]
                infinity_select_pass += int(int(after[instruction['dst']]) == int(before[keep_src]))
    kernel_lookup = {row['opcode']: row for row in arithmetic_lowerings['kernels']}
    per_opcode = []
    for opcode in sorted(per_opcode_stats):
        stats = per_opcode_stats[opcode]
        kernel_row = kernel_lookup.get(opcode)
        per_opcode.append(
            {
                'opcode': opcode,
                'total': stats['total'],
                'pass': stats['pass'],
                'lowering_non_clifford_per_kernel': None if kernel_row is None else int(kernel_row['exact_non_clifford_per_kernel']),
            }
        )
    per_pc = [per_pc_stats[pc] for pc in sorted(per_pc_stats)]
    return {
        'leaf_source_artifact': leaf_source_artifact,
        'case_suite': {
            'total': len(selected_cases),
            'per_category': {name: int(limit) for name, limit in LEAF_TRACE_SAMPLE_COUNTS.items()},
        },
        'per_pc': per_pc,
        'per_opcode': per_opcode,
        'cleanup_zero_after_clear': {
            'total': cleanup_zero_total,
            'pass': cleanup_zero_pass,
        },
        'infinity_select_keeps_original_accumulator': {
            'total': infinity_select_total,
            'pass': infinity_select_pass,
        },
        'bool_flag_value_partition': {
            'flag_one_cases': bool_flag_one_cases,
            'flag_zero_cases': bool_flag_zero_cases,
        },
        'reduced_width_family_shape_witnesses': _reduced_width_family_shape_witnesses(),
        'notes': [
            'These traces check the ISA-level arithmetic and flag-manipulation opcodes directly on deterministic secp256k1 basis-state leaf cases.',
            'The reduced-width witness section validates the family shape of the arithmetic kernels on exhaustive modulo-2^n instances; it is an internal family-shape check, not a 256-bit prime-field micro-expansion proof.',
        ],
    }


def _lookup_family_equivalence(lookup_lowerings: Mapping[str, Any]) -> Dict[str, Any]:
    semantic_summary = lowered_lookup_semantic_summary()
    semantic_lookup = {row['name']: row for row in semantic_summary['families']}
    families = []
    for family in lookup_lowerings['families']:
        semantic_row = semantic_lookup[family['name']]
        stage_non_clifford = sum(int(stage['non_clifford_total']) for stage in family['stages'])
        stage_workspace = max(int(stage['total_workspace_qubits']) for stage in family['stages'])
        families.append(
            {
                'name': family['name'],
                'direct_lookup_non_clifford': int(family['direct_lookup_non_clifford']),
                'stage_reconstructed_non_clifford': stage_non_clifford,
                'workspace_qubits': int(family['extra_lookup_workspace_qubits']),
                'stage_reconstructed_workspace_qubits': stage_workspace,
                'canonical_full_exhaustive_total': int(semantic_row['canonical_full_exhaustive_total']),
                'canonical_full_exhaustive_pass': int(semantic_row['canonical_full_exhaustive_pass']),
                'multibase_edge_total': int(semantic_row['multibase_edge_total']),
                'multibase_edge_pass': int(semantic_row['multibase_edge_pass']),
            }
        )
    return {
        'lookup_contract_sha256': semantic_summary['lookup_contract_sha256'],
        'families': families,
    }


def _cleanup_window_equivalence(arithmetic_trace: Mapping[str, Any], leaf: Mapping[str, Any], leaf_source_artifact: str) -> Dict[str, Any]:
    cleanup_summary = load_json(_cleanup_summary_path())
    per_pc = {int(row['pc']): row for row in arithmetic_trace['per_pc']}
    extract_pc = next(int(ins['pc']) for ins in leaf['instructions'] if ins['op'] == 'bool_from_flag')
    clear_pc = next(int(ins['pc']) for ins in leaf['instructions'] if ins['op'] == 'clear_bool_from_flag')
    select_pcs = [int(ins['pc']) for ins in leaf['instructions'] if ins['op'] == 'select_field_if_flag']
    return {
        'leaf_source_artifact': leaf_source_artifact,
        'cleanup_summary_path': 'artifacts/verification/extended/coherent_cleanup_summary.json',
        'cleanup_summary_sha256': sha256_path(_cleanup_summary_path()),
        'extract_pc': extract_pc,
        'select_pcs': select_pcs,
        'clear_pc': clear_pc,
        'trace_extract_pass': int(per_pc[extract_pc]['pass']),
        'trace_extract_total': int(per_pc[extract_pc]['total']),
        'trace_clear_pass': int(per_pc[clear_pc]['pass']),
        'trace_clear_total': int(per_pc[clear_pc]['total']),
        'trace_cleanup_zero_pass': int(arithmetic_trace['cleanup_zero_after_clear']['pass']),
        'trace_cleanup_zero_total': int(arithmetic_trace['cleanup_zero_after_clear']['total']),
        'imported_cleanup_audit': cleanup_summary['summary'],
    }


def _whole_oracle_composition_equivalence(
    generated_block_inventories: Mapping[str, Any],
    frontier: Mapping[str, Any],
    full_attack_inventory: Mapping[str, Any],
) -> Dict[str, Any]:
    frontier_lookup = {row['name']: row for row in frontier['families']}
    inventory_lookup = {
        row['name']: row
        for row in full_attack_inventory['generated_block_inventory_summary']['family_reconstructed_totals']
    }
    family_rows = []
    for family in generated_block_inventories['families']:
        reconstruction = family['reconstruction']
        frontier_row = frontier_lookup[family['name']]
        inventory_row = inventory_lookup[family['name']]
        family_rows.append(
            {
                'name': family['name'],
                'generated_full_oracle_non_clifford': int(reconstruction['full_oracle_non_clifford']),
                'generated_total_logical_qubits': int(reconstruction['total_logical_qubits']),
                'frontier_full_oracle_non_clifford': int(frontier_row['full_oracle_non_clifford']),
                'frontier_total_logical_qubits': int(frontier_row['total_logical_qubits']),
                'inventory_full_oracle_non_clifford': int(inventory_row['full_oracle_non_clifford']),
                'inventory_total_logical_qubits': int(inventory_row['total_logical_qubits']),
            }
        )
    return {
        'best_gate_family': generated_block_inventories['best_gate_family'],
        'best_qubit_family': generated_block_inventories['best_qubit_family'],
        'families': family_rows,
    }


def build_subcircuit_equivalence_artifact(
    arithmetic_lowerings: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    generated_block_inventories: Mapping[str, Any],
    frontier: Mapping[str, Any],
    full_attack_inventory: Mapping[str, Any],
) -> Dict[str, Any]:
    selected_leaf = build_lookup_fed_leaf()
    selected_leaf_source = 'compiler_verification_project/artifacts/lookup_fed_leaf.json'
    arithmetic_trace = _arithmetic_opcode_equivalence(
        arithmetic_lowerings,
        leaf=selected_leaf,
        leaf_source_artifact=selected_leaf_source,
    )
    return {
        'schema': 'compiler-project-subcircuit-equivalence-v2',
        'source_artifacts': {
            'leaf': selected_leaf_source,
            'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
            'cleanup_summary': 'artifacts/verification/extended/coherent_cleanup_summary.json',
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
        },
        'arithmetic_opcode_equivalence': arithmetic_trace,
        'leaf_interface_equivalence': {
            'lookup_fed_leaf': build_lookup_fed_leaf_equivalence(),
        },
        'lookup_family_equivalence': _lookup_family_equivalence(lookup_lowerings),
        'cleanup_window_equivalence': _cleanup_window_equivalence(
            arithmetic_trace,
            leaf=selected_leaf,
            leaf_source_artifact=selected_leaf_source,
        ),
        'whole_oracle_composition_equivalence': _whole_oracle_composition_equivalence(
            generated_block_inventories,
            frontier,
            full_attack_inventory,
        ),
        'notes': [
            'This artifact binds the exact compiler-family summaries back to checked lower layers: traced ISA arithmetic/flag opcodes on the selected lookup-fed leaf, leaf-interface equivalence, lowered lookup-family semantics, the coherent cleanup window, and generated whole-oracle block composition.',
            'It does not claim external primitive-gate equivalence below the named arithmetic or lookup blocks.',
        ],
    }


__all__ = ['build_subcircuit_equivalence_artifact']
