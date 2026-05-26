#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from itertools import chain
from typing import Any, Dict, Iterable, Mapping


MODULAR_ACCUMULATOR_SCRATCH_SCHEDULE_SCHEMA = 'compiler-project-modular-accumulator-scratch-schedule-v1'
SCRATCH_SCHEDULE_COLUMNS = [
    'event_index',
    'triplet_index',
    'phase_index',
    'phase',
    'route_kind',
    'source_column',
    'temporary_live_after',
    'destination_owner',
    'promotion_status',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _encoded_stream_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(_canonical_json(row[column]) for column in SCRATCH_SCHEDULE_COLUMNS) + '\n'


def _partial_product_triplets(*, field_bits: int, grid_count: int) -> Iterable[Dict[str, Any]]:
    triplet_index = 0
    for _grid_index in range(grid_count):
        for left_bit in range(field_bits):
            for right_bit in range(field_bits):
                yield {
                    'triplet_index': triplet_index,
                    'route_kind': 'partial_product_column_to_streamed_modular_accumulator',
                    'source_column': left_bit + right_bit,
                    'destination_owner': 'streamed_product_accumulator_column_space',
                }
                triplet_index += 1


def _guard_triplets(*, start_triplet_index: int, guard_count: int) -> Iterable[Dict[str, Any]]:
    for guard_index in range(guard_count):
        yield {
            'triplet_index': start_triplet_index + guard_index,
            'route_kind': 'zero_lift_guard_predicate_ladder',
            'source_column': 0,
            'destination_owner': 'guard_ladder_predicate_workspace',
        }


def _schedule_rows(triplets: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    phases = [
        ('temporary_and_compute', 1),
        ('consume_into_counted_owner', 1),
        ('cleanup_or_measure_uncompute', 0),
    ]
    event_index = 0
    for triplet in triplets:
        for phase_index, (phase, temporary_live_after) in enumerate(phases):
            yield {
                'event_index': event_index,
                'triplet_index': int(triplet['triplet_index']),
                'phase_index': phase_index,
                'phase': phase,
                'route_kind': str(triplet['route_kind']),
                'source_column': int(triplet['source_column']),
                'temporary_live_after': temporary_live_after,
                'destination_owner': str(triplet['destination_owner']),
                'promotion_status': 'scratch_liveness_schedule_not_semantic_gate_lowering',
            }
            event_index += 1


def _stream_summary(rows: Iterable[Dict[str, Any]], *, segment_size: int) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(SCRATCH_SCHEDULE_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_start = 0
    segment_count = 0
    event_count = 0
    peak_temporary_live = 0
    phase_counts: Dict[str, int] = {}
    route_kind_counts: Dict[str, int] = {}
    preview_head = []
    preview_tail = []
    segments = []
    for row in rows:
        phase = str(row['phase'])
        route_kind = str(row['route_kind'])
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        route_kind_counts[route_kind] = route_kind_counts.get(route_kind, 0) + 1
        peak_temporary_live = max(peak_temporary_live, int(row['temporary_live_after']))
        encoded = _encoded_stream_row(row).encode('ascii')
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        if len(preview_head) < 6:
            preview_head.append(row)
        preview_tail.append(row)
        if len(preview_tail) > 6:
            preview_tail.pop(0)
        event_count += 1
        segment_count += 1
        if segment_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'event_start': segment_start,
                'event_end_exclusive': event_count,
                'event_count': segment_count,
                'sha256': segment_digest.hexdigest(),
            })
            segment_digest = hashlib.sha256()
            segment_start = event_count
            segment_count = 0
    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'event_start': segment_start,
            'event_end_exclusive': event_count,
            'event_count': segment_count,
            'sha256': segment_digest.hexdigest(),
        })
    return {
        'stream_columns': SCRATCH_SCHEDULE_COLUMNS,
        'events_materialized_in_json': False,
        'segment_size': int(segment_size),
        'event_count': event_count,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_count': len(segments),
        'segments': segments,
        'phase_counts': {key: int(value) for key, value in sorted(phase_counts.items())},
        'route_kind_counts': {key: int(value) for key, value in sorted(route_kind_counts.items())},
        'peak_temporary_live_qubits': peak_temporary_live,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def build_modular_accumulator_scratch_schedule(
    *,
    modular_multiplier_lifecycle: Mapping[str, Any],
    modular_accumulator_capacity_certificate: Mapping[str, Any],
    field_bits: int,
    segment_size: int = 16384,
) -> Dict[str, Any]:
    lifecycle_stream = modular_multiplier_lifecycle['candidate_lifecycle_stream']
    route_summary = lifecycle_stream['route_summary']
    capacity_obligations = {
        str(row['owner_id']): row
        for row in modular_accumulator_capacity_certificate['owner_capacity_obligations']
    }
    partial_product_routes = int(route_summary['partial_product_routes'])
    guard_routes = int(route_summary['zero_lift_guard_routes'])
    grid_count = partial_product_routes // (int(field_bits) * int(field_bits))
    triplets = chain(
        _partial_product_triplets(field_bits=int(field_bits), grid_count=grid_count),
        _guard_triplets(start_triplet_index=partial_product_routes, guard_count=guard_routes),
    )
    stream = _stream_summary(_schedule_rows(triplets), segment_size=segment_size)
    triplet_count = partial_product_routes + guard_routes
    checks = {
        'source_lifecycle_passes': modular_multiplier_lifecycle['pass'] is True,
        'source_capacity_certificate_passes': modular_accumulator_capacity_certificate['pass'] is True,
        'triplet_count_matches_lifecycle_routes': triplet_count == int(lifecycle_stream['temporary_and_compute_events']),
        'schedule_has_three_adjacent_events_per_triplet': stream['event_count'] == triplet_count * 3,
        'phase_counts_match_triplets': all(int(stream['phase_counts'][phase]) == triplet_count for phase in ('temporary_and_compute', 'consume_into_counted_owner', 'cleanup_or_measure_uncompute')),
        'route_counts_match_lifecycle_routes': (
            int(stream['route_kind_counts']['partial_product_column_to_streamed_modular_accumulator']) == partial_product_routes * 3
            and int(stream['route_kind_counts']['zero_lift_guard_predicate_ladder']) == guard_routes * 3
        ),
        'serialized_temporary_peak_matches_capacity_certificate': (
            int(stream['peak_temporary_live_qubits']) == int(capacity_obligations['temporary_and_target_wire']['serialized_candidate_peak_logical_qubits']) == 1
        ),
        'schedule_remains_unpromoted_until_consume_gate_semantics_exist': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_SCRATCH_SCHEDULE_SCHEMA,
        'definition': 'Generated serialized scratch lifecycle schedule for modular accumulator obligations. It proves the adjacent compute-consume-cleanup ordering and temporary-wire liveness peak for the schedule shape, but does not claim semantic lowering of the consume or fold operations.',
        'source_digests': {
            'modular_multiplier_lifecycle_sha256': _sha256_payload(modular_multiplier_lifecycle),
            'modular_accumulator_capacity_certificate_sha256': _sha256_payload(modular_accumulator_capacity_certificate),
        },
        'field_bits': int(field_bits),
        'triplet_count': triplet_count,
        'partial_product_triplets': partial_product_routes,
        'guard_triplets': guard_routes,
        'schedule_stream': stream,
        'liveness_certificate': {
            'schedule_model': 'serialized_adjacent_compute_consume_cleanup_triplets',
            'obligation_order_temporary_peak_qubits': int(capacity_obligations['temporary_and_target_wire']['obligation_order_peak_logical_qubits']),
            'serialized_schedule_temporary_peak_qubits': int(stream['peak_temporary_live_qubits']),
            'semantic_gate_lowering_proven': False,
        },
        'promotion_status': {
            'status': 'scratch_schedule_not_promoted_to_public_resource_contract',
            'required_to_promote': [
                'Replace consume_into_counted_owner schedule rows with concrete reversible accumulator-update gates.',
                'Bind those gates to product-column and pseudo-Mersenne fold semantics.',
                'Rebuild public liveness from the promoted primitive gate stream, not from this schedule-shape certificate.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_SCRATCH_SCHEDULE_SCHEMA',
    'build_modular_accumulator_scratch_schedule',
]
