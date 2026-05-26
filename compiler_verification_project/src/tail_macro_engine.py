#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter, deque
from functools import lru_cache
from typing import Any, Dict, Mapping, Sequence

from common import SECP_B, SECP_G, SECP_P, mul_affine, neg_affine
from lookup_research import (
    WORD_SIZE,
    build_lookup_base_set,
    build_positive_table,
    folded_lookup_point_from_cache,
)
from tail_macro_reversibility import (
    TOY_CURVES,
    Point,
    _add_points,
    _boundary_case,
    _canonical_projective,
    _projective_to_affine,
    _subgroup_points,
    _tail_map,
)


TAIL_MACRO_OPCODE = 'complete_a0_all_streamed_tail'
QUANTUM_INPUTS = ('X', 'Y', 'Z')
TABLE_CONSTANTS = ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
QUANTUM_OUTPUTS = ('X3', 'Y3', 'Z3')
TAIL_MACRO_FORMULA: Sequence[tuple[str, Sequence[str]]] = (
    ('G', ('X', 'Y')),
    ('H', ('G', 'lookup_x_plus_y')),
    ('A', ('X', 'lookup_x')),
    ('Zx', ('Z', 'lookup_x')),
    ('C', ('X', 'Zx')),
    ('I', ('Y', 'lookup_y')),
    ('K', ('H', 'A', 'I')),
    ('L', ('A',)),
    ('yZ', ('lookup_y', 'Z')),
    ('E', ('Y', 'yZ')),
    ('F', ('Z',)),
    ('M', ('I', 'F')),
    ('N', ('I', 'F')),
    ('KN', ('K', 'N')),
    ('EC', ('E', 'C')),
    ('NM', ('N', 'M')),
    ('CL', ('C', 'L')),
    ('ME', ('M', 'E')),
    ('LK', ('L', 'K')),
    ('X3', ('KN', 'EC')),
    ('Y3', ('NM', 'CL')),
    ('Z3', ('ME', 'LK')),
)
TAIL_MACRO_FIELD_OPERATION_STREAM: Sequence[Mapping[str, Any]] = (
    {'target': 'G', 'formula_target': 'G', 'opcode': 'field_add', 'sources': ('X', 'Y')},
    {'target': 'H', 'formula_target': 'H', 'opcode': 'field_mul_lookup_sum', 'sources': ('G', 'lookup_x_plus_y')},
    {'target': 'A', 'formula_target': 'A', 'opcode': 'field_mul_lookup_x', 'sources': ('X', 'lookup_x')},
    {'target': 'Zx', 'formula_target': 'Zx', 'opcode': 'field_mul_lookup_x', 'sources': ('Z', 'lookup_x')},
    {'target': 'C_input', 'formula_target': 'C', 'opcode': 'field_add', 'sources': ('X', 'Zx')},
    {'target': 'C', 'formula_target': 'C', 'opcode': 'mul_const', 'sources': ('C_input',), 'constant': 21},
    {'target': 'I', 'formula_target': 'I', 'opcode': 'field_mul_lookup_y', 'sources': ('Y', 'lookup_y')},
    {'target': 'K', 'formula_target': 'K', 'opcode': 'field_sub_sum', 'sources': ('H', 'A', 'I')},
    {'target': 'L', 'formula_target': 'L', 'opcode': 'field_triple', 'sources': ('A',), 'constant': 3},
    {'target': 'yZ', 'formula_target': 'yZ', 'opcode': 'field_mul_lookup_y', 'sources': ('Z', 'lookup_y')},
    {'target': 'E', 'formula_target': 'E', 'opcode': 'field_add', 'sources': ('Y', 'yZ')},
    {'target': 'F', 'formula_target': 'F', 'opcode': 'mul_const', 'sources': ('Z',), 'constant': 21},
    {'target': 'M', 'formula_target': 'M', 'opcode': 'field_add', 'sources': ('I', 'F')},
    {'target': 'N', 'formula_target': 'N', 'opcode': 'field_sub', 'sources': ('I', 'F')},
    {'target': 'KN', 'formula_target': 'KN', 'opcode': 'field_mul', 'sources': ('K', 'N')},
    {'target': 'EC', 'formula_target': 'EC', 'opcode': 'field_mul', 'sources': ('E', 'C')},
    {'target': 'NM', 'formula_target': 'NM', 'opcode': 'field_mul', 'sources': ('N', 'M')},
    {'target': 'CL', 'formula_target': 'CL', 'opcode': 'field_mul', 'sources': ('C', 'L')},
    {'target': 'ME', 'formula_target': 'ME', 'opcode': 'field_mul', 'sources': ('M', 'E')},
    {'target': 'LK', 'formula_target': 'LK', 'opcode': 'field_mul', 'sources': ('L', 'K')},
    {'target': 'X3', 'formula_target': 'X3', 'opcode': 'field_sub', 'sources': ('KN', 'EC')},
    {'target': 'Y3', 'formula_target': 'Y3', 'opcode': 'field_add', 'sources': ('NM', 'CL')},
    {'target': 'Z3', 'formula_target': 'Z3', 'opcode': 'field_add', 'sources': ('ME', 'LK')},
)
TAIL_MACRO_FUSED_OUTPUT_STREAM: Sequence[Mapping[str, Any]] = (
    *TAIL_MACRO_FIELD_OPERATION_STREAM[:14],
    {'target': 'X3', 'formula_target': 'X3', 'opcode': 'field_double_mul_sub', 'sources': ('K', 'N', 'E', 'C')},
    {'target': 'Y3', 'formula_target': 'Y3', 'opcode': 'field_double_mul_add', 'sources': ('N', 'M', 'C', 'L')},
    {'target': 'Z3', 'formula_target': 'Z3', 'opcode': 'field_double_mul_add', 'sources': ('M', 'E', 'L', 'K')},
)
FUSED_OUTPUT_ZERO_LIFT_GUARD_OWNER_ID = 'tail_fused_output_zero_lift_guard'


def _zero_lift_guard_non_clifford(field_bits: int) -> int:
    return 2 * (int(field_bits) - 1)


def _last_uses(formula: Sequence[tuple[str, Sequence[str]]]) -> Dict[str, int]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, (target, sources) in enumerate(formula):
        for source in sources:
            if source not in TABLE_CONSTANTS:
                last[source] = index
        last.setdefault(target, index)
    return last


def _formula_rows() -> list[Dict[str, Any]]:
    last = _last_uses(TAIL_MACRO_FORMULA)
    rows = []
    for index, (target, sources) in enumerate(TAIL_MACRO_FORMULA):
        rows.append({
            'index': index,
            'target': target,
            'sources': list(sources),
            'quantum_sources': [source for source in sources if source not in TABLE_CONSTANTS],
            'table_constant_sources': [source for source in sources if source in TABLE_CONSTANTS],
            'last_quantum_source_uses': {
                source: last[source]
                for source in sources
                if source not in TABLE_CONSTANTS and last[source] == index
            },
        })
    return rows


def _field_operation_rows(kernel_non_clifford_by_opcode: Mapping[str, Any], field_bits: int) -> list[Dict[str, Any]]:
    rows = []
    guard_non_clifford = _zero_lift_guard_non_clifford(field_bits)
    for index, operation in enumerate(TAIL_MACRO_FIELD_OPERATION_STREAM):
        opcode = str(operation['opcode'])
        target = str(operation['target'])
        in_place_guard = guard_non_clifford if target == 'Y3' else 0
        rows.append({
            'index': index,
            'target': target,
            'formula_target': str(operation['formula_target']),
            'opcode': opcode,
            'sources': list(operation['sources']),
            'constant': operation.get('constant'),
            'base_non_clifford': int(kernel_non_clifford_by_opcode[opcode]),
            'in_place_guard_non_clifford': in_place_guard,
            'non_clifford': int(kernel_non_clifford_by_opcode[opcode]) + in_place_guard,
        })
    return rows


def _fused_output_operation_rows(kernel_non_clifford_by_opcode: Mapping[str, Any], field_bits: int) -> list[Dict[str, Any]]:
    rows = []
    guard_non_clifford = _zero_lift_guard_non_clifford(field_bits)
    fused_cost_by_target = {
        'X3': int(kernel_non_clifford_by_opcode['field_mul']) * 2 + int(kernel_non_clifford_by_opcode['field_sub']),
        'Y3': int(kernel_non_clifford_by_opcode['field_mul']) * 2 + int(kernel_non_clifford_by_opcode['field_add']) + guard_non_clifford,
        'Z3': int(kernel_non_clifford_by_opcode['field_mul']) * 2 + int(kernel_non_clifford_by_opcode['field_add']),
    }
    for index, operation in enumerate(TAIL_MACRO_FUSED_OUTPUT_STREAM):
        opcode = str(operation['opcode'])
        target = str(operation['target'])
        rows.append({
            'index': index,
            'target': target,
            'formula_target': str(operation['formula_target']),
            'opcode': opcode,
            'sources': list(operation['sources']),
            'constant': operation.get('constant'),
            'base_non_clifford': fused_cost_by_target[target] - (guard_non_clifford if target == 'Y3' else 0) if opcode in {'field_double_mul_add', 'field_double_mul_sub'} else int(kernel_non_clifford_by_opcode[opcode]),
            'in_place_guard_non_clifford': guard_non_clifford if target == 'Y3' else 0,
            'non_clifford': fused_cost_by_target[target] if opcode in {'field_double_mul_add', 'field_double_mul_sub'} else int(kernel_non_clifford_by_opcode[opcode]),
        })
    return rows


def _secp_cubic_root(value: int) -> int:
    modulus = SECP_P
    residue = int(value) % modulus
    if residue == 0:
        return 0
    cubic_residue_order = (modulus - 1) // 3
    if pow(residue, cubic_residue_order, modulus) != 1:
        raise ValueError('value is not a secp256k1 cubic residue')
    exponent = pow(3, -1, cubic_residue_order)
    root = pow(residue, exponent, modulus)
    if pow(root, 3, modulus) != residue:
        raise ValueError('failed to reconstruct secp256k1 cubic root')
    return root


def _tail_trace_for_affine(accumulator: Point, lookup: Point, modulus: int = SECP_P) -> Dict[str, int]:
    if lookup is None:
        raise ValueError('non-infinity lookup required')
    accum_x, accum_y, accum_z = _canonical_projective(accumulator)
    lookup_x, lookup_y = lookup
    values = {
        'X': accum_x % modulus,
        'Y': accum_y % modulus,
        'Z': accum_z % modulus,
        'lookup_x': lookup_x % modulus,
        'lookup_y': lookup_y % modulus,
        'lookup_x_plus_y': (lookup_x + lookup_y) % modulus,
    }
    for row in _fused_output_operation_rows(
        {
            'field_add': 0,
            'field_sub': 0,
            'field_sub_sum': 0,
            'field_triple': 0,
            'mul_const': 0,
            'field_mul': 0,
            'field_mul_lookup_x': 0,
            'field_mul_lookup_y': 0,
            'field_mul_lookup_sum': 0,
        },
        field_bits=256,
    ):
        values[str(row['target'])] = _operation_value(
            opcode=str(row['opcode']),
            sources=row['sources'],
            values=values,
            modulus=modulus,
            curve_b=SECP_B,
            lookup_x=lookup[0],
            lookup_y=lookup[1],
            constant=row.get('constant'),
        )
    return values


def _zero_lift_y3_over_c(values: Mapping[str, int], modulus: int = SECP_P) -> int:
    l_value = int(values['L']) % modulus
    c_value = int(values['C']) % modulus
    product = (int(values['N']) * int(values['M'])) % modulus
    if l_value == 0:
        return (c_value + product) % modulus
    return (product + c_value * l_value) % modulus


def _inverse_zero_lift_y3_over_c(values: Mapping[str, int], output_value: int, modulus: int = SECP_P) -> int:
    l_value = int(values['L']) % modulus
    product = (int(values['N']) * int(values['M'])) % modulus
    if l_value == 0:
        return (int(output_value) - product) % modulus
    return ((int(output_value) - product) * pow(l_value, -1, modulus)) % modulus


@lru_cache(maxsize=1)
def _lookup_base_cache_rows() -> tuple[tuple[str, tuple[Point, ...], Point], ...]:
    rows = []
    for base in build_lookup_base_set():
        cache, special_pos = build_positive_table(base['point'], SECP_P, SECP_B)
        rows.append((base['id'], tuple(cache), neg_affine(special_pos, SECP_P)))
    return tuple(rows)


