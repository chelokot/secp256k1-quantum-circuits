#!/usr/bin/env python3

from __future__ import annotations

from math import ceil
from typing import Any, Dict, List, Mapping, Optional, Tuple

from tail_macro_reversibility import (
    TOY_CURVES,
    Point,
    _add_points,
    _canonical_projective,
    _projective_to_affine,
    _subgroup_points,
    _tail_map,
)


def _split_chunks(value: int, chunk_bits: int, chunk_count: int) -> List[int]:
    mask = (1 << int(chunk_bits)) - 1
    return [(int(value) >> (index * int(chunk_bits))) & mask for index in range(int(chunk_count))]


def _chunked_const_mul(value: int, constant: int, modulus: int, chunk_bits: int, chunk_count: int) -> int:
    total = 0
    for index, chunk in enumerate(_split_chunks(constant, chunk_bits, chunk_count)):
        total += int(value) * int(chunk) * pow(2, index * int(chunk_bits), modulus)
    return total % int(modulus)


def _chunked_tail_map(
    *,
    modulus: int,
    curve_b: int,
    lookup_x: int,
    lookup_y: int,
    accum_x: int,
    accum_y: int,
    accum_z: int,
    chunk_bits: int,
    chunk_count: int,
) -> Tuple[int, int, int]:
    b3 = (3 * int(curve_b)) % int(modulus)
    lookup_x_plus_y = (int(lookup_x) + int(lookup_y)) % int(modulus)
    g_value = (int(accum_x) + int(accum_y)) % int(modulus)
    h_value = _chunked_const_mul(g_value, lookup_x_plus_y, modulus, chunk_bits, chunk_count)
    a_value = _chunked_const_mul(accum_x, lookup_x, modulus, chunk_bits, chunk_count)
    zx_value = _chunked_const_mul(accum_z, lookup_x, modulus, chunk_bits, chunk_count)
    c_value = (b3 * (int(accum_x) + zx_value)) % int(modulus)
    i_value = _chunked_const_mul(accum_y, lookup_y, modulus, chunk_bits, chunk_count)
    k_value = (h_value - a_value - i_value) % int(modulus)
    l_value = (3 * a_value) % int(modulus)
    yz_value = _chunked_const_mul(accum_z, lookup_y, modulus, chunk_bits, chunk_count)
    e_value = (int(accum_y) + yz_value) % int(modulus)
    f_value = (b3 * int(accum_z)) % int(modulus)
    m_value = (i_value + f_value) % int(modulus)
    n_value = (i_value - f_value) % int(modulus)
    return (
        (k_value * n_value - e_value * c_value) % int(modulus),
        (n_value * m_value + c_value * l_value) % int(modulus),
        (m_value * e_value + l_value * k_value) % int(modulus),
    )


def _boundary_case(accumulator: Point, lookup: Point, modulus: int) -> str:
    if lookup is None:
        return 'lookup_infinity'
    if accumulator is None:
        return 'accumulator_infinity'
    if accumulator == lookup:
        return 'doubling'
    if accumulator[0] == lookup[0] and (accumulator[1] + lookup[1]) % modulus == 0:
        return 'inverse'
    return 'ordinary'


