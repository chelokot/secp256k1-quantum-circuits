#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from arithmetic_lowering import (
    SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    SECP256K1_PSEUDO_MERSENNE_SHIFT,
)


MODULAR_ACCUMULATOR_LOWERING_SCHEMA = 'compiler-project-modular-accumulator-lowering-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _schoolbook_column_histogram(field_bits: int) -> Dict[str, int]:
    histogram: Dict[str, int] = {}
    for left_bit in range(int(field_bits)):
        for right_bit in range(int(field_bits)):
            column = left_bit + right_bit
            histogram[str(column)] = histogram.get(str(column), 0) + 1
    return histogram


def _fold_route_for_column(column: int, *, field_bits: int, shift: int, low_term: int) -> Dict[str, Any]:
    if column < int(field_bits):
        return {
            'source_column': int(column),
            'source_region': 'low_product_column',
            'low_accumulator_column': int(column),
            'shifted_accumulator_column': None,
            'low_term_multiplier': 0,
            'requires_second_fold_if_column_overflows_field': False,
        }
    high_column = int(column) - int(field_bits)
    shifted_column = high_column + int(shift)
    return {
        'source_column': int(column),
        'source_region': 'high_product_column',
        'low_accumulator_column': None,
        'shifted_accumulator_column': shifted_column,
        'low_term_multiplier': int(low_term),
        'requires_second_fold_if_column_overflows_field': shifted_column >= int(field_bits),
    }


def build_modular_accumulator_lowering(
    *,
    modular_multiplier_lifecycle: Mapping[str, Any],
    field_bits: int,
    shift: int = SECP256K1_PSEUDO_MERSENNE_SHIFT,
    low_term: int = SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
) -> Dict[str, Any]:
    route_summary = modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']
    histogram = _schoolbook_column_histogram(field_bits)
    routes = [
        _fold_route_for_column(column, field_bits=field_bits, shift=shift, low_term=low_term)
        for column in range(2 * int(field_bits) - 1)
    ]
    low_columns = sum(1 for route in routes if route['source_region'] == 'low_product_column')
    high_columns = sum(1 for route in routes if route['source_region'] == 'high_product_column')
    overflowing_shift_columns = sum(1 for route in routes if route['requires_second_fold_if_column_overflows_field'])
    expected_partial_product_routes = 11 * int(field_bits) * int(field_bits)
    partial_product_routes = int(route_summary['partial_product_routes'])
    product_column_max = int(route_summary['product_column_max'])
    checks = {
        'lifecycle_schema_is_routed': modular_multiplier_lifecycle['schema'] == 'compiler-project-modular-multiplier-lifecycle-v2',
        'lifecycle_passes': modular_multiplier_lifecycle['pass'] is True,
        'partial_product_route_count_matches_eleven_schoolbook_grids': partial_product_routes == expected_partial_product_routes,
        'single_grid_histogram_covers_all_product_columns': (
            sum(histogram.values()) == int(field_bits) * int(field_bits)
            and min(int(column) for column in histogram) == 0
            and max(int(column) for column in histogram) == 2 * int(field_bits) - 2
        ),
        'lifecycle_column_range_matches_schoolbook_histogram': (
            int(route_summary['product_column_min']) == 0
            and product_column_max == max(int(column) for column in histogram)
        ),
        'pseudo_mersenne_fold_routes_every_product_column': len(routes) == 2 * int(field_bits) - 1,
        'fold_routes_preserve_low_and_high_column_counts': low_columns == int(field_bits) and high_columns == int(field_bits) - 1,
        'high_columns_use_checked_secp256k1_fold_constants': (
            int(shift) == SECP256K1_PSEUDO_MERSENNE_SHIFT
            and int(low_term) == SECP256K1_PSEUDO_MERSENNE_LOW_TERM
            and all(route['low_term_multiplier'] == int(low_term) for route in routes if route['source_region'] == 'high_product_column')
        ),
        'materialized_product_accumulator_shortcut_is_rejected': (
            route_summary['materialized_product_accumulator_exceeds_counted_field_slot'] is True
            and int(route_summary['materialized_product_accumulator_bits_required']) == 2 * int(field_bits)
        ),
        'streamed_lowering_is_not_promoted_until_primitive_rows_exist': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_LOWERING_SCHEMA,
        'definition': 'Generated lowering plan for consuming schoolbook partial-product temporary ANDs into a streamed secp256k1 pseudo-Mersenne accumulator without materializing a 512-bit product register inside a 256-bit field slot.',
        'source_digests': {
            'modular_multiplier_lifecycle_sha256': _sha256_payload(modular_multiplier_lifecycle),
        },
        'field_bits': int(field_bits),
        'pseudo_mersenne': {
            'identity': '2^256 = 2^32 + 977 mod p',
            'shift': int(shift),
            'low_term': int(low_term),
        },
        'single_schoolbook_grid': {
            'partial_product_count': int(field_bits) * int(field_bits),
            'column_count': len(histogram),
            'column_histogram_sha256': _sha256_payload(histogram),
            'column_min': 0,
            'column_max': 2 * int(field_bits) - 2,
            'preview_head': [
                {'column': int(column), 'partial_products': int(histogram[str(column)])}
                for column in range(min(8, len(histogram)))
            ],
            'preview_tail': [
                {'column': int(column), 'partial_products': int(histogram[str(column)])}
                for column in range(max(0, len(histogram) - 8), len(histogram))
            ],
        },
        'public_tail_route_count': {
            'schoolbook_grid_count': 11,
            'partial_product_routes': partial_product_routes,
            'expected_partial_product_routes': expected_partial_product_routes,
            'zero_lift_guard_routes': int(route_summary['zero_lift_guard_routes']),
            'unrouted_scratch_targets': int(route_summary['unrouted_scratch_targets']),
        },
        'pseudo_mersenne_fold_routes': {
            'route_count': len(routes),
            'low_product_column_count': low_columns,
            'high_product_column_count': high_columns,
            'overflowing_shift_column_count': overflowing_shift_columns,
            'routes_sha256': _sha256_payload(routes),
            'preview_head': routes[:8],
            'preview_tail': routes[-8:],
        },
        'promotion_status': {
            'status': 'lowering_plan_not_promoted_to_scheduled_primitive_netlist',
            'required_to_promote': [
                'Emit primitive rows that add each routed partial product into a counted streamed accumulator lane.',
                'Emit pseudo-Mersenne fold rows for every high product column using shift=32 and low_term=977.',
                'Emit cleanup or measurement rows that return each temporary AND to zero before reuse.',
                'Recompute non-Clifford and measurement totals from the promoted primitive rows.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_LOWERING_SCHEMA',
    'build_modular_accumulator_lowering',
]