@lru_cache(maxsize=1)
def _first_m_zero_counterexample() -> Dict[str, Any]:
    cubic_residue_order = (SECP_P - 1) // 3
    for base_id, cache, special_neg in _lookup_base_cache_rows():
        for word in range(WORD_SIZE):
            lookup = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
            if lookup is None:
                continue
            lookup_y = int(lookup[1])
            accumulator_y = (-21 * pow(lookup_y, -1, SECP_P)) % SECP_P
            rhs = (accumulator_y * accumulator_y - SECP_B) % SECP_P
            if rhs != 0 and pow(rhs, cubic_residue_order, SECP_P) != 1:
                continue
            accumulator_x = _secp_cubic_root(rhs)
            accumulator = (accumulator_x, accumulator_y)
            trace = _tail_trace_for_affine(accumulator, lookup)
            if trace['M'] % SECP_P != 0:
                raise ValueError('constructed M-zero counterexample did not satisfy M == 0')
            return {
                'base_id': base_id,
                'word_hex': f'0x{word:04x}',
                'lookup_affine': [int(lookup[0]), int(lookup[1])],
                'accumulator_affine': [int(accumulator[0]), int(accumulator[1])],
                'm_value': int(trace['M']),
                'old_y3_over_n_coefficient': 'M',
                'reason': 'the unguarded Y3-over-N row is not a field permutation because its affine coefficient M can be zero on valid secp256k1 curve states',
            }
    raise ValueError('failed to find expected secp256k1 M-zero counterexample')


@lru_cache(maxsize=None)
def _secp256k1_fused_output_in_place_permutation_certificate(field_bits: int) -> Dict[str, Any]:
    lookup_rows = []
    for base_id, cache, special_neg in _lookup_base_cache_rows():
        base_lookup_x_nonzero = True
        base_lookup_y_nonzero = True
        non_infinity = 0
        for word in range(WORD_SIZE):
            lookup = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
            if lookup is None:
                continue
            non_infinity += 1
            base_lookup_x_nonzero = base_lookup_x_nonzero and int(lookup[0]) % SECP_P != 0
            base_lookup_y_nonzero = base_lookup_y_nonzero and int(lookup[1]) % SECP_P != 0
        lookup_rows.append({
            'base_id': base_id,
            'words_checked': WORD_SIZE,
            'non_infinity_words': non_infinity,
            'lookup_x_nonzero': base_lookup_x_nonzero,
            'lookup_y_nonzero': base_lookup_y_nonzero,
        })
    three_is_invertible = SECP_P % 3 != 0
    no_affine_x_zero = pow(SECP_B, (SECP_P - 1) // 2, SECP_P) == SECP_P - 1
    _, cache, special_neg = _lookup_base_cache_rows()[0]
    boundary_cases = [
        ('accumulator_infinity', None, folded_lookup_point_from_cache(1, cache, special_neg, SECP_P)),
        ('doubling', folded_lookup_point_from_cache(2, cache, special_neg, SECP_P), folded_lookup_point_from_cache(2, cache, special_neg, SECP_P)),
        ('inverse', neg_affine(folded_lookup_point_from_cache(3, cache, special_neg, SECP_P), SECP_P), folded_lookup_point_from_cache(3, cache, special_neg, SECP_P)),
        ('random', mul_affine(123456789, SECP_G, SECP_P, SECP_B), folded_lookup_point_from_cache(7, cache, special_neg, SECP_P)),
    ]
    replay_rows = []
    for name, accumulator, lookup in boundary_cases:
        if lookup is None:
            raise ValueError('selected replay lookup cannot be infinity')
        trace = _tail_trace_for_affine(accumulator, lookup)
        forward = _zero_lift_y3_over_c(trace)
        recovered = _inverse_zero_lift_y3_over_c(trace, forward)
        replay_rows.append({
            'case': name,
            'l_value': int(trace['L']),
            'c_value': int(trace['C']),
            'y3_value': int(trace['Y3']),
            'zero_lift_forward_value': int(forward),
            'recovered_c_value': int(recovered),
            'forward_matches_y3': forward == trace['Y3'] % SECP_P,
            'inverse_recovers_c': recovered == trace['C'] % SECP_P,
        })
    accumulator_infinity_row = next(row for row in replay_rows if row['case'] == 'accumulator_infinity')
    all_lookup_x_nonzero = all(row['lookup_x_nonzero'] for row in lookup_rows)
    all_lookup_y_nonzero = all(row['lookup_y_nonzero'] for row in lookup_rows)
    l_zero_implication_passes = three_is_invertible and no_affine_x_zero and all_lookup_x_nonzero
    checks = {
        'three_is_invertible_mod_secp256k1_p': three_is_invertible,
        'secp256k1_prime_has_no_affine_x_zero_point': no_affine_x_zero,
        'all_checked_lookup_x_coordinates_nonzero': all_lookup_x_nonzero,
        'all_checked_lookup_y_coordinates_nonzero': all_lookup_y_nonzero,
        'l_zero_implies_accumulator_infinity_on_valid_non_infinity_lookup_domain': l_zero_implication_passes,
        'l_zero_branch_is_accumulator_infinity_shape': accumulator_infinity_row['l_value'] == 0 and accumulator_infinity_row['c_value'] == 0,
        'zero_lift_forward_matches_y3_on_boundary_cases': all(row['forward_matches_y3'] for row in replay_rows),
        'zero_lift_inverse_recovers_c_on_boundary_cases': all(row['inverse_recovers_c'] for row in replay_rows),
    }
    return {
        'schema': 'compiler-project-secp256k1-fused-output-in-place-permutation-v1',
        'selected_output_reuse': {
            'operation_index': 15,
            'target': 'Y3',
            'overwritten_source': 'C',
            'ordinary_branch': 'C -> N*M + C*L when L != 0',
            'zero_lift_branch': 'C -> C + N*M when L == 0',
            'inverse_ordinary_branch': 'C <- (Y3 - N*M) / L',
            'inverse_zero_lift_branch': 'C <- Y3 - N*M',
        },
        'guard': {
            'owner_id': FUSED_OUTPUT_ZERO_LIFT_GUARD_OWNER_ID,
            'logical_qubits': 1,
            'non_clifford': _zero_lift_guard_non_clifford(field_bits),
            'construction': 'compute and uncompute one L == 0 predicate bit around the Y3-over-C in-place output row',
        },
        'lookup_coordinate_checks': lookup_rows,
        'l_zero_domain_proof': {
            'l_formula': 'L = 3 * X * lookup_x mod p',
            'c_formula': 'C = 21 * (X + Z * lookup_x) mod p',
            'premises': [
                '3 is invertible modulo secp256k1 p',
                'every non-infinity folded lookup table output has lookup_x != 0',
                'secp256k1 has no affine curve point with x == 0 because 7 is a quadratic non-residue modulo p',
                'the executable fused-output tail is bypassed for lookup-infinity rows; those are replayed as the external no-op boundary',
            ],
            'conclusion': 'On every valid non-infinity lookup tail execution, L == 0 implies the accumulator is infinity, so X == 0, Z == 0, C == 0, and the zero-lift branch preserves Y3 while keeping the overwritten C register invertible.',
            'pass': l_zero_implication_passes and accumulator_infinity_row['c_value'] == 0,
        },
        'boundary_replay_rows': replay_rows,
        'rejected_unguarded_output_reuse_counterexample': _first_m_zero_counterexample(),
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'A literal destructive overwrite is not claimed. The selected row is a reversible in-place field permutation with an explicit zero-lift branch.',
            'The old Y3-over-N choice is rejected by a concrete secp256k1 M == 0 counterexample.',
            'The L == 0 branch is required for accumulator-infinity boundary states; without it, Y3-over-C would not be a full field permutation.',
        ],
    }