def _toy_semantic_row(curve: Mapping[str, Any]) -> Dict[str, Any]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    field_bits = modulus.bit_length()
    chunk_bits = max(1, ceil(field_bits / 2))
    chunk_count = ceil(field_bits / chunk_bits)
    points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
    category_totals = {
        'ordinary': 0,
        'doubling': 0,
        'inverse': 0,
        'accumulator_infinity': 0,
        'lookup_infinity': 0,
    }
    semantic_failures = []
    total_pairs = 0
    for lookup in points:
        for accumulator in points:
            input_triple = _canonical_projective(accumulator)
            if lookup is None:
                output_triple = input_triple
                reference_triple = input_triple
            else:
                output_triple = _chunked_tail_map(
                    modulus=modulus,
                    curve_b=curve_b,
                    lookup_x=lookup[0],
                    lookup_y=lookup[1],
                    accum_x=input_triple[0],
                    accum_y=input_triple[1],
                    accum_z=input_triple[2],
                    chunk_bits=chunk_bits,
                    chunk_count=chunk_count,
                )
                reference_triple = _tail_map(modulus, curve_b, lookup[0], lookup[1], *input_triple)
            expected_affine = _add_points(accumulator, lookup, modulus)
            output_affine = _projective_to_affine(output_triple, modulus)
            reference_affine = _projective_to_affine(reference_triple, modulus)
            category_totals[_boundary_case(accumulator, lookup, modulus)] += 1
            total_pairs += 1
            if (
                output_triple != reference_triple
                or output_affine != reference_affine
                or output_affine != expected_affine
            ) and len(semantic_failures) < 4:
                semantic_failures.append({
                    'lookup_affine': None if lookup is None else list(lookup),
                    'accumulator_affine': None if accumulator is None else list(accumulator),
                    'input_projective': list(input_triple),
                    'output_projective': list(output_triple),
                    'reference_projective': list(reference_triple),
                    'output_affine': None if output_affine is None else list(output_affine),
                    'reference_affine': None if reference_affine is None else list(reference_affine),
                    'expected_affine': None if expected_affine is None else list(expected_affine),
                })
    return {
        'curve': curve['name'],
        'field_bits': field_bits,
        'chunk_bits': chunk_bits,
        'chunk_count': chunk_count,
        'total_boundary_pairs': total_pairs,
        'category_totals': category_totals,
        'semantic_pass': not semantic_failures,
        'semantic_failure_examples': semantic_failures,
    }


def build_reusable_chunk_tail_candidate(
    *,
    fallback_frontier_stress: Mapping[str, Any],
) -> Dict[str, Any]:
    candidate = fallback_frontier_stress['reusable_chunked_coordinate_candidate']
    toy_rows = [_toy_semantic_row(curve) for curve in TOY_CURVES]
    return {
        'schema': 'compiler-project-reusable-chunk-tail-candidate-v1',
        'status': 'candidate_unproven_not_headline',
        'source_artifact': 'compiler_verification_project/artifacts/fallback_frontier_stress.json',
        'semantic_model': {
            'description': 'Each table coordinate is split into chunks; the same live chunk target may feed every matching table-controlled multiplication before uncompute.',
            'coordinate_tables': list(candidate['coordinate_tables']),
            'consumer_plan': {
                'lookup_x': ['A = X * lookup_x', 'Zx = Z * lookup_x'],
                'lookup_y': ['I = Y * lookup_y', 'yZ = Z * lookup_y'],
                'lookup_x_plus_y': ['H = (X + Y) * (lookup_x + lookup_y)'],
            },
            'full_coordinate_lanes_materialized': 0,
        },
        'toy_semantic_equivalence': {
            'rows': toy_rows,
            'all_rows_semantic': all(bool(row['semantic_pass']) for row in toy_rows),
            'total_boundary_pairs': sum(int(row['total_boundary_pairs']) for row in toy_rows),
            'category_totals': {
                category: sum(int(row['category_totals'][category]) for row in toy_rows)
                for category in ('ordinary', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity')
            },
        },
        'production_resource_candidate': {
            'field_bits': 256,
            'chunk_bits': int(fallback_frontier_stress['chunked_coordinate_qroam_counterfactual']['max_qroam_target_bits_per_live_chunk']),
            'chunk_count': int(candidate['chunks_per_coordinate_table']),
            'arithmetic_slot_count': 4,
            'chunk_streams_per_leaf': int(candidate['chunk_streams_per_leaf']),
            'leaf_call_count_total': int(candidate['leaf_call_count_total']),
            'candidate_total_non_clifford': int(candidate['candidate_total_non_clifford']),
            'candidate_total_logical_qubits': int(candidate['candidate_total_logical_qubits']),
            'beats_requested_non_clifford_limit': bool(candidate['beats_requested_non_clifford_limit']),
            'beats_requested_logical_qubit_limit': bool(candidate['beats_requested_logical_qubit_limit']),
        },
        'remaining_proof_obligations': list(candidate['proof_obligations_before_public_claim']),
        'notes': [
            'This artifact proves only the chunked table-constant semantics and resource arithmetic for the candidate model.',
            'It deliberately does not update the repository headline or ZKP public values.',
            'A public result still requires a generated chunked multiplier lowering and an executable four-slot leaf contract.',
        ],
    }


__all__ = ['build_reusable_chunk_tail_candidate']
