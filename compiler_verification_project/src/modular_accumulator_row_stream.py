#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from itertools import chain
from typing import Any, Dict, Iterable, Mapping

from arithmetic_lowering import (
    SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    SECP256K1_PSEUDO_MERSENNE_SHIFT,
)


MODULAR_ACCUMULATOR_ROW_STREAM_SCHEMA = 'compiler-project-modular-accumulator-row-stream-v1'
ACCUMULATOR_ROW_STREAM_COLUMNS = [
    'row_index',
    'role',
    'schoolbook_grid_index',
    'left_bit',
    'right_bit',
    'source_column',
    'destination_column',
    'fold_low_column',
    'fold_shifted_column',
    'low_term_multiplier',
    'route_kind',
    'capacity_owner',
    'requires_followup_lowering',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _encoded_stream_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(_canonical_json(row[column]) for column in ACCUMULATOR_ROW_STREAM_COLUMNS) + '\n'


def _partial_product_rows(*, field_bits: int, grid_count: int) -> Iterable[Dict[str, Any]]:
    for grid_index in range(grid_count):
        for left_bit in range(field_bits):
            for right_bit in range(field_bits):
                column = left_bit + right_bit
                yield {
                    'role': 'partial_product_accumulator_consume',
                    'schoolbook_grid_index': grid_index,
                    'left_bit': left_bit,
                    'right_bit': right_bit,
                    'source_column': column,
                    'destination_column': column,
                    'fold_low_column': None,
                    'fold_shifted_column': None,
                    'low_term_multiplier': 0,
                    'route_kind': 'partial_product_column_to_streamed_modular_accumulator',
                    'capacity_owner': 'streamed_product_accumulator_column_space',
                    'requires_followup_lowering': True,
                }


def _zero_lift_guard_rows(*, guard_count: int) -> Iterable[Dict[str, Any]]:
    for guard_index in range(guard_count):
        yield {
            'role': 'zero_lift_guard_consume_cleanup',
            'schoolbook_grid_index': None,
            'left_bit': guard_index,
            'right_bit': None,
            'source_column': 0,
            'destination_column': 0,
            'fold_low_column': None,
            'fold_shifted_column': None,
            'low_term_multiplier': 0,
            'route_kind': 'zero_lift_guard_predicate_ladder',
            'capacity_owner': 'guard_ladder_predicate_workspace',
            'requires_followup_lowering': True,
        }


def _cleanup_rows(*, field_bits: int, grid_count: int, guard_count: int) -> Iterable[Dict[str, Any]]:
    for grid_index in range(grid_count):
        for left_bit in range(field_bits):
            for right_bit in range(field_bits):
                column = left_bit + right_bit
                yield {
                    'role': 'temporary_and_cleanup',
                    'schoolbook_grid_index': grid_index,
                    'left_bit': left_bit,
                    'right_bit': right_bit,
                    'source_column': column,
                    'destination_column': None,
                    'fold_low_column': None,
                    'fold_shifted_column': None,
                    'low_term_multiplier': 0,
                    'route_kind': 'partial_product_column_to_streamed_modular_accumulator',
                    'capacity_owner': 'temporary_and_target_wire',
                    'requires_followup_lowering': True,
                }
    for guard_index in range(guard_count):
        yield {
            'role': 'temporary_and_cleanup',
            'schoolbook_grid_index': None,
            'left_bit': guard_index,
            'right_bit': None,
            'source_column': 0,
            'destination_column': None,
            'fold_low_column': None,
            'fold_shifted_column': None,
            'low_term_multiplier': 0,
            'route_kind': 'zero_lift_guard_predicate_ladder',
            'capacity_owner': 'temporary_and_target_wire',
            'requires_followup_lowering': True,
        }


def _fold_rows(
    *,
    field_bits: int,
    grid_count: int,
    shift: int,
    low_term: int,
) -> Iterable[Dict[str, Any]]:
    for grid_index in range(grid_count):
        for source_column in range(2 * field_bits - 1):
            if source_column < field_bits:
                yield {
                    'role': 'pseudo_mersenne_low_column_fold',
                    'schoolbook_grid_index': grid_index,
                    'left_bit': None,
                    'right_bit': None,
                    'source_column': source_column,
                    'destination_column': source_column,
                    'fold_low_column': source_column,
                    'fold_shifted_column': None,
                    'low_term_multiplier': 0,
                    'route_kind': 'pseudo_mersenne_fold',
                    'capacity_owner': 'streamed_modular_accumulator_field_lane',
                    'requires_followup_lowering': True,
                }
            else:
                high_column = source_column - field_bits
                shifted_column = high_column + shift
                yield {
                    'role': 'pseudo_mersenne_high_column_fold',
                    'schoolbook_grid_index': grid_index,
                    'left_bit': None,
                    'right_bit': None,
                    'source_column': source_column,
                    'destination_column': shifted_column,
                    'fold_low_column': None,
                    'fold_shifted_column': shifted_column,
                    'low_term_multiplier': low_term,
                    'route_kind': 'pseudo_mersenne_fold',
                    'capacity_owner': 'streamed_modular_accumulator_field_lane',
                    'requires_followup_lowering': True,
                }


def _stream_summary(rows: Iterable[Dict[str, Any]], *, segment_size: int) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(ACCUMULATOR_ROW_STREAM_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_start = 0
    segment_count = 0
    row_count = 0
    role_counts: Dict[str, int] = {}
    route_kind_counts: Dict[str, int] = {}
    capacity_owner_counts: Dict[str, int] = {}
    max_source_column = None
    max_destination_column = None
    preview_head = []
    preview_tail = []
    segments = []
    for row_without_index in rows:
        row = {'row_index': row_count, **row_without_index}
        role = str(row['role'])
        route_kind = str(row['route_kind'])
        capacity_owner = str(row['capacity_owner'])
        role_counts[role] = role_counts.get(role, 0) + 1
        route_kind_counts[route_kind] = route_kind_counts.get(route_kind, 0) + 1
        capacity_owner_counts[capacity_owner] = capacity_owner_counts.get(capacity_owner, 0) + 1
        if row['source_column'] is not None:
            source_column = int(row['source_column'])
            max_source_column = source_column if max_source_column is None else max(max_source_column, source_column)
        if row['destination_column'] is not None:
            destination_column = int(row['destination_column'])
            max_destination_column = destination_column if max_destination_column is None else max(max_destination_column, destination_column)
        encoded = _encoded_stream_row(row).encode('ascii')
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        if len(preview_head) < 6:
            preview_head.append(row)
        preview_tail.append(row)
        if len(preview_tail) > 6:
            preview_tail.pop(0)
        row_count += 1
        segment_count += 1
        if segment_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'row_start': segment_start,
                'row_end_exclusive': row_count,
                'row_count': segment_count,
                'sha256': segment_digest.hexdigest(),
            })
            segment_digest = hashlib.sha256()
            segment_start = row_count
            segment_count = 0
    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'row_start': segment_start,
            'row_end_exclusive': row_count,
            'row_count': segment_count,
            'sha256': segment_digest.hexdigest(),
        })
    return {
        'stream_columns': ACCUMULATOR_ROW_STREAM_COLUMNS,
        'rows_materialized_in_json': False,
        'segment_size': int(segment_size),
        'row_count': row_count,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_count': len(segments),
        'segments': segments,
        'role_counts': {key: int(value) for key, value in sorted(role_counts.items())},
        'route_kind_counts': {key: int(value) for key, value in sorted(route_kind_counts.items())},
        'capacity_owner_counts': {key: int(value) for key, value in sorted(capacity_owner_counts.items())},
        'max_source_column': max_source_column,
        'max_destination_column': max_destination_column,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def build_modular_accumulator_row_stream(
    *,
    modular_multiplier_lifecycle: Mapping[str, Any],
    modular_accumulator_lowering: Mapping[str, Any],
    field_bits: int,
    segment_size: int = 16384,
) -> Dict[str, Any]:
    public_routes = modular_accumulator_lowering['public_tail_route_count']
    grid_count = int(public_routes['schoolbook_grid_count'])
    partial_product_routes = int(public_routes['partial_product_routes'])
    guard_routes = int(public_routes['zero_lift_guard_routes'])
    fold_route_count = int(modular_accumulator_lowering['pseudo_mersenne_fold_routes']['route_count'])
    shift = int(modular_accumulator_lowering['pseudo_mersenne']['shift'])
    low_term = int(modular_accumulator_lowering['pseudo_mersenne']['low_term'])
    rows = chain(
        _partial_product_rows(field_bits=int(field_bits), grid_count=grid_count),
        _zero_lift_guard_rows(guard_count=guard_routes),
        _fold_rows(field_bits=int(field_bits), grid_count=grid_count, shift=shift, low_term=low_term),
        _cleanup_rows(field_bits=int(field_bits), grid_count=grid_count, guard_count=guard_routes),
    )
    stream = _stream_summary(rows, segment_size=segment_size)
    expected_partial_rows = grid_count * int(field_bits) * int(field_bits)
    expected_fold_rows = grid_count * (2 * int(field_bits) - 1)
    expected_cleanup_rows = partial_product_routes + guard_routes
    role_counts = stream['role_counts']
    checks = {
        'source_lowering_passes': modular_accumulator_lowering['pass'] is True,
        'source_lifecycle_passes': modular_multiplier_lifecycle['pass'] is True,
        'source_lifecycle_stream_matches_lowering_routes': (
            int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['partial_product_routes']) == partial_product_routes
            and int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['zero_lift_guard_routes']) == guard_routes
            and int(modular_multiplier_lifecycle['candidate_lifecycle_stream']['route_summary']['unrouted_scratch_targets']) == 0
        ),
        'partial_product_rows_expand_all_routed_products': (
            expected_partial_rows == partial_product_routes
            and int(role_counts['partial_product_accumulator_consume']) == partial_product_routes
        ),
        'guard_rows_expand_all_guard_routes': int(role_counts['zero_lift_guard_consume_cleanup']) == guard_routes,
        'fold_rows_expand_every_grid_column': (
            int(role_counts['pseudo_mersenne_low_column_fold'])
            + int(role_counts['pseudo_mersenne_high_column_fold'])
            == grid_count * fold_route_count
            == expected_fold_rows
        ),
        'cleanup_rows_cover_every_temporary_and_target': (
            int(role_counts['temporary_and_cleanup']) == expected_cleanup_rows
        ),
        'row_stream_rejects_hidden_512_bit_field_slot': (
            stream['max_source_column'] == 2 * int(field_bits) - 2
            and stream['max_destination_column'] == 2 * int(field_bits) - 2
            and modular_accumulator_lowering['checks']['materialized_product_accumulator_shortcut_is_rejected'] is True
        ),
        'row_stream_remains_unpromoted_until_gate_lowering_exists': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_ROW_STREAM_SCHEMA,
        'definition': 'Generated accumulator route row stream for the modular multiplier boundary. It expands schoolbook partial products, zero-lift guards, pseudo-Mersenne fold obligations, and temporary cleanup obligations into deterministic segment-hashed rows, but it is not yet the promoted Clifford-complete primitive gate netlist.',
        'source_digests': {
            'modular_multiplier_lifecycle_sha256': _sha256_payload(modular_multiplier_lifecycle),
            'modular_accumulator_lowering_sha256': _sha256_payload(modular_accumulator_lowering),
        },
        'field_bits': int(field_bits),
        'row_stream': stream,
        'expanded_counts': {
            'schoolbook_grid_count': grid_count,
            'partial_product_consume_rows': partial_product_routes,
            'zero_lift_guard_rows': guard_routes,
            'pseudo_mersenne_fold_rows': expected_fold_rows,
            'temporary_cleanup_rows': expected_cleanup_rows,
            'total_rows': int(stream['row_count']),
        },
        'known_cost_status': {
            'promoted_to_public_resource_contract': False,
            'exact_non_clifford_delta': None,
            'exact_measurement_delta': None,
            'reason': 'Rows are route and lifecycle obligations. Promotion still requires replacing each role row with concrete primitive Clifford/CCX/measurement gates and deriving liveness from that flat stream.',
        },
        'promotion_status': {
            'status': 'row_stream_obligations_not_promoted_to_scheduled_primitive_netlist',
            'required_to_promote': [
                'Lower partial_product_accumulator_consume rows to concrete reversible accumulator update gates.',
                'Lower pseudo_mersenne_*_fold rows to concrete field-lane fold gates with carry/cleanup wires assigned to counted owners.',
                'Lower temporary_and_cleanup rows to exact uncompute or measurement-cleanup primitive gates.',
                'Rebuild scheduled_modular_primitive_netlist from those primitive gates and derive non-Clifford, measurements, and peak liveness from the rebuilt stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'ACCUMULATOR_ROW_STREAM_COLUMNS',
    'MODULAR_ACCUMULATOR_ROW_STREAM_SCHEMA',
    'build_modular_accumulator_row_stream',
]