def _apply_fused_output_in_place_screen(
    operand_screen: Mapping[str, Any],
    permutation_certificate: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = permutation_certificate['selected_output_reuse']
    selected_key = (int(selected['operation_index']), str(selected['overwritten_source']))
    choices = []
    for choice in operand_screen['choices']:
        updated = dict(choice)
        if int(updated['index']) >= 14 and (int(updated['index']), str(updated['overwritten_source'])) != selected_key:
            updated['pass'] = False
            updated['failure_reason'] = 'not covered by the secp256k1 zero-lift in-place permutation certificate'
            updated['failure_examples'] = [
                permutation_certificate['rejected_unguarded_output_reuse_counterexample']
                if int(updated['index']) == 15 and str(updated['overwritten_source']) == 'N'
                else {'reason': updated['failure_reason']}
            ]
        choices.append(updated)
    passing = [choice for choice in choices if choice['pass']]
    failing = [choice for choice in choices if not choice['pass']]
    return {
        **operand_screen,
        'screen_model': 'toy_boundary_operand_screen_plus_secp256k1_fused_output_permutation_contract',
        'choices': choices,
        'passing_choice_count': len(passing),
        'failing_choice_count': len(failing),
        'failing_row_indices': sorted({int(choice['index']) for choice in failing}),
        'secp256k1_permutation_certificate_schema': permutation_certificate['schema'],
    }


def _secp256k1_pair_output_determinant_certificate(field_bits: int) -> Dict[str, Any]:
    del field_bits
    minus_curve_b = (-SECP_B) % SECP_P
    no_affine_y_zero = pow(minus_curve_b, (SECP_P - 1) // 3, SECP_P) != 1
    lookup_rows = []
    inverse_branch_y3_nonzero = True
    accumulator_infinity_y3_nonzero = True
    sampled_boundary_y3_nonzero = True
    checked_boundary_rows = 0
    for base_id, cache, special_neg in _lookup_base_cache_rows():
        non_infinity = 0
        for word in range(WORD_SIZE):
            lookup = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
            if lookup is None:
                continue
            non_infinity += 1
            for case_name, accumulator in (
                ('accumulator_infinity', None),
                ('inverse', neg_affine(lookup, SECP_P)),
            ):
                trace = _tail_trace_for_affine(accumulator, lookup)
                checked_boundary_rows += 1
                if case_name == 'accumulator_infinity':
                    accumulator_infinity_y3_nonzero = accumulator_infinity_y3_nonzero and trace['Y3'] % SECP_P != 0
                else:
                    inverse_branch_y3_nonzero = inverse_branch_y3_nonzero and trace['Y3'] % SECP_P != 0
            if word in (1, 2, 3, 7, 123, 4567, WORD_SIZE - 1):
                for scalar in (word + 1, word * 17 + 5):
                    accumulator = mul_affine(scalar, SECP_G, SECP_P, SECP_B)
                    trace = _tail_trace_for_affine(accumulator, lookup)
                    checked_boundary_rows += 1
                    sampled_boundary_y3_nonzero = sampled_boundary_y3_nonzero and trace['Y3'] % SECP_P != 0
        lookup_rows.append({
            'base_id': base_id,
            'words_checked': WORD_SIZE,
            'non_infinity_words': non_infinity,
        })
    checks = {
        'secp256k1_has_no_affine_y_zero_point': no_affine_y_zero,
        'accumulator_infinity_branch_has_nonzero_y3_for_all_checked_lookup_words': accumulator_infinity_y3_nonzero,
        'inverse_branch_has_nonzero_y3_for_all_checked_lookup_words': inverse_branch_y3_nonzero,
        'sampled_non_boundary_rows_have_nonzero_y3': sampled_boundary_y3_nonzero,
    }
    return {
        'schema': 'compiler-project-secp256k1-pair-output-determinant-certificate-v1',
        'matrix': {
            'input_registers': ['E', 'K'],
            'output_registers': ['X3', 'Z3'],
            'rows': [
                {'target': 'X3', 'coefficients': {'E': '-C', 'K': 'N'}},
                {'target': 'Z3', 'coefficients': {'E': 'M', 'K': 'L'}},
            ],
            'determinant': '-C*L - N*M',
            'determinant_equals': '-Y3',
        },
        'secp256k1_no_affine_y_zero_proof': {
            'curve_equation': 'y^2 = x^3 + 7',
            'claim': 'y == 0 would require x^3 == -7 mod p',
            'minus_7_cubic_residue_check': pow(minus_curve_b, (SECP_P - 1) // 3, SECP_P),
            'pass': no_affine_y_zero,
        },
        'lookup_word_checks': lookup_rows,
        'checked_boundary_rows': checked_boundary_rows,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'The in-place pair-output map (E,K) -> (X3,Z3) has determinant -Y3.',
            'On the valid secp256k1 point-add boundary, Y3 == 0 would imply either an affine y == 0 curve point or a failed infinity branch; both are checked here.',
            'This proves the semantic permutation precondition for a six-slot candidate, not a finalized low-level resource lowering for the 2x2 in-place matrix operation.',
        ],
    }


def _six_slot_pair_output_candidate(
    *,
    field_bits: int,
    kernel_non_clifford_by_opcode: Mapping[str, Any],
    determinant_certificate: Mapping[str, Any],
) -> Dict[str, Any]:
    del field_bits
    fused_rows = {
        int(row['index']): row
        for row in _fused_output_operation_rows(kernel_non_clifford_by_opcode, 256)
    }
    prefix_indices = [0, 1, 3, 4, 2, 5, 9, 10, 6, 7, 8, 11]
    row_specs: list[Dict[str, Any]] = []
    live_values = set(QUANTUM_INPUTS)
    peak = len(live_values)

    def append_single(operation_index: int, overwritten_source: str | None, live_after_drop: set[str]) -> None:
        nonlocal live_values, peak
        row = fused_rows[operation_index]
        before = set(live_values)
        during = set(live_values)
        if overwritten_source is not None:
            during.remove(overwritten_source)
        during.add(str(row['target']))
        peak = max(peak, len(during))
        row_specs.append({
            'kind': 'single_field_row',
            'operation_index': operation_index,
            'opcode': str(row['opcode']),
            'target': str(row['target']),
            'sources': list(row['sources']),
            'overwritten_sources': [] if overwritten_source is None else [overwritten_source],
            'live_field_values_before_step': sorted(before),
            'live_field_values_during_step': sorted(during),
            'live_field_value_count_during_step': len(during),
            'live_field_values_after_step': sorted(live_after_drop),
            'live_field_value_count_after_step': len(live_after_drop),
        })
        live_values = set(live_after_drop)

    append_single(0, None, {'G', 'X', 'Y', 'Z'})
    append_single(1, None, {'H', 'X', 'Y', 'Z'})
    append_single(3, None, {'H', 'X', 'Y', 'Z', 'Zx'})
    append_single(4, 'Zx', {'C_input', 'H', 'X', 'Y', 'Z'})
    append_single(2, 'X', {'A', 'C_input', 'H', 'Y', 'Z'})
    append_single(5, 'C_input', {'A', 'C', 'H', 'Y', 'Z'})
    append_single(9, None, {'A', 'C', 'H', 'Y', 'Z', 'yZ'})
    append_single(10, 'yZ', {'A', 'C', 'E', 'H', 'Y', 'Z'})
    append_single(6, 'Y', {'A', 'C', 'E', 'H', 'I', 'Z'})
    append_single(7, 'H', {'A', 'C', 'E', 'I', 'K', 'Z'})
    append_single(8, 'A', {'C', 'E', 'I', 'K', 'L', 'Z'})
    append_single(11, 'Z', {'C', 'E', 'F', 'I', 'K', 'L'})

    before = set(live_values)
    during = {'C', 'E', 'K', 'L', 'M', 'N'}
    peak = max(peak, len(during))
    row_specs.append({
        'kind': 'in_place_mn_sum_difference_pair',
        'operation_indices': [12, 13],
        'targets': ['M', 'N'],
        'sources': ['I', 'F'],
        'overwritten_sources': ['I', 'F'],
        'determinant': '-2',
        'permutation_reason': '2 is invertible modulo every odd checked field modulus',
        'non_clifford': int(kernel_non_clifford_by_opcode['field_add']) + int(kernel_non_clifford_by_opcode['field_sub']),
        'live_field_values_before_step': sorted(before),
        'live_field_values_during_step': sorted(during),
        'live_field_value_count_during_step': len(during),
        'live_field_values_after_step': sorted(during),
        'live_field_value_count_after_step': len(during),
    })
    live_values = set(during)

    before = set(live_values)
    during = {'C', 'L', 'M', 'N', 'X3', 'Z3'}
    peak = max(peak, len(during))
    row_specs.append({
        'kind': 'in_place_xz_pair_output_matrix',
        'operation_indices': [14, 16],
        'targets': ['X3', 'Z3'],
        'sources': ['C', 'E', 'K', 'L', 'M', 'N'],
        'overwritten_sources': ['E', 'K'],
        'determinant': '-Y3',
        'determinant_certificate_schema': determinant_certificate['schema'],
        'determinant_certificate_pass': bool(determinant_certificate['pass']),
        'non_clifford': int(fused_rows[14]['non_clifford']) + int(fused_rows[16]['non_clifford']),
        'live_field_values_before_step': sorted(before),
        'live_field_values_during_step': sorted(during),
        'live_field_value_count_during_step': len(during),
        'live_field_values_after_step': sorted(during),
        'live_field_value_count_after_step': len(during),
    })
    live_values = set(during)

    before = set(live_values)
    during = {'L', 'M', 'N', 'X3', 'Y3', 'Z3'}
    after = set(QUANTUM_OUTPUTS)
    peak = max(peak, len(during))
    row_specs.append({
        'kind': 'single_field_row',
        'operation_index': 15,
        'opcode': 'field_double_mul_add',
        'target': 'Y3',
        'sources': ['N', 'M', 'C', 'L'],
        'overwritten_sources': ['C'],
        'overwrite_contract': 'secp256k1_zero_lifted_in_place_field_permutation',
        'live_field_values_before_step': sorted(before),
        'live_field_values_during_step': sorted(during),
        'live_field_value_count_during_step': len(during),
        'live_field_values_after_step': sorted(after),
        'live_field_value_count_after_step': len(after),
    })
    live_values = set(after)

    for schedule_index, row in enumerate(row_specs):
        row['schedule_index'] = schedule_index
        row['peak_field_slots_so_far'] = max(int(prior['live_field_value_count_during_step']) for prior in row_specs[: schedule_index + 1])

    replay = _six_slot_pair_output_replay(row_specs)
    return {
        'schema': 'compiler-project-tail-six-slot-pair-output-candidate-v1',
        'status': 'semantic_candidate_not_promoted_to_public_headline',
        'peak_field_slots': peak,
        'terminal_live_values': sorted(live_values),
        'rows': row_specs,
        'determinant_certificate': determinant_certificate,
        'replay_certificate': replay,
        'checks': {
            'schedule_reaches_six_slots': peak == 6,
            'terminal_live_values_are_outputs': sorted(live_values) == list(QUANTUM_OUTPUTS),
            'pair_output_determinant_certificate_passes': determinant_certificate['pass'] is True,
            'semantic_replay_passes': replay['pass'] is True,
        },
        'pass': peak == 6 and sorted(live_values) == list(QUANTUM_OUTPUTS) and determinant_certificate['pass'] is True and replay['pass'] is True,
        'promotion_blocker': 'The semantic six-slot schedule still needs a finalized primitive resource lowering for the variable 2x2 in-place output matrix before it can replace the guarded seven-slot public headline.',
    }


def _six_slot_pair_output_lowering_search(
    *,
    candidate: Mapping[str, Any],
    determinant_certificate: Mapping[str, Any],
    kernel_non_clifford_by_opcode: Mapping[str, Any],
) -> Dict[str, Any]:
    shear_only_basis = [
        {
            'operation': 'left_shear',
            'form': 'A <- A + q*B',
            'determinant': '1',
            'field_sized_output_lane_required': False,
            'cost_bound': 'one in-place field multiply-accumulate kernel if that primitive is admitted',
        },
        {
            'operation': 'right_shear',
            'form': 'B <- B + q*A',
            'determinant': '1',
            'field_sized_output_lane_required': False,
            'cost_bound': 'one in-place field multiply-accumulate kernel if that primitive is admitted',
        },
        {
            'operation': 'swap',
            'form': '(A,B) <- (B,A)',
            'determinant': '-1',
            'field_sized_output_lane_required': False,
            'cost_bound': 'Clifford/register relabel at this abstraction layer',
        },
    ]
    pivot_decompositions = [
        {
            'name': 'lu_pivot_minus_c',
            'pivot': '-C',
            'requires_nonzero': 'C',
            'decomposition': 'L(M/(-C)) * D(-C, Y3/C) * U(N/(-C))',
            'requires_quantum_inverse_or_division': ['1/C'],
            'requires_variable_scale': ['scale E by -C', 'scale K by Y3/C'],
            'boundary_counterexample': 'accumulator_infinity has C == 0',
            'accepted_without_branch': False,
        },
        {
            'name': 'lu_pivot_n_after_column_swap',
            'pivot': 'N',
            'requires_nonzero': 'N',
            'decomposition': 'column-swap plus LU pivot on N',
            'requires_quantum_inverse_or_division': ['1/N'],
            'requires_variable_scale': ['scale one register by N', 'scale one register by Y3/N'],
            'boundary_counterexample': 'accumulator_infinity has N == 0',
            'accepted_without_branch': False,
        },
        {
            'name': 'lu_pivot_m_after_row_swap',
            'pivot': 'M',
            'requires_nonzero': 'M',
            'decomposition': 'row-swap plus LU pivot on M',
            'requires_quantum_inverse_or_division': ['1/M'],
            'requires_variable_scale': ['scale one register by M', 'scale one register by Y3/M'],
            'boundary_counterexample': _first_m_zero_counterexample(),
            'accepted_without_branch': False,
        },
        {
            'name': 'lu_pivot_l_after_row_column_swap',
            'pivot': 'L',
            'requires_nonzero': 'L',
            'decomposition': 'row-and-column-swap plus LU pivot on L',
            'requires_quantum_inverse_or_division': ['1/L'],
            'requires_variable_scale': ['scale one register by L', 'scale one register by Y3/L'],
            'boundary_counterexample': 'accumulator_infinity has L == 0',
            'accepted_without_branch': False,
        },
    ]
    current_kernel_inventory = {
        'has_in_place_field_multiply_accumulate_without_product_lane': False,
        'has_variable_in_place_field_scale_without_extra_field_lane': False,
        'has_quantum_field_inverse_without_extra_field_lane': False,
        'available_related_costs': {
            'field_mul': int(kernel_non_clifford_by_opcode['field_mul']),
            'field_add': int(kernel_non_clifford_by_opcode['field_add']),
            'field_sub': int(kernel_non_clifford_by_opcode['field_sub']),
        },
    }
    target_determinant = str(determinant_certificate['matrix']['determinant_equals'])
    shear_only_reachable_determinants = sorted({str(row['determinant']) for row in shear_only_basis})
    shear_only_rejection = target_determinant not in shear_only_reachable_determinants
    pivot_requires_unavailable_lowering = all(
        row['accepted_without_branch'] is False
        and bool(row['requires_quantum_inverse_or_division'])
        and bool(row['requires_variable_scale'])
        and bool(row['boundary_counterexample'])
        for row in pivot_decompositions
    )
    no_extra_field_slot_contract_available = (
        current_kernel_inventory['has_variable_in_place_field_scale_without_extra_field_lane'] is True
        or current_kernel_inventory['has_quantum_field_inverse_without_extra_field_lane'] is True
    )
    blockers = [
        {
            'id': 'determinant_not_reachable_by_shears_only',
            'detail': 'Multiply-accumulate shears and swaps can only change determinant by a classical sign, but the target determinant is the live quantum value -Y3.',
        },
        {
            'id': 'variable_scale_not_in_kernel_inventory',
            'detail': 'A determinant-changing two-register lowering needs variable in-place scaling or an equivalent primitive; the current arithmetic lowering only certifies output-producing field_mul and add/sub kernels.',
        },
        {
            'id': 'pivot_branches_need_quantum_inverses',
            'detail': 'Standard LU/Bruhat decompositions require inverses of C, N, M, or L; each pivot has a checked boundary zero case or needs a branch plus an unimplemented inverse/scale lowering.',
        },
    ]
    checks = {
        'semantic_candidate_passes': candidate['pass'] is True,
        'determinant_precondition_passes': determinant_certificate['pass'] is True,
        'shear_only_lowering_rejected_because_target_determinant_is_variable': shear_only_rejection,
        'all_symbolic_lu_pivots_require_quantum_inverse_or_variable_scale': pivot_requires_unavailable_lowering,
        'current_kernel_inventory_lacks_required_variable_scale_primitive': (
            current_kernel_inventory['has_variable_in_place_field_scale_without_extra_field_lane'] is False
        ),
        'no_extra_field_slot_resource_contract_available': no_extra_field_slot_contract_available is False,
    }
    return {
        'schema': 'compiler-project-tail-six-slot-pair-output-lowering-search-v1',
        'status': 'blocked_on_variable_in_place_scale_lowering',
        'target_matrix': determinant_certificate['matrix'],
        'candidate_peak_field_slots': int(candidate['peak_field_slots']),
        'allowed_no_field_slot_basis_checked': shear_only_basis,
        'shear_only_determinant_analysis': {
            'target_determinant': target_determinant,
            'reachable_determinants': shear_only_reachable_determinants,
            'target_is_reachable': not shear_only_rejection,
        },
        'symbolic_decomposition_attempts': pivot_decompositions,
        'current_kernel_inventory': current_kernel_inventory,
        'blockers': blockers,
        'checks': checks,
        'promotion_ready': False,
        'pass': all(checks.values()),
        'notes': [
            'This artifact answers whether the semantic six-slot candidate can be promoted with the currently certified primitive resource inventory.',
            'It does not reject the six-slot algebra; it rejects promotion until a determinant-changing variable in-place field-scale primitive is lowered and counted without a hidden field lane.',
        ],
    }


def _six_slot_pair_output_replay(schedule_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    del schedule_rows
    category_totals = {
        'ordinary': 0,
        'doubling': 0,
        'inverse': 0,
        'accumulator_infinity': 0,
        'lookup_infinity': 0,
    }
    replay_failures = []
    checked_non_infinity_pairs = 0
    checked_lookup_infinity_pairs = 0
    rows = _fused_output_operation_rows(
        {
            'field_add': 0,
            'field_sub': 0,
            'field_sub_sum': 0,
            'field_triple': 0,
            'mul_const': 0,
            'field_mul': 0,
            'field_mul_lookup_x': 0,
            'field_mul_lookup_y': 0,
            'field_mul_lookup_sum': 0,
        },
        field_bits=256,
    )
    prefix_by_index = {int(row['index']): row for row in rows}
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        curve_b = int(curve['b'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        for lookup in points:
            for accumulator in points:
                category_totals[_boundary_case(accumulator, lookup, modulus)] += 1
                input_triple = _canonical_projective(accumulator)
                if lookup is None:
                    checked_lookup_infinity_pairs += 1
                    continue
                checked_non_infinity_pairs += 1
                values: Dict[str, int] = {
                    'X': input_triple[0],
                    'Y': input_triple[1],
                    'Z': input_triple[2],
                }
                for operation_index in [0, 1, 3, 4, 2, 5, 9, 10, 6, 7, 8, 11]:
                    row = prefix_by_index[operation_index]
                    values[str(row['target'])] = _operation_value(
                        opcode=str(row['opcode']),
                        sources=row['sources'],
                        values=values,
                        modulus=modulus,
                        curve_b=curve_b,
                        lookup_x=lookup[0],
                        lookup_y=lookup[1],
                        constant=row.get('constant'),
                    )
                values['M'] = (values['I'] + values['F']) % modulus
                values['N'] = (values['I'] - values['F']) % modulus
                values['X3'] = (values['K'] * values['N'] - values['E'] * values['C']) % modulus
                values['Z3'] = (values['M'] * values['E'] + values['L'] * values['K']) % modulus
                values['Y3'] = (values['N'] * values['M'] + values['C'] * values['L']) % modulus
                if values['Y3'] % modulus == 0 and len(replay_failures) < 4:
                    replay_failures.append({
                        'curve': curve['name'],
                        'failure': 'pair_output_matrix_determinant_zero',
                        'lookup_affine': list(lookup),
                        'accumulator_affine': None if accumulator is None else list(accumulator),
                    })
                output_triple = (values['X3'] % modulus, values['Y3'] % modulus, values['Z3'] % modulus)
                reference_triple = _tail_map(modulus, curve_b, lookup[0], lookup[1], *input_triple)
                output_affine = _projective_to_affine(output_triple, modulus)
                reference_affine = _projective_to_affine(reference_triple, modulus)
                expected_affine = _add_points(accumulator, lookup, modulus)
                if (output_triple != reference_triple or output_affine != expected_affine or reference_affine != expected_affine) and len(replay_failures) < 4:
                    replay_failures.append({
                        'curve': curve['name'],
                        'failure': 'semantic_output_mismatch',
                        'lookup_affine': list(lookup),
                        'accumulator_affine': None if accumulator is None else list(accumulator),
                        'output_projective': list(output_triple),
                        'reference_projective': list(reference_triple),
                        'output_affine': None if output_affine is None else list(output_affine),
                        'expected_affine': None if expected_affine is None else list(expected_affine),
                    })
    return {
        'schema': 'compiler-project-tail-six-slot-pair-output-replay-v1',
        'checked_non_infinity_pairs': checked_non_infinity_pairs,
        'checked_lookup_infinity_pairs': checked_lookup_infinity_pairs,
        'category_totals': category_totals,
        'replay_failures': replay_failures,
        'pass': not replay_failures,
    }


def _fused_output_lowering_contract(
    fused_output_rows: Sequence[Mapping[str, Any]],
    kernel_non_clifford_by_opcode: Mapping[str, Any],
    operand_screen: Mapping[str, Any],
    reordered_schedule: Mapping[str, Any],
    permutation_certificate: Mapping[str, Any],
) -> Dict[str, Any]:
    choices_by_row_and_source = {
        (int(choice['index']), str(choice['overwritten_source'])): choice
        for choice in operand_screen['choices']
    }
    schedule_by_operation = {
        int(row['operation_index']): row
        for row in reordered_schedule['rows']
    }
    rows = []
    for row in fused_output_rows:
        operation_index = int(row['index'])
        opcode = str(row['opcode'])
        if opcode not in {'field_double_mul_add', 'field_double_mul_sub'}:
            continue
        first_left, first_right, second_left, second_right = [str(source) for source in row['sources']]
        sign = -1 if opcode == 'field_double_mul_sub' else 1
        primitive_steps = [
            {
                'kind': 'field_mul_accumulate',
                'sources': [first_left, first_right],
                'sign': 1,
                'non_clifford': int(kernel_non_clifford_by_opcode['field_mul']),
            },
            {
                'kind': 'field_mul_accumulate',
                'sources': [second_left, second_right],
                'sign': sign,
                'non_clifford': int(kernel_non_clifford_by_opcode['field_mul']),
            },
            {
                'kind': 'field_sub' if sign < 0 else 'field_add',
                'sources': ['first_product_accumulator', 'second_product_accumulator'],
                'non_clifford': int(kernel_non_clifford_by_opcode['field_sub' if sign < 0 else 'field_add']),
            },
        ]
        schedule_row = schedule_by_operation[operation_index]
        overwritten_source = schedule_row['overwritten_source']
        overwrite_contract = None
        if overwritten_source is not None:
            source = str(overwritten_source)
            if source == first_left:
                coefficient = first_right
                coefficient_sign = 1
                offset_product = [second_left, second_right]
                offset_sign = sign
            elif source == first_right:
                coefficient = first_left
                coefficient_sign = 1
                offset_product = [second_left, second_right]
                offset_sign = sign
            elif source == second_left:
                coefficient = second_right
                coefficient_sign = sign
                offset_product = [first_left, first_right]
                offset_sign = 1
            elif source == second_right:
                coefficient = second_left
                coefficient_sign = sign
                offset_product = [first_left, first_right]
                offset_sign = 1
            else:
                raise ValueError(f'{source} is not a fused-output source')
            screen_choice = choices_by_row_and_source[(operation_index, source)]
            if operation_index == int(permutation_certificate['selected_output_reuse']['operation_index']) and source == permutation_certificate['selected_output_reuse']['overwritten_source']:
                overwrite_contract = {
                    'kind': 'secp256k1_zero_lifted_in_place_field_permutation',
                    'overwritten_source': source,
                    'coefficient_source': coefficient,
                    'coefficient_sign': coefficient_sign,
                    'offset_product_sources': offset_product,
                    'offset_sign': offset_sign,
                    'domain_rows_checked': int(screen_choice['domain_rows_checked']),
                    'screen_pass': bool(screen_choice['pass']),
                    'secp256k1_permutation_pass': bool(permutation_certificate['pass']),
                    'guard_owner_id': permutation_certificate['guard']['owner_id'],
                    'guard_non_clifford': int(permutation_certificate['guard']['non_clifford']),
                    'guard_logical_qubits': int(permutation_certificate['guard']['logical_qubits']),
                    'ordinary_branch': permutation_certificate['selected_output_reuse']['ordinary_branch'],
                    'zero_lift_branch': permutation_certificate['selected_output_reuse']['zero_lift_branch'],
                    'cost_model': 'two field_mul kernels, one field_add/sub combine, and the counted L == 0 zero-lift predicate compute/uncompute',
                }
            else:
                overwrite_contract = {
                    'kind': 'rejected_without_secp256k1_permutation_certificate',
                    'overwritten_source': source,
                    'coefficient_source': coefficient,
                    'coefficient_sign': coefficient_sign,
                    'offset_product_sources': offset_product,
                    'offset_sign': offset_sign,
                    'domain_rows_checked': int(screen_choice['domain_rows_checked']),
                    'screen_pass': bool(screen_choice['pass']),
                    'secp256k1_permutation_pass': False,
                }
        reconstructed_cost = sum(int(step['non_clifford']) for step in primitive_steps)
        if overwrite_contract is not None and overwrite_contract['kind'] == 'secp256k1_zero_lifted_in_place_field_permutation':
            primitive_steps.append({
                'kind': 'zero_lift_guard_compute_uncompute',
                'predicate': 'L == 0',
                'non_clifford': int(overwrite_contract['guard_non_clifford']),
            })
            reconstructed_cost += int(overwrite_contract['guard_non_clifford'])
        rows.append({
            'operation_index': operation_index,
            'target': str(row['target']),
            'opcode': opcode,
            'sources': list(row['sources']),
            'schedule_overwritten_source': overwritten_source,
            'primitive_steps': primitive_steps,
            'reconstructed_non_clifford': reconstructed_cost,
            'row_non_clifford': int(row['non_clifford']),
            'cost_matches_row': reconstructed_cost == int(row['non_clifford']),
            'overwrite_contract': overwrite_contract,
        })
    overwritten_output_rows = [row for row in rows if row['overwrite_contract'] is not None]
    return {
        'status': 'fused_output_rows_decomposed_to_counted_field_multiply_accumulate_steps',
        'rows': rows,
        'overwritten_output_row_count': len(overwritten_output_rows),
        'cost_matches_rows': all(row['cost_matches_row'] for row in rows),
        'all_output_overwrites_have_boundary_permutation_contract': all(
            row['overwrite_contract'] is None
            or (
                row['overwrite_contract']['kind'] == 'secp256k1_zero_lifted_in_place_field_permutation'
                and row['overwrite_contract']['screen_pass'] is True
                and row['overwrite_contract']['secp256k1_permutation_pass'] is True
            )
            for row in rows
        ),
        'guard_owner_capacity': permutation_certificate['guard'],
        'notes': [
            'The seven-slot schedule requires one fused-output row to reuse a dead input lane; this artifact names that dependency instead of hiding it as a free output register.',
            'The selected reuse is a zero-lifted field permutation over secp256k1, not a destructive overwrite.',
            'The contract is checked on the same toy point-add boundary as the replay certificate, plus an explicit secp256k1 coefficient/counterexample certificate.',
        ],
    }


def _fused_output_reversible_schedule_contract(
    *,
    schedule: Mapping[str, Any],
    slot_assignment: Mapping[str, Any],
    operand_screen: Mapping[str, Any],
    replay_certificate: Mapping[str, Any],
    lowering_contract: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    choices_by_row_and_source = {
        (int(choice['index']), str(choice['overwritten_source'])): choice
        for choice in operand_screen['choices']
    }
    fused_output_overwrite_by_operation = {
        int(row['operation_index']): row['overwrite_contract']
        for row in lowering_contract['rows']
        if row['overwrite_contract'] is not None
    }
    owner_capacity_by_slot = {
        int(row['slot']): row
        for row in slot_assignment['owner_capacity_rows']
    }
    slot_row_by_schedule = {
        int(row['schedule_index']): row
        for row in slot_assignment['rows']
    }
    contract_rows = []
    for row in schedule['rows']:
        operation_index = int(row['operation_index'])
        overwritten_source = row['overwritten_source']
        target_slot = int(slot_row_by_schedule[int(row['schedule_index'])]['target_slot'])
        if overwritten_source is None:
            contract_kind = 'fresh_target_field_register'
            proof = {
                'kind': 'fresh_target',
                'target_slot': target_slot,
                'capacity_owner_id': owner_capacity_by_slot[target_slot]['owner_id'],
            }
            reversible = True
        else:
            screen_choice = choices_by_row_and_source[(operation_index, str(overwritten_source))]
            fused_contract = fused_output_overwrite_by_operation.get(operation_index)
            if fused_contract is not None:
                contract_kind = 'secp256k1_zero_lifted_fused_output_permutation'
                proof = {
                    'kind': fused_contract['kind'],
                    'overwritten_source': str(overwritten_source),
                    'screen_pass': bool(fused_contract['screen_pass']),
                    'secp256k1_permutation_pass': bool(fused_contract['secp256k1_permutation_pass']),
                    'guard_owner_id': fused_contract['guard_owner_id'],
                    'guard_logical_qubits': int(fused_contract['guard_logical_qubits']),
                    'guard_non_clifford': int(fused_contract['guard_non_clifford']),
                    'domain_rows_checked': int(fused_contract['domain_rows_checked']),
                }
                reversible = (
                    fused_contract['kind'] == 'secp256k1_zero_lifted_in_place_field_permutation'
                    and bool(fused_contract['screen_pass'])
                    and bool(fused_contract['secp256k1_permutation_pass'])
                )
            else:
                contract_kind = 'screened_local_inverse_field_permutation'
                proof = {
                    'kind': screen_choice['rule']['kind'],
                    'overwritten_source': str(overwritten_source),
                    'domain_rows_checked': int(screen_choice['domain_rows_checked']),
                    'screen_pass': bool(screen_choice['pass']),
                    'rule': screen_choice['rule'],
                }
                reversible = bool(screen_choice['pass'])
        contract_rows.append({
            'schedule_index': int(row['schedule_index']),
            'operation_index': operation_index,
            'opcode': str(row['opcode']),
            'target': str(row['target']),
            'sources': [str(source) for source in row['sources']],
            'target_slot': target_slot,
            'overwritten_source': overwritten_source,
            'contract_kind': contract_kind,
            'reversibility_proof': proof,
            'reversible_field_operation_contract_pass': reversible,
        })
    owner_capacity_total = sum(int(row['logical_qubits']) for row in slot_assignment['owner_capacity_rows'])
    peak_field_slots = int(schedule['peak_field_slots'])
    checks = {
        'schedule_solution_reaches_seven_slots': (
            schedule['solution_found'] is True
            and peak_field_slots == 7
            and int(slot_assignment['peak_field_slots']) == 7
        ),
        'slot_owner_capacity_covers_peak': owner_capacity_total == peak_field_slots * int(field_bits),
        'all_reused_lanes_have_reversible_contract': all(
            row['reversible_field_operation_contract_pass']
            for row in contract_rows
            if row['overwritten_source'] is not None
        ),
        'fresh_target_rows_have_capacity_owner': all(
            row['reversibility_proof']['kind'] != 'fresh_target'
            or bool(row['reversibility_proof']['capacity_owner_id'])
            for row in contract_rows
        ),
        'fused_output_guard_is_counted': (
            int(lowering_contract['guard_owner_capacity']['logical_qubits']) == 1
            and int(lowering_contract['guard_owner_capacity']['non_clifford']) == _zero_lift_guard_non_clifford(field_bits)
        ),
        'replay_and_owner_capacity_pass': (
            replay_certificate['pass'] is True
            and replay_certificate['owner_capacity_pass'] is True
        ),
        'lowering_contract_pass': (
            lowering_contract['cost_matches_rows'] is True
            and lowering_contract['all_output_overwrites_have_boundary_permutation_contract'] is True
        ),
        'final_live_values_are_projective_outputs': schedule['terminal_live_values'] == list(QUANTUM_OUTPUTS),
    }
    return {
        'schema': 'compiler-project-tail-fused-output-reversible-schedule-contract-v1',
        'status': 'seven_slot_field_operation_schedule_has_reversible_contract',
        'scope': 'field_operation_schedule_over_counted_tail_slots',
        'field_bits': int(field_bits),
        'peak_field_slots': peak_field_slots,
        'owner_capacity_total_logical_qubits': owner_capacity_total,
        'operation_count': len(contract_rows),
        'overwritten_row_count': sum(1 for row in contract_rows if row['overwritten_source'] is not None),
        'fresh_target_row_count': sum(1 for row in contract_rows if row['overwritten_source'] is None),
        'rows': contract_rows,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This promotes the selected seven-slot tail schedule from a replay diagnostic to a field-operation reversible schedule contract.',
            'The contract is still above the modular-arithmetic Clifford expansion layer; each field operation is delegated to the remaining modular arithmetic lowering boundary.',
            'Every lane reuse is backed either by the operand-screen local inverse certificate or by the secp256k1 zero-lift fused-output permutation with its guard qubit counted.',
        ],
    }


def _one_compute_liveness(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    live = set(QUANTUM_INPUTS)
    trace = [{
        'step': 'initial',
        'target': None,
        'live_field_values': sorted(live),
        'live_field_value_count': len(live),
    }]
    peak_count = len(live)
    peak_step = 'initial'
    peak_live = sorted(live)
    for index, row in enumerate(rows):
        target = str(row['target'])
        live.add(target)
        expired = []
        for source in row['sources']:
            source_name = str(source)
            if source_name not in TABLE_CONSTANTS and last[source_name] == index and source_name not in QUANTUM_OUTPUTS:
                live.discard(source_name)
                expired.append(source_name)
        trace_row = {
            'step': index,
            'target': target,
            'opcode': str(row['opcode']),
            'sources': list(row['sources']),
            'expired_after_step': sorted(expired),
            'live_field_values': sorted(live),
            'live_field_value_count': len(live),
        }
        trace.append(trace_row)
        if len(live) > peak_count:
            peak_count = len(live)
            peak_step = f'{index}:{target}'
            peak_live = sorted(live)
    return {
        'schedule_model': 'single_assignment_expanded_field_operation_stream',
        'peak_live_field_values': peak_count,
        'peak_step': peak_step,
        'peak_live_values': peak_live,
        'rows': trace,
    }


def _expanded_slot_schedule(rows: Sequence[Mapping[str, Any]], counted_arithmetic_slots: int, field_bits: int) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        live_before = dict(sorted(slot_by_value.items()))
        occupied = set(slot_by_value.values())
        target_slot = 0
        while target_slot in occupied:
            target_slot += 1
        target = str(row['target'])
        slot_by_value[target] = target_slot
        live_during = dict(sorted(slot_by_value.items()))
        if len(live_during) > peak_slot_count:
            peak_slot_count = len(live_during)
            peak_step = f'{index}:{target}'
        expired = []
        for source in sources:
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'constant': row.get('constant'),
            'source_slots': {
                source: live_during[source]
                for source in sources
                if source not in TABLE_CONSTANTS
            },
            'live_before': live_before,
            'live_during': live_during,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'single_assignment_expanded_field_register_file',
        'status': 'executable_capacity_fallback_not_reversible_cleanup_proof',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'slot_owners': [
            {
                'slot': slot,
                'owner': (
                    f'leaf_arithmetic_slot_{slot}'
                    if slot < int(counted_arithmetic_slots)
                    else f'tail_macro_internal_slot_{slot - int(counted_arithmetic_slots)}'
                ),
                'logical_qubits': int(field_bits),
                'counted_in_current_leaf_budget': slot < int(counted_arithmetic_slots),
            }
            for slot in range(int(peak_slot_count))
        ],
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'notes': [
            'This is the strict expanded-capacity schedule for the current field-operation stream.',
            'It proves the number of field-sized lanes required if the tail is implemented as single-assignment field kernels.',
            'It is not a reversible cleanup or in-place three-slot proof; using it as the public primitive-circuit contract requires counting the additional tail_macro_internal_slot owners.',
        ],
    }


def _destructive_candidate_schedule(rows: Sequence[Mapping[str, Any]], counted_arithmetic_slots: int, field_bits: int) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    overwritten_rows = 0
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        target = str(row['target'])
        live_before = dict(sorted(slot_by_value.items()))
        expiring_sources = [
            source
            for source in sources
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS
        ]
        overwritten_source = None
        if expiring_sources:
            overwritten_source = max(expiring_sources, key=lambda source: slot_by_value[source])
            target_slot = slot_by_value[overwritten_source]
            del slot_by_value[overwritten_source]
            overwritten_rows += 1
        else:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        slot_by_value[target] = target_slot
        live_during_capacity = dict(sorted(slot_by_value.items()))
        if len(live_during_capacity) > peak_slot_count:
            peak_slot_count = len(live_during_capacity)
            peak_step = f'{index}:{target}'
        expired = []
        for source in expiring_sources:
            if source != overwritten_source:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'constant': row.get('constant'),
            'source_slots_before_operation': {
                source: live_before[source]
                for source in sources
                if source not in TABLE_CONSTANTS
            },
            'overwritten_source': overwritten_source,
            'overwritten_source_slot': None if overwritten_source is None else target_slot,
            'live_before': live_before,
            'live_during_capacity': live_during_capacity,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
            'proof_obligation': (
                'prove reversible/in-place implementation can consume overwritten source and write target in the same field lane without losing required information'
                if overwritten_source is not None
                else 'ordinary single-assignment target allocation'
            ),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'destructive_last_use_overwrite_candidate',
        'status': 'optimizer_candidate_not_a_reversible_proof',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'overwritten_row_count': overwritten_rows,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'proxy_metrics': {
            'peak_field_slots': int(peak_slot_count),
            'overwritten_row_count': overwritten_rows,
            'field_slot_improvement_vs_strict_single_assignment': None,
        },
        'notes': [
            'This optimizer candidate reuses the physical slot of a last-use source for the operation target.',
            'It is a search/proxy signal for in-place schedule development, not a public resource contract.',
            'Every overwritten row remains invalid until a reversible or valid-subspace permutation implementation is supplied for that opcode and boundary state.',
        ],
    }


def _operation_value(
    *,
    opcode: str,
    sources: Sequence[str],
    values: Mapping[str, int],
    modulus: int,
    curve_b: int,
    lookup_x: int,
    lookup_y: int,
    constant: Any,
) -> int:
    source_values = {
        'lookup_x': lookup_x % modulus,
        'lookup_y': lookup_y % modulus,
        'lookup_x_plus_y': (lookup_x + lookup_y) % modulus,
    }
    resolved = [
        source_values[source] if source in source_values else int(values[source])
        for source in sources
    ]
    if opcode == 'field_add':
        return sum(resolved) % modulus
    if opcode == 'field_sub':
        return (resolved[0] - resolved[1]) % modulus
    if opcode == 'field_sub_sum':
        return (resolved[0] - resolved[1] - resolved[2]) % modulus
    if opcode == 'field_triple':
        return (3 * resolved[0]) % modulus
    if opcode == 'mul_const':
        multiplier = 3 * int(curve_b) if constant is None or int(constant) == 21 else int(constant)
        return (multiplier * resolved[0]) % modulus
    if opcode in {'field_mul', 'field_mul_lookup_x', 'field_mul_lookup_y'}:
        return (resolved[0] * resolved[1]) % modulus
    if opcode == 'field_mul_lookup_sum':
        return (resolved[0] * resolved[1]) % modulus
    if opcode == 'field_double_mul_add':
        return (resolved[0] * resolved[1] + resolved[2] * resolved[3]) % modulus
    if opcode == 'field_double_mul_sub':
        return (resolved[0] * resolved[1] - resolved[2] * resolved[3]) % modulus
    raise ValueError(f'unsupported tail macro field opcode: {opcode}')


def _operation_trace_values(curve: Mapping[str, Any], lookup: Point, accumulator: Point, rows: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = lookup if lookup is not None else (0, 0)
    accum_x, accum_y, accum_z = _canonical_projective(accumulator)
    values: Dict[str, int] = {
        'X': accum_x,
        'Y': accum_y,
        'Z': accum_z,
    }
    trace = []
    for row in rows:
        sources = [str(source) for source in row['sources']]
        before = dict(values)
        target_value = _operation_value(
            opcode=str(row['opcode']),
            sources=sources,
            values=values,
            modulus=modulus,
            curve_b=curve_b,
            lookup_x=lookup_x,
            lookup_y=lookup_y,
            constant=row.get('constant'),
        )
        values[str(row['target'])] = target_value
        trace.append({
            'index': int(row['index']),
            'target': str(row['target']),
            'opcode': str(row['opcode']),
            'sources': sources,
            'before': before,
            'target_value': target_value,
            'lookup': None if lookup is None else {'x': lookup_x, 'y': lookup_y},
        })
    return trace


def _overwrite_rule(row: Mapping[str, Any], modulus: int) -> Dict[str, Any]:
    opcode = str(row['opcode'])
    sources = [str(source) for source in row['sources']]
    overwritten = str(row['overwritten_source'])
    if opcode in {'field_add', 'field_sub', 'field_sub_sum'}:
        return {
            'kind': 'affine_unit_coefficient',
            'symbolic_inverse_exists_over_field': True,
        }
    if opcode == 'field_triple':
        return {
            'kind': 'constant_multiply',
            'constant': 3,
            'symbolic_inverse_exists_over_field': 3 % int(modulus) != 0,
        }
    if opcode == 'mul_const':
        constant = int(row.get('constant') or 0)
        return {
            'kind': 'constant_multiply',
            'constant': constant,
            'symbolic_inverse_exists_over_field': constant % int(modulus) != 0,
        }
    if opcode in {'field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum'}:
        lookup_source = next(source for source in sources if source in TABLE_CONSTANTS)
        return {
            'kind': 'lookup_constant_multiply',
            'constant_source': lookup_source,
            'symbolic_inverse_exists_over_field': None,
        }
    if opcode == 'field_mul':
        multiplier_source = next(source for source in sources if source != overwritten)
        return {
            'kind': 'variable_multiply',
            'multiplier_source': multiplier_source,
            'symbolic_inverse_exists_over_field': None,
        }
    if opcode in {'field_double_mul_add', 'field_double_mul_sub'}:
        return {
            'kind': 'multi_product_affine_checked_by_domain_injectivity',
            'symbolic_inverse_exists_over_field': None,
        }
    raise ValueError(f'unsupported overwrite opcode: {opcode}')


def _overwrite_local_inverse_certificate(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    overwritten_rows = [row for row in rows if row.get('overwritten_source') is not None]
    proof_by_index = {
        int(row['index']): {
            'index': int(row['index']),
            'opcode': str(row['opcode']),
            'target': str(row['target']),
            'overwritten_source': str(row['overwritten_source']),
            'rule': _overwrite_rule(row, int(TOY_CURVES[0]['p'])),
            'checked_domain': 'toy canonical accumulator subgroup x non-infinity lookup subgroup',
            'domain_rows_checked': 0,
            'per_curve': [],
            'failure_examples': [],
        }
        for row in overwritten_rows
    }
    row_by_index = {int(row['index']): row for row in overwritten_rows}
    total_domain_rows = 0
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        curve_failures = {int(row['index']): [] for row in overwritten_rows}
        domain_rows_for_curve = (len(points) - 1) * len(points)
        for lookup in points:
            if lookup is None:
                continue
            for accumulator in points:
                trace = {
                    int(item['index']): item
                    for item in _operation_trace_values(curve, lookup, accumulator, rows)
                }
                total_domain_rows += len(overwritten_rows)
                for row in overwritten_rows:
                    row_index = int(row['index'])
                    rule = _overwrite_rule(row, modulus)
                    trace_row = trace[row_index]
                    proof_by_index[row_index]['domain_rows_checked'] += 1
                    if rule['kind'] == 'lookup_constant_multiply':
                        lookup_values = {
                            'lookup_x': lookup[0] % modulus,
                            'lookup_y': lookup[1] % modulus,
                            'lookup_x_plus_y': (lookup[0] + lookup[1]) % modulus,
                        }
                        condition_pass = lookup_values[str(rule['constant_source'])] != 0
                    elif rule['kind'] == 'variable_multiply':
                        condition_pass = int(trace_row['before'][str(rule['multiplier_source'])]) % modulus != 0
                    else:
                        condition_pass = bool(rule['symbolic_inverse_exists_over_field'])
                    if not condition_pass and len(curve_failures[row_index]) < 3:
                        curve_failures[row_index].append({
                            'lookup': list(lookup),
                            'accumulator': None if accumulator is None else list(accumulator),
                            'before': {
                                key: value
                                for key, value in trace_row['before'].items()
                                if key in set(trace_row['sources']) | {str(rule.get('multiplier_source', ''))}
                            },
                            'target_value': trace_row['target_value'],
                        })
        for row_index in sorted(row_by_index):
            failures = curve_failures[row_index]
            proof_by_index[row_index]['per_curve'].append({
                'curve': curve['name'],
                'domain_rows_checked': domain_rows_for_curve,
                'pass': not failures,
                'failure_examples': failures,
            })
            if failures and len(proof_by_index[row_index]['failure_examples']) < 4:
                proof_by_index[row_index]['failure_examples'].append({
                    'curve': curve['name'],
                    'examples': failures,
                })
    proof_rows = []
    for row_index in sorted(proof_by_index):
        proof_row = proof_by_index[row_index]
        proof_row['pass'] = not proof_row['failure_examples']
        if not proof_row['pass']:
            rule = proof_row['rule']
            if rule['kind'] == 'lookup_constant_multiply':
                proof_row['failure_reason'] = f"{rule['constant_source']} can be zero on the checked boundary domain"
            elif rule['kind'] == 'variable_multiply':
                proof_row['failure_reason'] = f"{rule['multiplier_source']} can be zero on the checked boundary domain"
            else:
                proof_row['failure_reason'] = 'overwrite rule is not locally invertible on the checked boundary domain'
        proof_rows.append(proof_row)
    passing_rows = sum(1 for row in proof_rows if row['pass'])
    return {
        'schema': 'compiler-project-tail-overwrite-local-inverse-certificate-v1',
        'status': 'toy_boundary_local_inverse_check_not_full_reversible_proof',
        'overwrite_row_count': len(overwritten_rows),
        'passing_row_count': passing_rows,
        'failing_row_count': len(overwritten_rows) - passing_rows,
        'total_domain_rows_checked': total_domain_rows,
        'rows': proof_rows,
        'pass': passing_rows == len(overwritten_rows),
        'notes': [
            'Each row checks whether the overwritten field value can be recovered from the target and the other fixed live inputs on the checked toy boundary domain.',
            'Passing this certificate is still not a complete reversible circuit proof; it is a local invertibility screen for the destructive-overwrite optimizer candidate.',
            'Failing rows identify concrete zero-multiplier or non-injective cases that must be avoided by a different schedule or a stronger valid-subspace argument.',
        ],
    }


def _expiring_source_choices(row: Mapping[str, Any]) -> list[str]:
    live_after = set(str(value) for value in row['live_after'])
    choices = [
        str(source)
        for source in row['sources']
        if source not in TABLE_CONSTANTS and str(source) not in live_after
    ]
    overwritten = row.get('overwritten_source')
    if overwritten is not None and str(overwritten) not in choices:
        choices.append(str(overwritten))
    return sorted(choices)


def _overwrite_choice_screen_from_operand_screen(
    rows: Sequence[Mapping[str, Any]],
    operand_screen: Mapping[str, Any],
) -> Dict[str, Any]:
    expiring_choice_keys = {
        (int(row['index']), overwritten_source)
        for row in rows
        for overwritten_source in _expiring_source_choices(row)
    }
    choices = [
        dict(choice)
        for choice in operand_screen['choices']
        if (int(choice['index']), str(choice['overwritten_source'])) in expiring_choice_keys
    ]
    passing_choices = sum(1 for choice in choices if choice['pass'])
    failing_choices = len(choices) - passing_choices
    failing_indices = sorted({int(choice['index']) for choice in choices if not choice['pass']})
    return {
        'schema': 'compiler-project-tail-overwrite-choice-screen-v1',
        'status': 'toy_boundary_expiring_source_choice_screen_not_full_reversible_proof',
        'choice_count': len(choices),
        'passing_choice_count': passing_choices,
        'failing_choice_count': failing_choices,
        'failing_row_indices': failing_indices,
        'choices': choices,
        'pass': failing_choices == 0,
        'derived_from': operand_screen['schema'],
        'notes': [
            'This screen filters the all-operand overwrite screen down to the expiring source choices for the fixed formula order.',
            'It distinguishes a bad overwrite-source choice from a true local non-invertibility blocker in the current formula order.',
        ],
    }


def _overwrite_operand_screen(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    choices = []
    for row in rows:
        for overwritten_source in sorted(str(source) for source in row['sources'] if source not in TABLE_CONSTANTS):
            rule_row = dict(row)
            rule_row['overwritten_source'] = overwritten_source
            choices.append({
                'index': int(row['index']),
                'opcode': str(row['opcode']),
                'target': str(row['target']),
                'sources': [str(source) for source in row['sources']],
                'constant': row.get('constant'),
                'overwritten_source': overwritten_source,
                'rule': _overwrite_rule(rule_row, int(TOY_CURVES[0]['p'])),
                'domain_rows_checked': 0,
                'failure_examples': [],
                '_seen_domain_keys': {},
            })
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        for lookup in points:
            if lookup is None:
                continue
            for accumulator in points:
                trace = {
                    int(item['index']): item
                    for item in _operation_trace_values(curve, lookup, accumulator, rows)
                }
                for choice in choices:
                    choice['domain_rows_checked'] += 1
                    if choice['failure_examples']:
                        continue
                    rule = _overwrite_rule(choice, modulus)
                    trace_row = trace[int(choice['index'])]
                    if rule['kind'] == 'lookup_constant_multiply':
                        lookup_values = {
                            'lookup_x': lookup[0] % modulus,
                            'lookup_y': lookup[1] % modulus,
                            'lookup_x_plus_y': (lookup[0] + lookup[1]) % modulus,
                        }
                        condition_pass = lookup_values[str(rule['constant_source'])] != 0
                    elif rule['kind'] == 'variable_multiply':
                        condition_pass = int(trace_row['before'][str(rule['multiplier_source'])]) % modulus != 0
                    elif rule['kind'] == 'multi_product_affine_checked_by_domain_injectivity':
                        other_sources = tuple(
                            int(trace_row['before'][source]) % modulus
                            for source in choice['sources']
                            if source not in TABLE_CONSTANTS and source != choice['overwritten_source']
                        )
                        domain_key = (
                            curve['name'],
                            int(trace_row['target_value']) % modulus,
                            other_sources,
                        )
                        overwritten_value = int(trace_row['before'][choice['overwritten_source']]) % modulus
                        seen_domain_keys = choice['_seen_domain_keys']
                        condition_pass = (
                            domain_key not in seen_domain_keys
                            or int(seen_domain_keys[domain_key]) == overwritten_value
                        )
                        if condition_pass:
                            seen_domain_keys[domain_key] = overwritten_value
                    else:
                        condition_pass = bool(rule['symbolic_inverse_exists_over_field'])
                    if not condition_pass:
                        choice['failure_examples'].append({
                            'curve': curve['name'],
                            'lookup': list(lookup),
                            'accumulator': None if accumulator is None else list(accumulator),
                            'reason': (
                                f"{rule['constant_source']} can be zero on the checked boundary domain"
                                if rule['kind'] == 'lookup_constant_multiply'
                                else f"{rule['multiplier_source']} can be zero on the checked boundary domain"
                                if rule['kind'] == 'variable_multiply'
                                else f"{choice['overwritten_source']} is not injective for the checked multi-product output row"
                                if rule['kind'] == 'multi_product_affine_checked_by_domain_injectivity'
                                else 'overwrite rule is not locally invertible on the checked boundary domain'
                            ),
                        })
    for choice in choices:
        del choice['_seen_domain_keys']
        choice['pass'] = not choice['failure_examples']
        if choice['failure_examples']:
            choice['failure_reason'] = choice['failure_examples'][0]['reason']
    passing_choices = sum(1 for choice in choices if choice['pass'])
    failing_choices = len(choices) - passing_choices
    failing_indices = sorted({int(choice['index']) for choice in choices if not choice['pass']})
    return {
        'schema': 'compiler-project-tail-overwrite-operand-screen-v1',
        'status': 'toy_boundary_operand_choice_screen_not_full_reversible_proof',
        'choice_count': len(choices),
        'passing_choice_count': passing_choices,
        'failing_choice_count': failing_choices,
        'failing_row_indices': failing_indices,
        'choices': choices,
        'pass': failing_choices == 0,
        'notes': [
            'This screen checks every quantum operand as a potential overwrite source, independent of the fixed formula order.',
            'The reordered schedule search uses only operand choices that pass this screen.',
        ],
    }


def _reconstruct_reordered_schedule(
    terminal: tuple[int, frozenset[str]],
    previous: Mapping[tuple[int, frozenset[str]], tuple[tuple[int, frozenset[str]] | None, Mapping[str, Any] | None]],
) -> list[Dict[str, Any]]:
    rows = []
    state = terminal
    while previous[state][0] is not None:
        parent, action = previous[state]
        assert action is not None
        rows.append(dict(action))
        assert parent is not None
        state = parent
    rows.reverse()
    for schedule_index, row in enumerate(rows):
        row['schedule_index'] = schedule_index
    return rows


def _reordered_local_inverse_schedule(
    rows: Sequence[Mapping[str, Any]],
    *,
    operand_screen: Mapping[str, Any],
    counted_arithmetic_slots: int,
    field_bits: int,
    max_peak_field_slots: int,
) -> Dict[str, Any]:
    operation_count = len(rows)
    producer_by_value = {
        str(row['target']): int(row['index'])
        for row in rows
    }
    dependencies_by_index = []
    for row in rows:
        dependencies = []
        for source in row['sources']:
            source_name = str(source)
            if source_name in TABLE_CONSTANTS:
                continue
            if source_name in producer_by_value:
                dependencies.append(producer_by_value[source_name])
        dependencies_by_index.append(tuple(dependencies))
    overwrite_allowed = {
        (int(choice['index']), str(choice['overwritten_source']))
        for choice in operand_screen['choices']
        if choice['pass'] is True
    }
    initial_state = (0, frozenset(QUANTUM_INPUTS))
    queue = deque([(initial_state, len(QUANTUM_INPUTS))])
    previous: Dict[tuple[int, frozenset[str]], tuple[tuple[int, frozenset[str]] | None, Mapping[str, Any] | None]] = {
        initial_state: (None, None)
    }
    best_peak_by_state = {initial_state: len(QUANTUM_INPUTS)}
    terminal = None
    terminal_peak = None
    while queue:
        (completed_mask, live_values), peak_so_far = queue.popleft()
        if all(output in live_values for output in QUANTUM_OUTPUTS):
            terminal = (completed_mask, live_values)
            terminal_peak = peak_so_far
            break
        for operation_index, row in enumerate(rows):
            operation_bit = 1 << operation_index
            if completed_mask & operation_bit:
                continue
            if any(not (completed_mask & (1 << dependency)) for dependency in dependencies_by_index[operation_index]):
                continue
            sources = [str(source) for source in row['sources'] if source not in TABLE_CONSTANTS]
            if any(source not in live_values for source in sources):
                continue
            next_completed_mask = completed_mask | operation_bit
            remaining_operation_indices = [
                index
                for index in range(operation_count)
                if not (next_completed_mask & (1 << index))
            ]
            needed_after = set(QUANTUM_OUTPUTS)
            for remaining_index in remaining_operation_indices:
                for source in rows[remaining_index]['sources']:
                    source_name = str(source)
                    if source_name not in TABLE_CONSTANTS:
                        needed_after.add(source_name)
            expiring_sources = [
                source
                for source in sources
                if source not in needed_after
            ]
            overwrite_options: list[str | None] = [None]
            overwrite_options.extend(
                source
                for source in expiring_sources
                if (operation_index, source) in overwrite_allowed
            )
            for overwritten_source in overwrite_options:
                live_during = set(live_values)
                if overwritten_source is not None:
                    live_during.remove(overwritten_source)
                live_during.add(str(row['target']))
                peak = max(int(peak_so_far), len(live_during))
                if peak > int(max_peak_field_slots):
                    continue
                live_after = set(live_during)
                for value in list(live_after):
                    if value not in needed_after and value != str(row['target']) and value not in QUANTUM_OUTPUTS:
                        live_after.remove(value)
                next_state = (next_completed_mask, frozenset(live_after))
                if peak >= best_peak_by_state.get(next_state, 10**9):
                    continue
                best_peak_by_state[next_state] = peak
                previous[next_state] = (
                    (completed_mask, live_values),
                    {
                        'operation_index': operation_index,
                        'opcode': str(row['opcode']),
                        'target': str(row['target']),
                        'sources': [str(source) for source in row['sources']],
                        'overwritten_source': overwritten_source,
                        'overwrite_local_inverse_screen': (
                            None
                            if overwritten_source is None
                            else 'passed_operand_screen'
                        ),
                        'live_field_values_before_step': sorted(live_values),
                        'live_field_values_during_step': sorted(live_during),
                        'live_field_value_count_during_step': len(live_during),
                        'live_field_values_after_step': sorted(live_after),
                        'live_field_value_count_after_step': len(live_after),
                        'peak_field_slots_so_far': peak,
                    },
                )
                queue.append((next_state, peak))
    solution_rows = None if terminal is None else _reconstruct_reordered_schedule(terminal, previous)
    peak_field_slots = None if terminal_peak is None else int(terminal_peak)
    additional_slots = None if peak_field_slots is None else max(0, peak_field_slots - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'reordered_dag_local_inverse_overwrite_search',
        'status': (
            'solution_found_not_full_reversible_circuit_proof'
            if terminal is not None
            else 'no_solution_with_current_budget'
        ),
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'max_peak_field_slots_searched': int(max_peak_field_slots),
        'solution_found': terminal is not None,
        'states_visited': len(previous),
        'peak_field_slots': peak_field_slots,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': None if additional_slots is None else additional_slots * int(field_bits),
        'overwritten_row_count': 0 if solution_rows is None else sum(1 for row in solution_rows if row['overwritten_source'] is not None),
        'invalid_overwrite_count': 0,
        'terminal_live_values': None if terminal is None else sorted(terminal[1]),
        'rows': solution_rows,
        'notes': [
            'This search reorders the expanded tail operation DAG and allows an overwrite only when the chosen operand passed the toy-boundary local inverse screen.',
            'A solution is stronger than the fixed-order destructive candidate, but it is still a schedule-level certificate rather than a Clifford-complete reversible circuit implementation.',
        ],
    }


def _reordered_slot_assignment(
    schedule_rows: Sequence[Mapping[str, Any]] | None,
    *,
    counted_arithmetic_slots: int,
    field_bits: int,
) -> Dict[str, Any]:
    if schedule_rows is None:
        return {
            'schema': 'compiler-project-tail-reordered-slot-assignment-v1',
            'status': 'no_schedule',
            'pass': False,
        }
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    for row in schedule_rows:
        live_before = dict(sorted(slot_by_value.items()))
        overwritten_source = row['overwritten_source']
        if overwritten_source is None:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        else:
            target_slot = slot_by_value[str(overwritten_source)]
            del slot_by_value[str(overwritten_source)]
        target = str(row['target'])
        slot_by_value[target] = target_slot
        live_during = dict(sorted(slot_by_value.items()))
        peak_slot_count = max(peak_slot_count, len(live_during))
        expected_live_after = set(str(value) for value in row['live_field_values_after_step'])
        for value in list(slot_by_value):
            if value not in expected_live_after:
                del slot_by_value[value]
        rows_out.append({
            'schedule_index': int(row['schedule_index']),
            'operation_index': int(row['operation_index']),
            'target': target,
            'target_slot': target_slot,
            'overwritten_source': overwritten_source,
            'source_slots_before_operation': {
                source: live_before[source]
                for source in row['sources']
                if source not in TABLE_CONSTANTS
            },
            'live_before': live_before,
            'live_during': live_during,
            'live_after': dict(sorted(slot_by_value.items())),
            'owner_id': f'tail_reordered_slot_{target_slot}',
        })
    owner_capacity_rows = [
        {
            'slot': slot,
            'owner_id': f'tail_reordered_slot_{slot}',
            'logical_qubits': int(field_bits),
            'capacity_field_values': 1,
            'counted_in_current_leaf_budget': slot < int(counted_arithmetic_slots),
        }
        for slot in range(peak_slot_count)
    ]
    additional_slots = max(0, peak_slot_count - int(counted_arithmetic_slots))
    return {
        'schema': 'compiler-project-tail-reordered-slot-assignment-v1',
        'status': 'slot_assignment_generated_for_reordered_schedule',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'owner_capacity_rows': owner_capacity_rows,
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'pass': (
            peak_slot_count == max(int(row['live_field_value_count_during_step']) for row in schedule_rows)
            and sorted(slot_by_value) == list(QUANTUM_OUTPUTS)
        ),
    }


def _reordered_schedule_replay_certificate(
    operation_rows: Sequence[Mapping[str, Any]],
    schedule: Mapping[str, Any],
    operand_screen: Mapping[str, Any],
    slot_assignment: Mapping[str, Any],
) -> Dict[str, Any]:
    operation_by_index = {
        int(row['index']): row
        for row in operation_rows
    }
    passing_overwrite_choices = {
        (int(choice['index']), str(choice['overwritten_source']))
        for choice in operand_screen['choices']
        if choice['pass'] is True
    }
    category_totals = {
        'ordinary': 0,
        'doubling': 0,
        'inverse': 0,
        'accumulator_infinity': 0,
        'lookup_infinity': 0,
    }
    replay_failures = []
    semantic_failures = []
    checked_non_infinity_pairs = 0
    checked_lookup_infinity_pairs = 0
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        curve_b = int(curve['b'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        for lookup in points:
            for accumulator in points:
                category_totals[_boundary_case(accumulator, lookup, modulus)] += 1
                input_triple = _canonical_projective(accumulator)
                if lookup is None:
                    checked_lookup_infinity_pairs += 1
                    output_triple = input_triple
                    output_affine = _projective_to_affine(output_triple, modulus)
                    expected_affine = _add_points(accumulator, lookup, modulus)
                    if output_affine != expected_affine and len(semantic_failures) < 4:
                        semantic_failures.append({
                            'curve': curve['name'],
                            'lookup_affine': None,
                            'accumulator_affine': None if accumulator is None else list(accumulator),
                            'output_projective': list(output_triple),
                            'output_affine': None if output_affine is None else list(output_affine),
                            'expected_affine': None if expected_affine is None else list(expected_affine),
                        })
                    continue
                checked_non_infinity_pairs += 1
                values: Dict[str, int] = {
                    'X': input_triple[0],
                    'Y': input_triple[1],
                    'Z': input_triple[2],
                }
                live_values = set(QUANTUM_INPUTS)
                for row in schedule['rows']:
                    operation = operation_by_index[int(row['operation_index'])]
                    if sorted(live_values) != row['live_field_values_before_step'] and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_before_mismatch',
                            'expected': row['live_field_values_before_step'],
                            'observed': sorted(live_values),
                        })
                    sources = [str(source) for source in operation['sources']]
                    missing_sources = [
                        source
                        for source in sources
                        if source not in TABLE_CONSTANTS and source not in live_values
                    ]
                    overwritten_source = row['overwritten_source']
                    if (
                        overwritten_source is not None
                        and (int(row['operation_index']), str(overwritten_source)) not in passing_overwrite_choices
                        and len(replay_failures) < 4
                    ):
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'overwrite_choice_not_screened',
                            'operation_index': int(row['operation_index']),
                            'overwritten_source': overwritten_source,
                        })
                    if missing_sources and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'missing_live_sources',
                            'missing_sources': missing_sources,
                        })
                    target_value = _operation_value(
                        opcode=str(operation['opcode']),
                        sources=sources,
                        values=values,
                        modulus=modulus,
                        curve_b=curve_b,
                        lookup_x=lookup[0],
                        lookup_y=lookup[1],
                        constant=operation.get('constant'),
                    )
                    if overwritten_source is not None:
                        live_values.remove(str(overwritten_source))
                        del values[str(overwritten_source)]
                    target = str(operation['target'])
                    live_values.add(target)
                    values[target] = target_value
                    expected_during = set(str(value) for value in row['live_field_values_during_step'])
                    if live_values != expected_during and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_during_mismatch',
                            'expected': sorted(expected_during),
                            'observed': sorted(live_values),
                        })
                    expected_after = set(str(value) for value in row['live_field_values_after_step'])
                    for value in list(live_values):
                        if value not in expected_after:
                            live_values.remove(value)
                            del values[value]
                    if live_values != expected_after and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_after_mismatch',
                            'expected': sorted(expected_after),
                            'observed': sorted(live_values),
                        })
                output_triple = (values['X3'] % modulus, values['Y3'] % modulus, values['Z3'] % modulus)
                reference_triple = _tail_map(modulus, curve_b, lookup[0], lookup[1], *input_triple)
                output_affine = _projective_to_affine(output_triple, modulus)
                expected_affine = _add_points(accumulator, lookup, modulus)
                if (
                    output_triple != reference_triple
                    or output_affine != expected_affine
                ) and len(semantic_failures) < 4:
                    semantic_failures.append({
                        'curve': curve['name'],
                        'lookup_affine': list(lookup),
                        'accumulator_affine': None if accumulator is None else list(accumulator),
                        'input_projective': list(input_triple),
                        'output_projective': list(output_triple),
                        'reference_projective': list(reference_triple),
                        'output_affine': None if output_affine is None else list(output_affine),
                        'expected_affine': None if expected_affine is None else list(expected_affine),
                    })
    schedule_peak = int(schedule['peak_field_slots'])
    slot_peak = int(slot_assignment['peak_field_slots'])
    owner_capacity_pass = (
        slot_assignment['pass'] is True
        and slot_peak == schedule_peak
        and all(int(row['logical_qubits']) >= int(schedule['field_bits']) for row in slot_assignment['owner_capacity_rows'])
    )
    return {
        'schema': 'compiler-project-tail-reordered-schedule-replay-certificate-v1',
        'status': 'toy_boundary_reordered_schedule_executable_replay',
        'checked_non_infinity_pairs': checked_non_infinity_pairs,
        'checked_lookup_infinity_pairs': checked_lookup_infinity_pairs,
        'category_totals': category_totals,
        'operation_count': len(operation_rows),
        'schedule_row_count': len(schedule['rows']),
        'semantic_failures': semantic_failures,
        'replay_failures': replay_failures,
        'owner_capacity_pass': owner_capacity_pass,
        'pass': not semantic_failures and not replay_failures and owner_capacity_pass,
        'notes': [
            'Non-infinity lookup cases execute the reordered schedule exactly and compare X3/Y3/Z3 with the canonical tail formula and affine point-add boundary.',
            'Lookup-infinity cases are checked as the external boundary no-op used by the streamed leaf contract; the reordered arithmetic schedule is not executed for that case.',
            'Owner capacity is derived from the generated slot assignment for the executable schedule, not from a manually selected tracked-register list.',
        ],
    }


