#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from scheduled_modular_primitive_netlist import iter_scheduled_modular_primitive_rows


MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA = 'compiler-project-modular-multiplier-lifecycle-v1'
LIFECYCLE_STREAM_COLUMNS = [
    'event_index',
    'source_operation_index',
    'source_suboperation_index',
    'role',
    'scratch_wire',
    'source_gate',
    'owner_id',
    'target',
    'block',
    'consume_destination_owner_id',
    'consume_destination_target',
    'route_status',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _scratch_prefix(wire_id: str) -> str | None:
    if not wire_id.startswith('arithmetic_scratch:') or '.bit[' not in wire_id:
        return None
    return wire_id[:wire_id.index('.bit[')]


def _encoded_stream_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(_canonical_json(row[column]) for column in LIFECYCLE_STREAM_COLUMNS) + '\n'


def _build_candidate_stream_summary(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    segment_size: int,
) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(LIFECYCLE_STREAM_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_start = 0
    segment_count = 0
    compute_events = 0
    consume_events = 0
    cleanup_events = 0
    event_index = 0
    segments = []
    preview_head = []
    preview_tail = []
    prefix_counts: Dict[str, int] = {}

    for primitive_row in iter_scheduled_modular_primitive_rows(
        modular_execution_trace=modular_execution_trace,
        modular_arithmetic_certificate=modular_arithmetic_certificate,
        arithmetic_lowerings=arithmetic_lowerings,
        reusable_chunk_lowering=reusable_chunk_lowering,
    ):
        operand_wires = [str(wire) for wire in primitive_row['operand_wires']]
        scratch_wires = [wire for wire in operand_wires if _scratch_prefix(wire) is not None]
        for scratch_wire in scratch_wires:
            prefix = _scratch_prefix(scratch_wire)
            if prefix is None:
                raise ValueError(f'unexpected non-scratch wire in scratch stream: {scratch_wire}')
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            event_templates = [
                {
                    'role': 'temporary_and_compute',
                    'consume_destination_owner_id': None,
                    'consume_destination_target': None,
                    'route_status': 'observed_current_stream',
                },
                {
                    'role': 'consume_into_counted_accumulator',
                    'consume_destination_owner_id': str(primitive_row['owner_id']),
                    'consume_destination_target': str(primitive_row['target']),
                    'route_status': 'candidate_route_requires_physical_accumulator_bit_mapping',
                },
                {
                    'role': 'cleanup_or_measure_uncompute',
                    'consume_destination_owner_id': None,
                    'consume_destination_target': None,
                    'route_status': 'candidate_cleanup_requires_lowering',
                },
            ]
            for template in event_templates:
                lifecycle_row = {
                    'event_index': event_index,
                    'source_operation_index': int(primitive_row['operation_index']),
                    'source_suboperation_index': int(primitive_row['suboperation_index']),
                    'role': template['role'],
                    'scratch_wire': scratch_wire,
                    'source_gate': str(primitive_row['gate']),
                    'owner_id': str(primitive_row['owner_id']),
                    'target': str(primitive_row['target']),
                    'block': str(primitive_row['block']),
                    'consume_destination_owner_id': template['consume_destination_owner_id'],
                    'consume_destination_target': template['consume_destination_target'],
                    'route_status': template['route_status'],
                }
                if template['role'] == 'temporary_and_compute':
                    compute_events += 1
                elif template['role'] == 'consume_into_counted_accumulator':
                    consume_events += 1
                elif template['role'] == 'cleanup_or_measure_uncompute':
                    cleanup_events += 1
                encoded = _encoded_stream_row(lifecycle_row).encode('ascii')
                stream_digest.update(encoded)
                segment_digest.update(encoded)
                if len(preview_head) < 6:
                    preview_head.append(lifecycle_row)
                preview_tail.append(lifecycle_row)
                if len(preview_tail) > 6:
                    preview_tail.pop(0)
                event_index += 1
                segment_count += 1
                if segment_count == segment_size:
                    segments.append({
                        'segment_index': len(segments),
                        'event_start': segment_start,
                        'event_end_exclusive': event_index,
                        'event_count': segment_count,
                        'sha256': segment_digest.hexdigest(),
                    })
                    segment_digest = hashlib.sha256()
                    segment_start = event_index
                    segment_count = 0

    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'event_start': segment_start,
            'event_end_exclusive': event_index,
            'event_count': segment_count,
            'sha256': segment_digest.hexdigest(),
        })

    return {
        'stream_columns': LIFECYCLE_STREAM_COLUMNS,
        'operation_rows_materialized_in_json': False,
        'segment_size': int(segment_size),
        'event_count': event_index,
        'temporary_and_compute_events': compute_events,
        'consume_events': consume_events,
        'cleanup_events': cleanup_events,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_count': len(segments),
        'segments': segments,
        'scratch_prefix_counts_sha256': _sha256_payload(prefix_counts),
        'top_scratch_prefixes': [
            {'scratch_prefix': prefix, 'observation_count': int(count)}
            for prefix, count in sorted(prefix_counts.items(), key=lambda item: (-item[1], item[0]))[:16]
        ],
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def build_modular_multiplier_lifecycle(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    scheduled_modular_primitive_netlist: Mapping[str, Any],
    modular_primitive_wire_audit: Mapping[str, Any],
    field_bits: int,
    segment_size: int = 16384,
) -> Dict[str, Any]:
    scratch_observations = int(modular_primitive_wire_audit['arithmetic_scratch_wire_observation_count'])
    scratch_unique = int(modular_primitive_wire_audit['arithmetic_scratch_unique_wire_count'])
    scratch_single_use = int(modular_primitive_wire_audit['arithmetic_scratch_single_use_wire_count'])
    scratch_cleanup = int(modular_primitive_wire_audit['arithmetic_scratch_cleanup_observation_count'])
    scratch_abandoned = int(modular_primitive_wire_audit['arithmetic_scratch_abandoned_garbage_count'])
    partial_product_prefixes = [
        row
        for row in modular_primitive_wire_audit['top_synthetic_scratch_prefixes']
        if str(row['scratch_prefix']).endswith('partial_product_grid')
    ]
    partial_product_observations = sum(int(row['observation_count']) for row in partial_product_prefixes)
    non_partial_product_observations = scratch_observations - partial_product_observations
    candidate_stream = _build_candidate_stream_summary(
        modular_execution_trace=modular_execution_trace,
        modular_arithmetic_certificate=modular_arithmetic_certificate,
        arithmetic_lowerings=arithmetic_lowerings,
        reusable_chunk_lowering=reusable_chunk_lowering,
        segment_size=segment_size,
    )
    streamed_candidate = {
        'model': 'serial_temporary_and_consume_cleanup',
        'status': 'candidate_not_promoted_to_public_resource_contract',
        'temporary_and_compute_events': scratch_observations,
        'required_consume_events': scratch_observations,
        'required_cleanup_events': scratch_observations,
        'peak_temporary_and_wires_if_serialized': 1 if scratch_observations else 0,
        'additional_measurements_for_measured_cleanup': scratch_observations,
        'non_clifford_delta_unproven_until_consume_cleanup_lowering_exists': None,
        'notes': [
            'This is a generated target lifecycle for closing the current gap, not a claimed public lowering.',
            'Promotion requires replacing each producer-only scratch target with a compute-consume-cleanup sequence that updates a counted accumulator wire and returns the temporary AND wire to zero.',
        ],
    }
    checks = {
        'wire_audit_binds_current_scheduled_netlist': (
            modular_primitive_wire_audit['source_digests']['scheduled_modular_primitive_netlist_sha256']
            == _sha256_payload(scheduled_modular_primitive_netlist)
        ),
        'candidate_stream_binds_current_sources': (
            scheduled_modular_primitive_netlist['source_digests']['modular_execution_trace_sha256'] == _sha256_payload(modular_execution_trace)
            and scheduled_modular_primitive_netlist['source_digests']['modular_arithmetic_certificate_sha256'] == _sha256_payload(modular_arithmetic_certificate)
            and scheduled_modular_primitive_netlist['source_digests']['arithmetic_lowerings_sha256'] == _sha256_payload(arithmetic_lowerings)
            and scheduled_modular_primitive_netlist['source_digests']['reusable_chunk_lowering_sha256'] == _sha256_payload(reusable_chunk_lowering)
        ),
        'current_scratch_is_single_use_ccx_target_only': (
            modular_primitive_wire_audit['checks']['synthetic_scratch_wires_are_single_use_ccx_targets'] is True
            and scratch_observations == scratch_unique == scratch_single_use
        ),
        'current_scratch_has_no_cleanup_or_counted_capacity': (
            modular_primitive_wire_audit['checks']['synthetic_scratch_wires_have_cleanup_or_counted_capacity'] is False
            and scratch_cleanup == 0
            and scratch_abandoned == scratch_observations
        ),
        'streamed_candidate_covers_every_current_scratch_target': (
            streamed_candidate['temporary_and_compute_events']
            == streamed_candidate['required_consume_events']
            == streamed_candidate['required_cleanup_events']
            == scratch_observations
        ),
        'candidate_stream_covers_every_current_scratch_target': (
            candidate_stream['temporary_and_compute_events'] == scratch_observations
            and candidate_stream['consume_events'] == scratch_observations
            and candidate_stream['cleanup_events'] == scratch_observations
            and candidate_stream['event_count'] == scratch_observations * 3
        ),
        'streamed_candidate_peak_is_serial_constant': streamed_candidate['peak_temporary_and_wires_if_serialized'] <= 1,
        'not_promoted_until_consume_cleanup_lowering_exists': streamed_candidate['status'] != 'promoted_public_resource_contract',
    }
    return {
        'schema': MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA,
        'definition': 'Generated lifecycle audit for modular-multiplier temporary-AND scratch targets. It distinguishes the current abandoned scratch placeholders from the compute-consume-cleanup lifecycle required by a physical primitive lowering.',
        'source_digests': {
            'modular_execution_trace_sha256': _sha256_payload(modular_execution_trace),
            'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
            'arithmetic_lowerings_sha256': _sha256_payload(arithmetic_lowerings),
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
            'scheduled_modular_primitive_netlist_sha256': _sha256_payload(scheduled_modular_primitive_netlist),
            'modular_primitive_wire_audit_sha256': _sha256_payload(modular_primitive_wire_audit),
        },
        'field_bits': int(field_bits),
        'current_stream': {
            'operation_count': int(scheduled_modular_primitive_netlist['operation_count']),
            'non_clifford_count': int(scheduled_modular_primitive_netlist['non_clifford_count']),
            'scratch_observation_count': scratch_observations,
            'scratch_unique_wire_count': scratch_unique,
            'scratch_single_use_wire_count': scratch_single_use,
            'scratch_cleanup_observation_count': scratch_cleanup,
            'scratch_abandoned_garbage_count': scratch_abandoned,
            'partial_product_scratch_observation_count': partial_product_observations,
            'non_partial_product_scratch_observation_count': non_partial_product_observations,
            'physical_lifecycle_status': 'invalid_abandoned_temporary_and_targets',
        },
        'streamed_lifecycle_candidate': streamed_candidate,
        'candidate_lifecycle_stream': candidate_stream,
        'checks': checks,
        'pass': all(checks.values()),
        'promotion_blockers': [
            {
                'name': 'consume_cleanup_lowering_missing',
                'active': True,
                'required_to_close': 'Generate primitive rows that consume each temporary AND into a counted accumulator update and then cleanup or measure-uncompute the temporary wire before reuse.',
            },
            {
                'name': 'candidate_cost_not_public',
                'active': True,
                'required_to_close': 'Bind the consume and cleanup rows into scheduled_modular_primitive_netlist, recompute non-Clifford/measurement totals, and only then update public resource claims.',
            },
        ],
    }


__all__ = [
    'MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA',
    'build_modular_multiplier_lifecycle',
]
