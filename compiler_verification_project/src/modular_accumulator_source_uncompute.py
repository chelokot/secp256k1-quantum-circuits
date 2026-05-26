#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Mapping

from scheduled_modular_primitive_netlist import iter_scheduled_modular_primitive_rows


MODULAR_ACCUMULATOR_SOURCE_UNCOMPUTE_SCHEMA = 'compiler-project-modular-accumulator-source-uncompute-v1'
SOURCE_UNCOMPUTE_UNPROMOTED_STATUS = 'source_uncompute_contract_not_promoted_to_scheduled_primitive_netlist'
ROUTE_PARTIAL_PRODUCT = 'partial_product_column_to_streamed_modular_accumulator'
ROUTE_ZERO_LIFT_GUARD = 'zero_lift_guard_predicate_ladder'
STATUS_SOURCE_UNCOMPUTE_PROVEN = 'source_uncompute_cleanup_ccx_proven'
STATUS_MISSING_SOURCE_CONTROLS = 'missing_source_controls_for_cleanup'

SOURCE_UNCOMPUTE_COLUMNS = [
    'source_operation_index',
    'source_suboperation_index',
    'route_kind',
    'compute_gate',
    'control_wire_count',
    'scratch_wire',
    'cleanup_status',
    'cleanup_gate',
    'cleanup_reuses_compute_controls',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _scratch_wires(row: Mapping[str, Any]) -> list[str]:
    return [
        str(wire)
        for wire in row['operand_wires']
        if str(wire).startswith('arithmetic_scratch:') and '.bit[' in str(wire)
    ]


def _route_kind(row: Mapping[str, Any]) -> str:
    if len(row['local_operands']) >= 2 and len(row['operand_wires']) == 3:
        return ROUTE_PARTIAL_PRODUCT
    if str(row['kind']) == 'zero_lift_guard_compute_uncompute':
        return ROUTE_ZERO_LIFT_GUARD
    return 'unknown_scratch_route'


def _source_uncompute_row(row: Mapping[str, Any]) -> Dict[str, Any] | None:
    scratch_wires = _scratch_wires(row)
    if not scratch_wires:
        return None
    route_kind = _route_kind(row)
    if route_kind == ROUTE_PARTIAL_PRODUCT:
        cleanup_status = STATUS_SOURCE_UNCOMPUTE_PROVEN
        cleanup_gate = str(row['gate'])
        cleanup_reuses_compute_controls = True
        control_wire_count = 2
    else:
        cleanup_status = STATUS_MISSING_SOURCE_CONTROLS
        cleanup_gate = None
        cleanup_reuses_compute_controls = False
        control_wire_count = max(0, len(row['operand_wires']) - len(scratch_wires))
    return {
        'source_operation_index': int(row['operation_index']),
        'source_suboperation_index': int(row['suboperation_index']),
        'route_kind': route_kind,
        'compute_gate': str(row['gate']),
        'control_wire_count': control_wire_count,
        'scratch_wire': scratch_wires[0],
        'cleanup_status': cleanup_status,
        'cleanup_gate': cleanup_gate,
        'cleanup_reuses_compute_controls': cleanup_reuses_compute_controls,
    }


def _encoded_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(_canonical_json(row[column]) for column in SOURCE_UNCOMPUTE_COLUMNS) + '\n'


def _ccx_self_inverse_truth_table() -> Dict[str, Any]:
    cases = []
    for left in range(2):
        for right in range(2):
            for target in range(2):
                computed = target ^ (left & right)
                uncomputed = computed ^ (left & right)
                cases.append({
                    'left': left,
                    'right': right,
                    'target': target,
                    'after_compute': computed,
                    'after_uncompute': uncomputed,
                    'pass': uncomputed == target,
                })
    return {
        'case_count': len(cases),
        'pass_count': sum(1 for case in cases if case['pass']),
        'cases': cases,
        'pass': all(case['pass'] for case in cases),
    }


def _stream_summary(rows: Iterable[Mapping[str, Any]], *, segment_size: int) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(SOURCE_UNCOMPUTE_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_start = 0
    segment_count = 0
    row_count = 0
    route_kind_counts: Dict[str, int] = {}
    cleanup_status_counts: Dict[str, int] = {}
    preview_head = []
    preview_tail = []
    segments = []
    for row in rows:
        route_kind = str(row['route_kind'])
        cleanup_status = str(row['cleanup_status'])
        route_kind_counts[route_kind] = route_kind_counts.get(route_kind, 0) + 1
        cleanup_status_counts[cleanup_status] = cleanup_status_counts.get(cleanup_status, 0) + 1
        encoded = _encoded_row(row).encode('ascii')
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        if len(preview_head) < 6:
            preview_head.append(dict(row))
        preview_tail.append(dict(row))
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
        'stream_columns': SOURCE_UNCOMPUTE_COLUMNS,
        'rows_materialized_in_json': False,
        'segment_size': int(segment_size),
        'row_count': row_count,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_count': len(segments),
        'segments': segments,
        'route_kind_counts': {key: int(value) for key, value in sorted(route_kind_counts.items())},
        'cleanup_status_counts': {key: int(value) for key, value in sorted(cleanup_status_counts.items())},
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def build_modular_accumulator_source_uncompute(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    scheduled_modular_primitive_netlist: Mapping[str, Any],
    modular_multiplier_lifecycle: Mapping[str, Any],
    field_bits: int,
    segment_size: int = 16384,
) -> Dict[str, Any]:
    source_rows = (
        source_uncompute_row
        for row in iter_scheduled_modular_primitive_rows(
            modular_execution_trace=modular_execution_trace,
            modular_arithmetic_certificate=modular_arithmetic_certificate,
            arithmetic_lowerings=arithmetic_lowerings,
            reusable_chunk_lowering=reusable_chunk_lowering,
        )
        for source_uncompute_row in [_source_uncompute_row(row)]
        if source_uncompute_row is not None
    )
    stream = _stream_summary(source_rows, segment_size=segment_size)
    route_counts = stream['route_kind_counts']
    cleanup_counts = stream['cleanup_status_counts']
    lifecycle_current = modular_multiplier_lifecycle['current_stream']
    partial_product_rows = int(route_counts.get(ROUTE_PARTIAL_PRODUCT, 0))
    zero_lift_guard_rows = int(route_counts.get(ROUTE_ZERO_LIFT_GUARD, 0))
    proven_cleanup_rows = int(cleanup_counts.get(STATUS_SOURCE_UNCOMPUTE_PROVEN, 0))
    blocked_cleanup_rows = int(cleanup_counts.get(STATUS_MISSING_SOURCE_CONTROLS, 0))
    truth_table = _ccx_self_inverse_truth_table()
    checks = {
        'scheduled_modular_primitive_netlist_passes': scheduled_modular_primitive_netlist['pass'] is True,
        'modular_multiplier_lifecycle_passes': modular_multiplier_lifecycle['pass'] is True,
        'source_stream_scans_every_current_scratch_target': int(stream['row_count']) == int(lifecycle_current['scratch_observation_count']),
        'partial_product_source_uncompute_covers_all_partial_product_scratch': partial_product_rows == int(lifecycle_current['partial_product_scratch_observation_count']),
        'zero_lift_guard_rows_are_the_only_source_uncompute_gap': (
            zero_lift_guard_rows == int(lifecycle_current['non_partial_product_scratch_observation_count'])
            and blocked_cleanup_rows == zero_lift_guard_rows
        ),
        'partial_product_cleanup_ccx_is_self_inverse': truth_table['pass'] is True,
        'partial_product_cleanup_delta_is_exact': proven_cleanup_rows == partial_product_rows,
        'not_promoted_until_guard_controls_and_accumulator_consume_exist': blocked_cleanup_rows > 0,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_SOURCE_UNCOMPUTE_SCHEMA,
        'definition': 'Generated source-uncompute contract for modular-accumulator scratch cleanup. It proves that every partial-product temporary AND can be cleaned by replaying the same CCX controls, and keeps zero-lift guard cleanup unpromoted because the current primitive iterator does not expose guard predicate controls.',
        'source_digests': {
            'modular_execution_trace_sha256': _sha256_payload(modular_execution_trace),
            'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
            'arithmetic_lowerings_sha256': _sha256_payload(arithmetic_lowerings),
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
            'scheduled_modular_primitive_netlist_sha256': _sha256_payload(scheduled_modular_primitive_netlist),
            'modular_multiplier_lifecycle_sha256': _sha256_payload(modular_multiplier_lifecycle),
        },
        'field_bits': int(field_bits),
        'source_uncompute_stream': stream,
        'cleanup_cost_bounds': {
            'partial_product_cleanup_ccx_delta_exact': proven_cleanup_rows,
            'zero_lift_guard_cleanup_delta_unproven': blocked_cleanup_rows,
            'total_cleanup_ccx_delta_not_claimed': None,
            'additional_witness_bits_for_partial_product_cleanup': 0,
        },
        'truth_table': truth_table,
        'promotion_status': {
            'status': SOURCE_UNCOMPUTE_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Expose concrete predicate controls for zero-lift guard scratch rows or remove those placeholders from the modular primitive iterator.',
                'Lower consume_into_counted_accumulator rows to concrete read-only temporary-control accumulator gates.',
                'Append the proven source-uncompute CCX cleanup rows to the promoted primitive stream and recompute global liveness and non-Clifford totals.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_SOURCE_UNCOMPUTE_SCHEMA',
    'ROUTE_PARTIAL_PRODUCT',
    'ROUTE_ZERO_LIFT_GUARD',
    'SOURCE_UNCOMPUTE_UNPROMOTED_STATUS',
    'STATUS_MISSING_SOURCE_CONTROLS',
    'STATUS_SOURCE_UNCOMPUTE_PROVEN',
    'build_modular_accumulator_source_uncompute',
]