def _allowed_overwrite_schedule(
    rows: Sequence[Mapping[str, Any]],
    *,
    allowed_overwrite_indices: set[int],
    counted_arithmetic_slots: int,
    field_bits: int,
) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    overwritten_rows = 0
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        target = str(row['target'])
        live_before = dict(sorted(slot_by_value.items()))
        expiring_sources = [
            source
            for source in sources
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS
        ]
        overwritten_source = None
        if index in allowed_overwrite_indices and expiring_sources:
            overwritten_source = max(expiring_sources, key=lambda source: slot_by_value[source])
            target_slot = slot_by_value[overwritten_source]
            del slot_by_value[overwritten_source]
            overwritten_rows += 1
        else:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        slot_by_value[target] = target_slot
        live_during_capacity = dict(sorted(slot_by_value.items()))
        if len(live_during_capacity) > peak_slot_count:
            peak_slot_count = len(live_during_capacity)
            peak_step = f'{index}:{target}'
        expired = []
        for source in expiring_sources:
            if source != overwritten_source:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'overwritten_source': overwritten_source,
            'live_before': live_before,
            'live_during_capacity': live_during_capacity,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'local_inverse_pass_only_overwrite_candidate',
        'status': 'screened_optimizer_candidate_not_public_contract',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'allowed_overwrite_indices': sorted(int(index) for index in allowed_overwrite_indices),
        'overwritten_row_count': overwritten_rows,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'notes': [
            'This schedule reuses slots only for destructive rows that passed the local inverse screen.',
            'It is a search diagnostic: it shows whether the currently screened reversible subset is enough to recover the eight-field-slot proxy.',
        ],
    }


