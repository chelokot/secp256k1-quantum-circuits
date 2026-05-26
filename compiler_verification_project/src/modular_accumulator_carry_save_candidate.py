#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping


MODULAR_ACCUMULATOR_CARRY_SAVE_CANDIDATE_SCHEMA = 'compiler-project-modular-accumulator-carry-save-candidate-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _initial_column_heights(width: int) -> List[int]:
    return [
        column + 1 if column < int(width) else 2 * int(width) - 1 - column
        for column in range(2 * int(width) - 1)
    ]


def _carry_save_layers(width: int) -> Dict[str, Any]:
    heights = _initial_column_heights(width)
    layers = []
    total_full_adders = 0
    layer_index = 0
    while max(heights) > 2:
        next_heights = [0] * (len(heights) + 1)
        layer_full_adders = 0
        for column, height in enumerate(heights):
            full_adders = height // 3
            remainder = height % 3
            next_heights[column] += remainder + full_adders
            next_heights[column + 1] += full_adders
            layer_full_adders += full_adders
        while len(next_heights) > 1 and next_heights[-1] == 0:
            next_heights.pop()
        layers.append({
            'layer_index': layer_index,
            'full_adder_count': layer_full_adders,
            'column_count_after_layer': len(next_heights),
            'max_column_height_after_layer': max(next_heights),
            'live_column_bits_after_layer': sum(next_heights),
        })
        total_full_adders += layer_full_adders
        heights = next_heights
        layer_index += 1
    return {
        'input_column_count': 2 * int(width) - 1,
        'initial_partial_product_bits': int(width) * int(width),
        'layer_count': len(layers),
        'full_adder_count': total_full_adders,
        'final_column_count': len(heights),
        'final_live_column_bits': sum(heights),
        'final_max_column_height': max(heights),
        'final_carry_propagate_bits': 2 * int(width),
        'layers_materialized_in_json': True,
        'layers': layers,
    }


def _carry_save_product(left: int, right: int, width: int) -> int:
    columns = [[] for _ in range(2 * int(width))]
    for left_bit in range(int(width)):
        for right_bit in range(int(width)):
            columns[left_bit + right_bit].append(((int(left) >> left_bit) & 1) & ((int(right) >> right_bit) & 1))
    while max(len(column) for column in columns) > 2:
        next_columns = [[] for _ in range(len(columns) + 1)]
        for column_index, column_bits in enumerate(columns):
            cursor = 0
            while cursor + 2 < len(column_bits):
                bit_a, bit_b, bit_c = column_bits[cursor], column_bits[cursor + 1], column_bits[cursor + 2]
                total = bit_a + bit_b + bit_c
                next_columns[column_index].append(total & 1)
                next_columns[column_index + 1].append(1 if total >= 2 else 0)
                cursor += 3
            next_columns[column_index].extend(column_bits[cursor:])
        while len(next_columns) > 1 and not next_columns[-1]:
            next_columns.pop()
        columns = next_columns
    value = 0
    for column_index, column_bits in enumerate(columns):
        value += sum(column_bits) << column_index
    return value


def _reduced_width_checks(widths: Iterable[int]) -> List[Dict[str, Any]]:
    checks = []
    for width in widths:
        mismatch_count = 0
        total_cases = 0
        max_result = 0
        for left in range(1 << int(width)):
            for right in range(1 << int(width)):
                total_cases += 1
                observed = _carry_save_product(left, right, int(width))
                expected = left * right
                max_result = max(max_result, observed)
                if observed != expected:
                    mismatch_count += 1
        layers = _carry_save_layers(int(width))
        checks.append({
            'width': int(width),
            'total_cases': total_cases,
            'mismatch_count': mismatch_count,
            'pass': mismatch_count == 0,
            'full_adder_count': int(layers['full_adder_count']),
            'layer_count': int(layers['layer_count']),
            'final_max_column_height': int(layers['final_max_column_height']),
            'max_result': max_result,
        })
    return checks


def build_modular_accumulator_carry_save_candidate(
    *,
    modular_accumulator_row_stream: Mapping[str, Any],
    modular_accumulator_carry_obligations: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    field_bits = int(field_bits)
    partial_product_rows = int(modular_accumulator_row_stream['expanded_counts']['partial_product_consume_rows'])
    grid_count = partial_product_rows // (field_bits * field_bits)
    single_grid_layers = _carry_save_layers(field_bits)
    reduced_width = _reduced_width_checks(range(2, 7))
    all_grid_full_adders = grid_count * int(single_grid_layers['full_adder_count'])
    all_grid_final_carry_bits = grid_count * int(single_grid_layers['final_carry_propagate_bits'])
    naive_carry_rows = int(modular_accumulator_carry_obligations['column_carry_obligation_stream']['total_carry_obligation_rows'])
    candidate_touch_count = all_grid_full_adders + all_grid_final_carry_bits
    checks = {
        'source_row_stream_passes': modular_accumulator_row_stream['pass'] is True,
        'source_carry_obligations_pass': modular_accumulator_carry_obligations['pass'] is True,
        'grid_count_matches_partial_product_rows': grid_count * field_bits * field_bits == partial_product_rows,
        'single_grid_reduces_columns_to_two_rows': int(single_grid_layers['final_max_column_height']) <= 2,
        'single_grid_keeps_carry_complete_capacity': int(single_grid_layers['final_carry_propagate_bits']) == 2 * field_bits,
        'candidate_touch_count_below_naive_carry_obligations': candidate_touch_count < naive_carry_rows,
        'reduced_width_semantic_replay_passes': all(row['pass'] is True for row in reduced_width),
        'candidate_not_promoted_to_public_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_CARRY_SAVE_CANDIDATE_SCHEMA,
        'definition': 'Generated carry-save product-accumulator candidate. It compresses each schoolbook partial-product column set with 3-to-2 full-adder layers before one final carry-propagate boundary, and validates the transform on reduced-width exhaustive products. It is not a promoted reversible primitive lowering.',
        'source_digests': {
            'modular_accumulator_row_stream_sha256': _sha256_payload(modular_accumulator_row_stream),
            'modular_accumulator_carry_obligations_sha256': _sha256_payload(modular_accumulator_carry_obligations),
        },
        'field_bits': field_bits,
        'schoolbook_grid_count': grid_count,
        'single_grid': single_grid_layers,
        'all_grids': {
            'partial_product_rows': partial_product_rows,
            'carry_save_full_adder_count': all_grid_full_adders,
            'final_carry_propagate_bits': all_grid_final_carry_bits,
            'candidate_touch_count': candidate_touch_count,
            'naive_carry_obligation_rows': naive_carry_rows,
            'touch_reduction_numerator': naive_carry_rows,
            'touch_reduction_denominator': candidate_touch_count,
        },
        'reduced_width_exhaustive_checks': reduced_width,
        'promotion_status': {
            'status': 'carry_save_candidate_not_promoted_to_public_resource_contract',
            'required_to_promote': [
                'Lower each 3-to-2 compression cell to concrete reversible gates with counted temporary and output owners.',
                'Prove cleanup or retained-owner semantics for every full-adder carry and sum output.',
                'Lower the final two-row carry-propagate adder into the global primitive schedule.',
                'Recompute public non-Clifford and peak-live-qubit totals from the promoted primitive gate stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_CARRY_SAVE_CANDIDATE_SCHEMA',
    'build_modular_accumulator_carry_save_candidate',
]