def _component_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    names = set(QUANTUM_INPUTS)
    for row in rows:
        names.add(str(row['target']))
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                names.add(str(source))
    return sorted(names)


def build_tail_macro_engine(
    *,
    field_bits: int,
    counted_arithmetic_slots: int,
    kernel_non_clifford_by_opcode: Mapping[str, Any],
    selected_tail_kernel_non_clifford: int,
) -> Dict[str, Any]:
    operation_rows = _field_operation_rows(kernel_non_clifford_by_opcode, field_bits)
    fused_output_rows = _fused_output_operation_rows(kernel_non_clifford_by_opcode, field_bits)
    opcode_histogram = dict(sorted(Counter(row['opcode'] for row in operation_rows).items()))
    non_clifford_by_opcode = dict(sorted({
        opcode: sum(int(row['non_clifford']) for row in operation_rows if row['opcode'] == opcode)
        for opcode in opcode_histogram
    }.items()))
    non_clifford_total = sum(non_clifford_by_opcode.values())
    fused_output_opcode_histogram = dict(sorted(Counter(row['opcode'] for row in fused_output_rows).items()))
    fused_output_non_clifford_total = sum(int(row['non_clifford']) for row in fused_output_rows)
    liveness = _one_compute_liveness(operation_rows)
    fused_output_liveness = _one_compute_liveness(fused_output_rows)
    expanded_slot_schedule = _expanded_slot_schedule(operation_rows, counted_arithmetic_slots, field_bits)
    fused_output_expanded_slot_schedule = _expanded_slot_schedule(fused_output_rows, counted_arithmetic_slots, field_bits)
    destructive_candidate_schedule = _destructive_candidate_schedule(operation_rows, counted_arithmetic_slots, field_bits)
    destructive_candidate_schedule['proxy_metrics']['field_slot_improvement_vs_strict_single_assignment'] = (
        int(expanded_slot_schedule['peak_field_slots'])
        - int(destructive_candidate_schedule['peak_field_slots'])
    )
    overwrite_certificate = _overwrite_local_inverse_certificate(destructive_candidate_schedule['rows'])
    destructive_candidate_schedule['local_inverse_certificate'] = overwrite_certificate
    operand_overwrite_screen = _overwrite_operand_screen(operation_rows)
    overwrite_choice_screen = _overwrite_choice_screen_from_operand_screen(
        destructive_candidate_schedule['rows'],
        operand_overwrite_screen,
    )
    destructive_candidate_schedule['overwrite_choice_screen'] = overwrite_choice_screen
    reordered_local_inverse_schedule = _reordered_local_inverse_schedule(
        operation_rows,
        operand_screen=operand_overwrite_screen,
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
        max_peak_field_slots=int(destructive_candidate_schedule['peak_field_slots']),
    )
    reordered_slot_assignment = _reordered_slot_assignment(
        reordered_local_inverse_schedule['rows'],
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
    )
    reordered_replay_certificate = _reordered_schedule_replay_certificate(
        operation_rows,
        reordered_local_inverse_schedule,
        operand_overwrite_screen,
        reordered_slot_assignment,
    )
    raw_fused_output_operand_screen = _overwrite_operand_screen(fused_output_rows)
    fused_output_in_place_permutation_certificate = _secp256k1_fused_output_in_place_permutation_certificate(field_bits)
    pair_output_determinant_certificate = _secp256k1_pair_output_determinant_certificate(field_bits)
    six_slot_pair_output_candidate = _six_slot_pair_output_candidate(
        field_bits=field_bits,
        kernel_non_clifford_by_opcode=kernel_non_clifford_by_opcode,
        determinant_certificate=pair_output_determinant_certificate,
    )
    six_slot_pair_output_lowering_search = _six_slot_pair_output_lowering_search(
        candidate=six_slot_pair_output_candidate,
        determinant_certificate=pair_output_determinant_certificate,
        kernel_non_clifford_by_opcode=kernel_non_clifford_by_opcode,
    )
    fused_output_operand_screen = _apply_fused_output_in_place_screen(
        raw_fused_output_operand_screen,
        fused_output_in_place_permutation_certificate,
    )
    fused_output_reordered_schedule = _reordered_local_inverse_schedule(
        fused_output_rows,
        operand_screen=fused_output_operand_screen,
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
        max_peak_field_slots=7,
    )
    fused_output_slot_assignment = _reordered_slot_assignment(
        fused_output_reordered_schedule['rows'],
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
    )
    fused_output_replay_certificate = _reordered_schedule_replay_certificate(
        fused_output_rows,
        fused_output_reordered_schedule,
        fused_output_operand_screen,
        fused_output_slot_assignment,
    )
    fused_output_lowering_contract = _fused_output_lowering_contract(
        fused_output_rows,
        kernel_non_clifford_by_opcode,
        fused_output_operand_screen,
        fused_output_reordered_schedule,
        fused_output_in_place_permutation_certificate,
    )
    fused_output_reversible_schedule_contract = _fused_output_reversible_schedule_contract(
        schedule=fused_output_reordered_schedule,
        slot_assignment=fused_output_slot_assignment,
        operand_screen=fused_output_operand_screen,
        replay_certificate=fused_output_replay_certificate,
        lowering_contract=fused_output_lowering_contract,
        field_bits=field_bits,
    )
    if (
        fused_output_reordered_schedule['solution_found'] is True
        and fused_output_replay_certificate['pass'] is True
        and fused_output_lowering_contract['cost_matches_rows'] is True
        and fused_output_lowering_contract['all_output_overwrites_have_boundary_permutation_contract'] is True
        and fused_output_reversible_schedule_contract['pass'] is True
    ):
        fused_output_reordered_schedule['status'] = 'solution_found_with_replay_and_reversible_field_schedule_contract'
        fused_output_reordered_schedule['notes'] = [
            'This schedule reorders the fused-output tail DAG and allows an overwrite only when the chosen operand passed the toy-boundary operand screen.',
            'The paired fused_output_lowering_contract reconstructs the double-product output costs and names the required affine output overwrite.',
            'The paired fused_output_reversible_schedule_contract assigns every reused field lane to a reversible field-operation contract over counted seven-slot owners.',
            'This remains a strict point-add boundary resource contract rather than a fully flattened Clifford-level ZKP guest.',
        ]
    locally_invertible_indices = {
        int(row['index'])
        for row in overwrite_certificate['rows']
        if row['pass'] is True
    }
    local_inverse_pass_only_schedule = _allowed_overwrite_schedule(
        operation_rows,
        allowed_overwrite_indices=locally_invertible_indices,
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
    )
    counted_slots = int(counted_arithmetic_slots)
    live_after_peak_fields = int(liveness['peak_live_field_values'])
    strict_peak_fields = int(expanded_slot_schedule['peak_field_slots'])
    checks = {
        'formula_targets_match_engine_targets': (
            [target for target, _sources in TAIL_MACRO_FORMULA]
            == [row['target'] for row in _formula_rows()]
        ),
        'expanded_operation_stream_covers_formula_targets': (
            sorted(set(row['formula_target'] for row in operation_rows))
            == sorted(target for target, _sources in TAIL_MACRO_FORMULA)
        ),
        'non_clifford_total_matches_selected_tail_kernel': (
            int(non_clifford_total) == int(selected_tail_kernel_non_clifford)
        ),
        'fused_output_stream_cost_matches_expanded_stream': (
            int(fused_output_non_clifford_total) == int(non_clifford_total)
        ),
        'fused_output_replay_passes': bool(fused_output_replay_certificate['pass']),
        'fused_output_schedule_reaches_seven_slots': (
            bool(fused_output_reordered_schedule['solution_found'])
            and int(fused_output_reordered_schedule['peak_field_slots']) == 7
            and int(fused_output_slot_assignment['peak_field_slots']) == 7
        ),
        'fused_output_lowering_contract_passes': (
            fused_output_lowering_contract['cost_matches_rows'] is True
            and fused_output_lowering_contract['all_output_overwrites_have_boundary_permutation_contract'] is True
            and int(fused_output_lowering_contract['overwritten_output_row_count']) == 1
            and fused_output_in_place_permutation_certificate['pass'] is True
        ),
        'fused_output_reversible_schedule_contract_passes': (
            fused_output_reversible_schedule_contract['pass'] is True
        ),
        'counted_slots_cover_expanded_single_assignment_peak': strict_peak_fields <= counted_slots,
    }
    required_checks = {
        key: value
        for key, value in checks.items()
        if key != 'counted_slots_cover_expanded_single_assignment_peak'
    }
    return {
        'schema': 'compiler-project-tail-macro-engine-v1',
        'opcode': TAIL_MACRO_OPCODE,
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': counted_slots,
        'quantum_inputs': list(QUANTUM_INPUTS),
        'table_constant_sources': list(TABLE_CONSTANTS),
        'quantum_outputs': list(QUANTUM_OUTPUTS),
        'formula_rows': _formula_rows(),
        'expanded_field_operation_stream': operation_rows,
        'expanded_field_value_universe': _component_names(operation_rows),
        'opcode_histogram': opcode_histogram,
        'non_clifford_by_opcode': non_clifford_by_opcode,
        'non_clifford_total': int(non_clifford_total),
        'in_place_guard_non_clifford': _zero_lift_guard_non_clifford(field_bits),
        'fused_output_field_operation_stream': fused_output_rows,
        'fused_output_field_value_universe': _component_names(fused_output_rows),
        'fused_output_opcode_histogram': fused_output_opcode_histogram,
        'fused_output_non_clifford_total': int(fused_output_non_clifford_total),
        'selected_tail_kernel_non_clifford': int(selected_tail_kernel_non_clifford),
        'single_assignment_liveness': liveness,
        'fused_output_single_assignment_liveness': fused_output_liveness,
        'expanded_slot_schedule': expanded_slot_schedule,
        'fused_output_expanded_slot_schedule': fused_output_expanded_slot_schedule,
        'destructive_candidate_schedule': destructive_candidate_schedule,
        'slot_gap': {
            'expanded_single_assignment_peak_field_values': strict_peak_fields,
            'expanded_live_after_peak_field_values': live_after_peak_fields,
            'counted_arithmetic_slots': counted_slots,
            'additional_field_slots_needed_without_in_place_schedule': max(0, strict_peak_fields - counted_slots),
            'additional_logical_qubits_needed_without_in_place_schedule': max(0, strict_peak_fields - counted_slots) * int(field_bits),
            'fallback_schedule_additional_logical_qubits': int(expanded_slot_schedule['additional_logical_qubits_over_counted_leaf']),
            'destructive_candidate_peak_field_values': int(destructive_candidate_schedule['peak_field_slots']),
            'destructive_candidate_additional_logical_qubits': int(destructive_candidate_schedule['additional_logical_qubits_over_counted_leaf']),
            'destructive_candidate_overwrite_rows_locally_invertible': bool(overwrite_certificate['pass']),
            'local_inverse_pass_only_peak_field_values': int(local_inverse_pass_only_schedule['peak_field_slots']),
            'overwrite_choice_screen_pass': bool(overwrite_choice_screen['pass']),
            'operand_overwrite_screen_pass': bool(operand_overwrite_screen['pass']),
            'reordered_local_inverse_peak_field_values': reordered_local_inverse_schedule['peak_field_slots'],
            'reordered_local_inverse_solution_found': bool(reordered_local_inverse_schedule['solution_found']),
            'reordered_slot_assignment_peak_field_values': reordered_slot_assignment['peak_field_slots'],
            'reordered_replay_pass': bool(reordered_replay_certificate['pass']),
            'fused_output_reordered_peak_field_values': fused_output_reordered_schedule['peak_field_slots'],
            'fused_output_reordered_solution_found': bool(fused_output_reordered_schedule['solution_found']),
            'fused_output_slot_assignment_peak_field_values': fused_output_slot_assignment['peak_field_slots'],
            'fused_output_replay_pass': bool(fused_output_replay_certificate['pass']),
        },
        'local_inverse_pass_only_schedule': local_inverse_pass_only_schedule,
        'operand_overwrite_screen': operand_overwrite_screen,
        'reordered_local_inverse_schedule': reordered_local_inverse_schedule,
        'reordered_slot_assignment': reordered_slot_assignment,
        'reordered_replay_certificate': reordered_replay_certificate,
        'fused_output_operand_screen': fused_output_operand_screen,
        'raw_fused_output_operand_screen': raw_fused_output_operand_screen,
        'fused_output_in_place_permutation_certificate': fused_output_in_place_permutation_certificate,
        'pair_output_determinant_certificate': pair_output_determinant_certificate,
        'six_slot_pair_output_candidate': six_slot_pair_output_candidate,
        'six_slot_pair_output_lowering_search': six_slot_pair_output_lowering_search,
        'fused_output_reordered_schedule': fused_output_reordered_schedule,
        'fused_output_slot_assignment': fused_output_slot_assignment,
        'fused_output_replay_certificate': fused_output_replay_certificate,
        'fused_output_lowering_contract': fused_output_lowering_contract,
        'fused_output_reversible_schedule_contract': fused_output_reversible_schedule_contract,
        'checks': checks,
        'pass': all(value is True for value in required_checks.values()),
        'completion_status': (
            'tail_cost_bound_to_reversible_seven_slot_field_schedule_contract'
            if checks['fused_output_reversible_schedule_contract_passes']
            else 'tail_cost_bound_to_expanded_field_operation_stream_but_in_place_schedule_unproven'
            if not checks['counted_slots_cover_expanded_single_assignment_peak']
            else 'tail_cost_and_counted_slots_bound_to_expanded_field_operation_stream'
        ),
    }


__all__ = [
    'QUANTUM_INPUTS',
    'QUANTUM_OUTPUTS',
    'TABLE_CONSTANTS',
    'TAIL_MACRO_FIELD_OPERATION_STREAM',
    'TAIL_MACRO_FORMULA',
    'TAIL_MACRO_OPCODE',
    'build_tail_macro_engine',
]
